"""State-space compiler: semantic mappings + program graph → StateSpaceModel.

This module provides :class:`StateSpaceCompiler`, the bridge between
the symbolic output of the translation engine
(:class:`SemanticMapping` instances) and the numerical output that
downstream Active Inference stages consume
(:class:`StateSpaceModel`). Given a :class:`ProgramGraph` and a dict
of semantic mappings, the compiler identifies:

* **hidden state variables** — from :class:`MappingKind.HIDDEN_STATE`
  mappings and from the graph's variable nodes;
* **observation modalities** — from :class:`MappingKind.OBSERVATION`
  mappings;
* **actions and policies** — from :class:`MappingKind.ACTION` and
  :class:`MappingKind.POLICY` mappings;
* **transitions** — derived from WRITES/MUTATES edges originating on
  action nodes;
* **likelihoods** — distribution families inferred from variable type
  hints; and
* **preferences** — from :class:`MappingKind.CONSTRAINT` and
  :class:`MappingKind.PREFERENCE` mappings (usually rooted in tests).

The resulting :class:`StateSpaceModel` is the canonical input to
:class:`cogant.gnn.matrices.GNNMatrices`,
:class:`cogant.simulate.runner.ModelRunner`, and the GNN markdown
formatter.

Example:
    >>> compiler = StateSpaceCompiler(graph, schema_name="calculator")
    >>> model = compiler.compile(semantic_mappings)
    >>> len(model.variables), len(model.actions)  # doctest: +SKIP
    (3, 2)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.temporal import TemporalAnalyzer, TimeRegime
from cogant.statespace.variables import ConfidenceLevel, StateVariable, StateVariableExtractor

logger = logging.getLogger(__name__)


@dataclass
class ObservationModality:
    """A single observation channel in the compiled state space.

    Represents one observable the system can sense (sensor reading,
    log line, metric, event, etc.). Produced by
    :meth:`StateSpaceCompiler._extract_observations` from
    :class:`MappingKind.OBSERVATION` semantic mappings; one instance
    per unique graph node backing the mapping.

    Attributes:
        id: Stable identifier, typically ``obs_<node_id>``.
        name: Human-readable name (semantic label, falling back to the
            node name).
        source_node_id: Graph node id that emits this observation.
        modality_type: Heuristic channel class — ``"sensor"``,
            ``"log"``, ``"metric"``, ``"event"``, or ``"other"``.
        cardinality: Optional number of discrete channels if known.
        description: Optional free-text description from the mapping.
        confidence: Confidence tier inherited from the upstream
            semantic mapping.
    """
    id: str
    name: str
    source_node_id: str  # Reference to read-only node
    modality_type: str  # "sensor", "log", "metric", "event", etc.
    cardinality: int | None = None
    description: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class Action:
    """An action the system can take on its hidden state.

    Represents a controllable intervention: a function, method, or
    API call that writes to (or conditions on) state variables.
    Produced by :meth:`StateSpaceCompiler._extract_actions` from
    :class:`MappingKind.ACTION` or :class:`MappingKind.POLICY`
    semantic mappings.

    Attributes:
        id: Stable identifier, typically ``act_<node_id>``.
        name: Human-readable name (semantic label or node name).
        controller_id: Graph node id of the controller / API /
            function that executes this action.
        parameters: Parameter-name → parameter-metadata dict pulled
            from the underlying function signature.
        effects: List of state-variable ids written or mutated by
            this action (from WRITES/MUTATES edges).
        preconditions: List of state-variable ids read before the
            action fires (from READS edges or declared parameters).
        description: Optional free-text description.
        confidence: Confidence tier inherited from the semantic
            mapping.
    """
    id: str
    name: str
    controller_id: str  # Reference to controller/API node
    parameters: dict[str, Any] = field(default_factory=dict)
    effects: list[str] = field(default_factory=list)  # State variable IDs affected
    preconditions: list[str] = field(default_factory=list)  # State variable constraints
    description: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class Transition:
    """A symbolic pre → post state transition triggered by an action.

    Represents one reachability edge in the state space, derived from
    the static effect set of an :class:`Action` on the extracted
    :class:`StateVariable` collection. Produced by
    :meth:`StateSpaceCompiler._extract_transitions`.

    Attributes:
        id: Stable identifier, typically ``trans_<action_id>``.
        source_state: Pre-action variable snapshot — maps variable
            id → symbolic value tag (usually ``"pre"``).
        target_state: Post-action variable snapshot — maps variable
            id → symbolic value tag (``"post"`` for written vars,
            ``"pre"`` for read-only vars).
        action_id: Id of the :class:`Action` that drives this
            transition, or ``None`` for unconditional flows.
        triggered_by: Optional free-text trigger description
            (``"called_by:<name>"``, ``"event:<name>"``, or
            ``"init"``).
        probability: Optional explicit transition probability if a
            rule supplied one; otherwise ``None`` and downstream code
            falls back to the deterministic default.
        confidence: Inherited from the driving action.
    """
    id: str
    source_state: dict[str, Any]
    target_state: dict[str, Any]
    action_id: str | None = None
    triggered_by: str | None = None  # Event or condition
    probability: float | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class Likelihood:
    """A probabilistic distribution attached to a variable or observation.

    Produced by :meth:`StateSpaceCompiler._extract_likelihoods`. The
    distribution family is inferred from the variable's
    :class:`StateVariableType` (or the observation node's type hint):
    booleans become Bernoulli, small-cardinality discretes become
    Categorical, and continuous types become Gaussian.

    Attributes:
        id: Stable identifier, typically ``like_<variable_or_obs_id>``.
        variable_id: Id of the :class:`StateVariable` or
            :class:`ObservationModality` this likelihood describes.
        distribution_type: Distribution family —
            ``"bernoulli"``, ``"categorical"``, ``"gaussian"``, or
            ``"unknown"`` when the type could not be inferred.
        parameters: Distribution parameters (e.g. ``{"p": 0.5}`` for
            Bernoulli; ``{"mean": 0.0, "variance": 1.0}`` for
            Gaussian). Kept as a plain dict for JSON portability.
        confidence: Inherited from the underlying variable or
            mapping.
    """
    id: str
    variable_id: str
    distribution_type: str  # "bernoulli", "categorical", "gaussian", etc.
    parameters: dict[str, float] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class Preference:
    """A desired or forbidden configuration of state variables.

    Produced by :meth:`StateSpaceCompiler._extract_preferences` from
    :class:`MappingKind.CONSTRAINT` and :class:`MappingKind.PREFERENCE`
    semantic mappings (usually rooted in a test, assertion, or
    domain rule). Populates the C vector downstream.

    Attributes:
        id: Stable identifier, typically ``pref_<mapping_id>``.
        name: Human-readable name.
        description: Free-text description of what the preference
            encodes.
        scope: List of state-variable ids the preference applies to.
        expression: Logical expression (free text) describing the
            constraint, e.g. ``"balance >= 0"``.
        weight: Scalar weight used to convert the preference into a
            log-preference contribution for the GNN C vector.
            Defaults to 1.0.
        source: Optional graph node id of the test or spec that
            originated the preference.
        confidence: Confidence tier inherited from the upstream
            mapping.
    """
    id: str
    name: str
    description: str
    scope: list[str]  # State variable IDs
    expression: str  # Logical expression
    weight: float = 1.0
    source: str | None = None  # Reference to test/spec node
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class StateSpaceModel:
    """Fully compiled state-space model for a single schema.

    The canonical output of :meth:`StateSpaceCompiler.compile`. Bundles
    all structural (variables, observations, actions), dynamic
    (transitions, likelihoods), and normative (preferences) components
    along with the inferred time regime and arbitrary metadata. Every
    downstream consumer (:class:`GNNMatrices`, :class:`GNNModelRunner`,
    scoring metrics, formatters) operates on this single type.

    Attributes:
        id: Stable identifier, typically ``model_<schema_name>``.
        schema_name: Human-readable schema name passed at compile
            time; useful as a provenance tag.
        variables: Dict keyed by variable id; values are
            :class:`StateVariable` instances.
        observations: Dict keyed by observation id; values are
            :class:`ObservationModality` instances.
        actions: Dict keyed by action id; values are :class:`Action`
            instances.
        transitions: Dict keyed by transition id; values are
            :class:`Transition` instances.
        likelihoods: Dict keyed by likelihood id; values are
            :class:`Likelihood` instances.
        preferences: Dict keyed by preference id; values are
            :class:`Preference` instances.
        time_regime: Inferred :class:`TimeRegime` — discrete,
            continuous, or hybrid.
        metadata: Free-form metadata (step_unit, is_async, max_steps,
            counts, compiler version, etc.). Kept as a plain dict for
            JSON portability.
    """
    id: str
    schema_name: str
    variables: dict[str, StateVariable]
    observations: dict[str, ObservationModality]
    actions: dict[str, Action]
    transitions: dict[str, Transition]
    likelihoods: dict[str, Likelihood]
    preferences: dict[str, Preference]
    time_regime: TimeRegime
    metadata: dict[str, Any] = field(default_factory=dict)


class StateSpaceCompiler:
    """Compile a state-space model from a program graph and semantic mappings.

    The compiler is the bridge between the symbolic output of the
    translation engine (``SemanticMapping`` instances) and the numerical
    output that the GNN matrix builder consumes (``StateSpaceModel``).
    Given a program graph and a dictionary of mappings, it identifies:

    * hidden state variables (from ``HIDDEN_STATE`` mappings);
    * observation modalities (from ``OBSERVATION`` mappings);
    * actions and control factors (from ``ACTION`` and ``POLICY``
      mappings);
    * transitions derived from control-flow edges;
    * likelihoods derived from READS/OBSERVES edges; and
    * preferences derived from ``CONSTRAINT``/``PREFERENCE`` mappings.

    The compiler is stateless beyond a reference to the program graph
    and the auxiliary ``StateVariableExtractor`` / ``TemporalAnalyzer``
    helpers. Construct one per compilation run; do not reuse across
    graphs.

    Example:
        >>> from cogant.schemas.graph import ProgramGraph
        >>> from cogant.statespace.compiler import StateSpaceCompiler
        >>> graph = ProgramGraph()  # populated by the graph stage
        >>> compiler = StateSpaceCompiler(graph, schema_name="calculator")
        >>> model = compiler.compile(semantic_mappings={})
        >>> model.variables  # dict of StateVariable keyed by id
        {}
    """

    def __init__(self, program_graph: ProgramGraph, schema_name: str):
        """Initialize the compiler.

        Args:
            program_graph: The program graph to compile.
            schema_name: Name of the schema being compiled. Used in
                diagnostic logging and stamped on the resulting
                ``StateSpaceModel`` as a provenance tag.
        """
        self.graph = program_graph
        self.schema_name = schema_name
        self.var_extractor = StateVariableExtractor(program_graph)
        self.temporal_analyzer = TemporalAnalyzer(program_graph)

    def compile(self, semantic_mappings: dict[str, SemanticMapping]) -> StateSpaceModel:
        """Compile a complete state space model.

        Args:
            semantic_mappings: Semantic mappings keyed by mapping id.
                Usually produced by ``TranslationEngine.translate()`` and
                passed through conflict resolution.

        Returns:
            A fully populated ``StateSpaceModel`` with variables,
            observations, actions, transitions, likelihoods, and
            preferences. Empty collections are returned for any category
            with no matching mappings (never ``None``).

        Raises:
            ValueError: If ``semantic_mappings`` contains a value that is
                not a ``SemanticMapping`` instance.

        Example:
            >>> compiler = StateSpaceCompiler(graph, "calculator")
            >>> model = compiler.compile(mappings)
            >>> len(model.variables)
            3
        """
        logger.info(f"Compiling state space model for schema '{self.schema_name}'")

        # Extract state variables
        variables = self.var_extractor.extract(semantic_mappings)

        # Extract observations from read-only nodes
        observations = self._extract_observations(semantic_mappings)

        # Extract actions from controllers and APIs
        actions = self._extract_actions(semantic_mappings)

        # Extract transitions from control flow
        transitions = self._extract_transitions(variables, actions)

        # Extract likelihoods from metrics/tests
        likelihoods = self._extract_likelihoods(variables, semantic_mappings)

        # Extract preferences from tests and assertions
        preferences = self._extract_preferences(semantic_mappings)

        # Determine time regime
        time_regime = self.temporal_analyzer.analyze()

        # Build metadata for the state space model
        metadata = {
            "step_unit": "discrete" if time_regime.value == "discrete" else "continuous",
            "is_async": False,  # Default to synchronous
            "max_steps": 1000,
            "variable_count": len(variables),
            "observation_count": len(observations),
            "action_count": len(actions),
            "transition_count": len(transitions),
        }

        model = StateSpaceModel(
            id=f"model_{self.schema_name}",
            schema_name=self.schema_name,
            variables=variables,
            observations=observations,
            actions=actions,
            transitions=transitions,
            likelihoods=likelihoods,
            preferences=preferences,
            time_regime=time_regime,
            metadata=metadata,
        )

        logger.info(f"Compiled model with {len(variables)} variables, "
                   f"{len(observations)} observations, {len(actions)} actions")

        return model

    def _extract_observations(
        self,
        semantic_mappings: dict[str, SemanticMapping]
    ) -> dict[str, ObservationModality]:
        """
        Extract observation modalities from semantic mappings.

        Args:
            semantic_mappings: Semantic mappings.

        Returns:
            Dictionary of observation modalities.
        """
        observations = {}

        # Find OBSERVATION mappings
        obs_mappings = {
            mid: m for mid, m in semantic_mappings.items()
            if m.kind == MappingKind.OBSERVATION
        }

        for _i, (_mapping_id, mapping) in enumerate(obs_mappings.items()):
            for node_id in mapping.graph_fragment_node_ids:
                node = self.graph.get_node(node_id)
                if not node:
                    continue

                obs_id = f"obs_{node_id}"
                obs_name = mapping.semantic_label or node.name

                # Infer modality type from metadata or description
                modality_type = self._infer_modality_type(node, mapping)

                obs = ObservationModality(
                    id=obs_id,
                    name=obs_name,
                    source_node_id=node_id,
                    modality_type=modality_type,
                    description=mapping.description,
                    confidence=self._map_confidence(mapping.confidence_score),
                )
                observations[obs_id] = obs

        logger.debug(f"Extracted {len(observations)} observation modalities")
        return observations

    def _extract_actions(
        self,
        semantic_mappings: dict[str, SemanticMapping]
    ) -> dict[str, Action]:
        """
        Extract actions from ACTION and POLICY semantic mappings.

        For each ACTION or POLICY mapping, walks the underlying graph fragment
        nodes to build an :class:`Action` object populated with parameters
        (from function signature metadata), effects (from WRITES/MUTATES edges
        and containment), and preconditions (from READS edges and parameters).

        Only the first encountered mapping per graph node is used, so policy
        mappings cannot clobber action mappings with the same controller.

        Args:
            semantic_mappings: Semantic mappings keyed by mapping id.

        Returns:
            Dictionary keyed by ``act_<node_id>`` whose values are
            :class:`Action` objects.
        """
        actions: dict[str, Action] = {}
        seen_controllers: set[str] = set()

        # Find ACTION and POLICY mappings. POLICY is folded in because the
        # COGANT spec treats policies as structured actions (decision rules
        # that write to state). CONSTRAINT/PREFERENCE are handled separately.
        action_kinds = {MappingKind.ACTION, MappingKind.POLICY}
        action_mappings = [
            (mid, m) for mid, m in semantic_mappings.items()
            if m.kind in action_kinds
        ]

        for _mapping_id, mapping in action_mappings:
            for node_id in mapping.graph_fragment_node_ids:
                node = self.graph.get_node(node_id)
                if not node:
                    continue

                # Skip if another ACTION mapping already claimed this node.
                if node_id in seen_controllers:
                    continue
                seen_controllers.add(node_id)

                action_id = f"act_{node_id}"
                action_name = mapping.semantic_label or node.name

                # Extract parameters and effects from the program graph
                parameters = self._extract_action_parameters(node)
                effects = self._extract_action_effects(node_id, mapping)
                preconditions = self._extract_action_preconditions(node)

                action = Action(
                    id=action_id,
                    name=action_name,
                    controller_id=node_id,
                    parameters=parameters,
                    effects=effects,
                    preconditions=preconditions,
                    description=mapping.description,
                    confidence=self._map_confidence(mapping.confidence_score),
                )
                actions[action_id] = action

        logger.debug(f"Extracted {len(actions)} actions")
        return actions

    def _cross_reference_actions_and_variables(
        self,
        variables: dict[str, StateVariable],
        actions: dict[str, Action],
    ) -> dict[str, dict[str, list[str]]]:
        """
        Build a mapping of which actions read/write which state variables.

        For each action, examines WRITES and READS edges from the action's
        controller node and maps them to known state variables.

        Args:
            variables: Extracted state variables.
            actions: Extracted actions.

        Returns:
            Dict keyed by action_id, each value is
            {"reads": [var_id, ...], "writes": [var_id, ...]}.
        """
        # Build reverse lookup: graph node_id -> variable id
        node_to_var: dict[str, str] = {}
        for var_id, var in variables.items():
            node_to_var[var.node_id] = var_id

        xref: dict[str, dict[str, list[str]]] = {}

        for action_id, action in actions.items():
            reads: list[str] = []
            writes: list[str] = []

            for edge in self.graph.get_edges_from(action.controller_id):
                target_var = node_to_var.get(edge.target_id)
                if not target_var:
                    continue
                if edge.kind == EdgeKind.WRITES or edge.kind == EdgeKind.MUTATES:
                    writes.append(target_var)
                elif edge.kind == EdgeKind.READS or edge.kind == EdgeKind.OBSERVES:
                    reads.append(target_var)

            # Also check incoming edges for reads (the action may be the target)
            for edge in self.graph.get_edges_to(action.controller_id):
                source_var = node_to_var.get(edge.source_id)
                if not source_var:
                    continue
                if edge.kind == EdgeKind.READS or edge.kind == EdgeKind.OBSERVES:
                    reads.append(source_var)

            xref[action_id] = {"reads": reads, "writes": writes}

        return xref

    def _extract_transitions(
        self,
        variables: dict[str, StateVariable],
        actions: dict[str, Action]
    ) -> dict[str, Transition]:
        """
        Extract state transitions from control flow and actions.

        Uses WRITES edges from action nodes to populate source_state (pre-action
        variable values) and target_state (post-action variable values). Also
        examines CALLS edges to show orchestration flows.

        Args:
            variables: Extracted state variables.
            actions: Extracted actions.

        Returns:
            Dictionary of transitions.
        """
        transitions = {}

        # Build action-to-variable cross-reference
        xref = self._cross_reference_actions_and_variables(variables, actions)

        for action_id, action in actions.items():
            trans_id = f"trans_{action_id}"
            action_xref = xref.get(action_id, {"reads": [], "writes": []})

            # Source state: variables the action reads or writes, in their
            # pre-action ("pre") state
            source_state: dict[str, Any] = {}
            all_involved = set(action_xref["reads"]) | set(action_xref["writes"])
            for var_id in all_involved:
                source_state[var_id] = "pre"

            # Target state: written variables move to "post", read-only stay "pre"
            target_state: dict[str, Any] = {}
            written_set = set(action_xref["writes"])
            for var_id in all_involved:
                target_state[var_id] = "post" if var_id in written_set else "pre"

            # Infer trigger from control-flow edges into the action node
            triggered_by: str | None = None
            next_actions: list[str] = []

            # Look for edges to this action (what triggers it)
            for edge in self.graph.get_edges_to(action.controller_id):
                if edge.kind == EdgeKind.TRIGGERS:
                    source_node = self.graph.get_node(edge.source_id)
                    triggered_by = source_node.name if source_node else edge.source_id
                    break
                elif edge.kind == EdgeKind.CALLS:
                    source_node = self.graph.get_node(edge.source_id)
                    if source_node and source_node.name != action.name:
                        triggered_by = f"called_by:{source_node.name}"
                        break

            # Look for CALLS edges FROM this action (what it calls)
            for edge in self.graph.get_edges_from(action.controller_id):
                if edge.kind == EdgeKind.CALLS:
                    target_node = self.graph.get_node(edge.target_id)
                    if target_node:
                        next_actions.append(f"calls:{target_node.name}")

            transition = Transition(
                id=trans_id,
                source_state=source_state,
                target_state=target_state,
                action_id=action_id,
                triggered_by=triggered_by or f"{', '.join(next_actions) if next_actions else 'init'}",
                confidence=action.confidence,
            )
            transitions[trans_id] = transition

        logger.debug(f"Extracted {len(transitions)} transitions")
        return transitions

    def _extract_likelihoods(
        self,
        variables: dict[str, StateVariable],
        semantic_mappings: dict[str, SemanticMapping]
    ) -> dict[str, Likelihood]:
        """
        Build :class:`Likelihood` distributions for hidden-state variables and
        observation channels.

        For each :class:`StateVariable`, a likelihood is produced whose
        distribution kind is inferred from the variable's
        :class:`StateVariableType`:

        - ``BOOLEAN`` -> Bernoulli
        - ``DISCRETE`` with cardinality 2 -> Bernoulli
        - ``DISCRETE`` / ``CATEGORICAL`` with larger cardinality -> Categorical
        - ``CONTINUOUS`` -> Gaussian
        - anything else -> ``unknown``

        In addition, each :class:`OBSERVATION` semantic mapping produces an
        observation-channel likelihood whose parameters are derived from the
        underlying graph node's ``type_hint``/``cardinality`` metadata. Boolean
        hints map to Bernoulli, small-integer hints to Categorical, and float
        hints to Gaussian, mirroring the hidden-state logic above.

        Args:
            variables: State variables produced by the
                :class:`StateVariableExtractor`.
            semantic_mappings: Semantic mappings keyed by mapping id.

        Returns:
            Dictionary keyed by ``like_<identifier>`` whose values are
            :class:`Likelihood` objects.
        """
        likelihoods: dict[str, Likelihood] = {}

        # ------------------------------------------------------------------
        # Hidden-state likelihoods: one per StateVariable.
        # ------------------------------------------------------------------
        for var_id, variable in variables.items():
            likelihood_id = f"like_{var_id}"

            dist_type = self._infer_distribution_type(variable)
            parameters = self._default_distribution_parameters(
                dist_type, variable.cardinality
            )

            likelihoods[likelihood_id] = Likelihood(
                id=likelihood_id,
                variable_id=var_id,
                distribution_type=dist_type,
                parameters=parameters,
                confidence=variable.confidence,
            )

        # ------------------------------------------------------------------
        # Observation-channel likelihoods: one per OBSERVATION mapping. These
        # describe ``P(observation | hidden_state)`` and are keyed by the
        # underlying graph node so they can be correlated with the
        # ObservationModality output from _extract_observations.
        # ------------------------------------------------------------------
        for _mapping_id, mapping in semantic_mappings.items():
            if mapping.kind != MappingKind.OBSERVATION:
                continue
            for node_id in mapping.graph_fragment_node_ids:
                node = self.graph.get_node(node_id)
                if not node:
                    continue

                obs_like_id = f"like_obs_{node_id}"
                if obs_like_id in likelihoods:
                    continue

                dist_type = self._infer_observation_distribution(node)
                cardinality = node.metadata.get("cardinality") if node.metadata else None
                parameters = self._default_distribution_parameters(
                    dist_type, cardinality
                )

                likelihoods[obs_like_id] = Likelihood(
                    id=obs_like_id,
                    variable_id=f"obs_{node_id}",
                    distribution_type=dist_type,
                    parameters=parameters,
                    confidence=self._map_confidence(mapping.confidence_score),
                )

        logger.debug(f"Extracted {len(likelihoods)} likelihoods")
        return likelihoods

    def _infer_observation_distribution(self, node: Node) -> str:
        """
        Infer a distribution type for an observation modality from the
        node's ``type_hint`` metadata.

        - Boolean hints (``bool``, ``boolean``) -> ``bernoulli``.
        - Integer hints (``int``, ``integer``) -> ``categorical`` when
          cardinality metadata is small (<= 10), otherwise ``categorical``
          (Gaussian doesn't make sense for discrete observations).
        - Float hints (``float``, ``real``, ``double``) -> ``gaussian``.
        - String hints (``str``, ``string``) -> ``categorical``.
        - Unknown -> ``unknown``.

        Args:
            node: The observation's underlying graph node.

        Returns:
            Distribution type identifier.
        """
        meta = node.metadata or {}
        hint = str(meta.get("type_hint", "")).lower()
        if hint in ("bool", "boolean"):
            return "bernoulli"
        if hint in ("int", "integer"):
            return "categorical"
        if hint in ("float", "real", "double"):
            return "gaussian"
        if hint in ("str", "string"):
            return "categorical"
        if "list" in hint or "array" in hint or "vector" in hint:
            return "categorical"
        return "unknown"

    def _default_distribution_parameters(
        self,
        dist_type: str,
        cardinality: int | None,
    ) -> dict[str, float]:
        """
        Produce default parameters for a given distribution type. These
        parameters are placeholders that satisfy the GNN schema (each
        likelihood needs *some* parameters for downstream formatters) but
        remain easily recognisable as priors.

        Args:
            dist_type: One of ``bernoulli``, ``categorical``, ``gaussian``.
            cardinality: Optional known cardinality of the underlying variable.

        Returns:
            Dictionary of parameter name -> float value.
        """
        # Distribution defaults below are **principled, maximum-
        # entropy priors** chosen to be explicitly uninformative so
        # that downstream consumers can immediately recognise "this
        # parameter has not been learned yet" and either replace it
        # with posterior data or trigger a calibration pass.
        if dist_type == "bernoulli":
            # p = 0.5 — maximum-entropy Bernoulli prior
            # (H(p=0.5) = 1 bit; no class preference encoded).
            return {"p": 0.5}
        if dist_type == "categorical":
            # alpha = 1.0 — symmetric Dirichlet prior
            # (uniform over the simplex). Standard pymdp default.
            if cardinality and cardinality > 0:
                return {"alpha": 1.0, "n_classes": float(cardinality)}
            return {"alpha": 1.0}
        if dist_type == "gaussian":
            # Standard normal N(0, 1) — maximum-entropy Gaussian
            # prior subject to unit variance; matches the
            # conventional Active Inference generative-model prior
            # (Friston et al. 2017, "Active Inference: A Process
            # Theory", Neural Computation 29(1)).
            return {"mean": 0.0, "variance": 1.0}
        return {}

    def _extract_preferences(
        self,
        semantic_mappings: dict[str, SemanticMapping]
    ) -> dict[str, Preference]:
        """
        Extract preferences and constraints from CONSTRAINT/PREFERENCE mappings.

        For each CONSTRAINT or PREFERENCE mapping, builds a :class:`Preference`
        whose ``variable_id`` scope is discovered from READS/WRITES edges on
        the mapping's graph fragment, whose ``expression`` is pulled from
        mapping metadata, assertion/test node metadata, or falls back to the
        semantic label, and whose ``weight`` is derived directly from the
        mapping's confidence score.

        POLICY mappings are *not* treated as preferences — they are handled in
        :meth:`_extract_actions` because policies express decision rules that
        mutate state rather than goal constraints over state.

        Args:
            semantic_mappings: Semantic mappings keyed by mapping id.

        Returns:
            Dictionary keyed by ``pref_<index>`` whose values are
            :class:`Preference` objects.
        """
        preferences: dict[str, Preference] = {}

        # Find CONSTRAINT and PREFERENCE mappings.  POLICY is intentionally
        # excluded here so that policies and preferences do not double-count
        # the same underlying mapping.
        pref_kinds = {MappingKind.CONSTRAINT, MappingKind.PREFERENCE}
        pref_mappings = [
            (mid, m) for mid, m in semantic_mappings.items()
            if m.kind in pref_kinds
        ]

        for i, (mapping_id, mapping) in enumerate(pref_mappings):
            pref_id = f"pref_{i}"

            # Extract scope: which state variables are touched by the
            # constraint's graph fragment.
            scope = self._extract_preference_scope(mapping)

            # Extract expression from node metadata or assertion patterns.
            expression = self._extract_preference_expression(mapping)

            # Weight is driven by the mapping confidence -- a constraint we
            # are certain of carries more weight in the preference model.
            weight = float(mapping.confidence_score) if mapping.confidence_score else 1.0

            preference = Preference(
                id=pref_id,
                name=mapping.semantic_label or f"Preference {i}",
                description=mapping.description,
                scope=scope,
                expression=expression,
                weight=weight,
                source=mapping_id,
                confidence=self._map_confidence(mapping.confidence_score),
            )
            preferences[pref_id] = preference

        logger.debug(f"Extracted {len(preferences)} preferences")
        return preferences

    def _extract_preference_scope(self, mapping: SemanticMapping) -> list[str]:
        """
        Extract scope (affected state variable IDs) for a preference mapping.

        Examines READS, WRITES, OBSERVES, and MUTATES edges from/to the
        mapping's graph fragment nodes to find related state variables.

        Args:
            mapping: The semantic mapping for the preference/constraint.

        Returns:
            List of state variable IDs (var_<node_id> format).
        """
        scope_ids: list[str] = []
        seen: set[str] = set()
        read_write_kinds = {EdgeKind.READS, EdgeKind.WRITES, EdgeKind.MUTATES}
        if hasattr(EdgeKind, "OBSERVES"):
            read_write_kinds.add(EdgeKind.OBSERVES)

        for node_id in mapping.graph_fragment_node_ids:
            # Outgoing edges
            for edge in self.graph.get_edges_from(node_id):
                if edge.kind in read_write_kinds:
                    var_id = f"var_{edge.target_id}"
                    if var_id not in seen:
                        seen.add(var_id)
                        scope_ids.append(var_id)
            # Incoming edges
            for edge in self.graph.get_edges_to(node_id):
                if edge.kind in read_write_kinds:
                    var_id = f"var_{edge.source_id}"
                    if var_id not in seen:
                        seen.add(var_id)
                        scope_ids.append(var_id)

        return scope_ids

    def _extract_preference_expression(self, mapping: SemanticMapping) -> str:
        """
        Extract a logical expression for a preference/constraint mapping.

        Strategy:
        1. Check mapping metadata for an explicit "expression" key.
        2. Check graph fragment nodes for ASSERTION nodes with metadata.
        3. Construct from semantic label and description as a fallback.

        Args:
            mapping: The semantic mapping.

        Returns:
            Expression string (may be empty if nothing can be inferred).
        """
        # Strategy 1: explicit expression in mapping metadata
        if mapping.metadata.get("expression"):
            return str(mapping.metadata["expression"])

        # Strategy 2: look for assertion nodes in the fragment
        for node_id in mapping.graph_fragment_node_ids:
            node = self.graph.get_node(node_id)
            if not node:
                continue
            # Assertion nodes often carry the expression in metadata
            if node.kind == NodeKind.ASSERTION:
                expr = node.metadata.get("expression") or node.metadata.get("condition")
                if expr:
                    return str(expr)
            # Test nodes may carry assertion text
            if node.kind == NodeKind.TEST:
                expr = node.metadata.get("assertion") or node.metadata.get("expression")
                if expr:
                    return str(expr)
            # Policy nodes
            if node.kind == NodeKind.POLICY:
                expr = node.metadata.get("rule") or node.metadata.get("expression")
                if expr:
                    return str(expr)

        # Strategy 3: construct from label/description
        label = mapping.semantic_label.strip() if mapping.semantic_label else ""
        desc = mapping.description.strip() if mapping.description else ""
        if label and desc:
            return f"{label}: {desc}"
        return label or desc or ""

    def _infer_modality_type(self, node: Node, mapping: SemanticMapping) -> str:
        """
        Infer observation modality type from node and mapping.

        Args:
            node: The node.
            mapping: The semantic mapping.

        Returns:
            Modality type string.
        """
        desc = (mapping.description or "").lower()
        name = (mapping.semantic_label or node.name).lower()

        if "log" in desc or "log" in name:
            return "log"
        elif "metric" in desc or "metric" in name:
            return "metric"
        elif "event" in desc or "event" in name:
            return "event"
        elif "sensor" in desc or "sensor" in name:
            return "sensor"
        else:
            return "generic"

    def _extract_action_parameters(self, node: Node) -> dict[str, Any]:
        """
        Extract action parameters from node metadata.

        Handles both the dict form (``{"param_name": type}``) and the list
        form (``["self", "digit"]``) commonly emitted by static parsers.
        Drops the ``self`` parameter because it is implicit for methods.

        Args:
            node: The action node.

        Returns:
            Dictionary mapping parameter name to type (or ``None`` when
            no type annotation is available). Always returns a ``dict``.
        """
        raw = node.metadata.get("parameters") if node.metadata else None
        if not raw:
            return {}
        if isinstance(raw, dict):
            return {name: ty for name, ty in raw.items() if name != "self"}
        if isinstance(raw, (list, tuple)):
            params: dict[str, Any] = {}
            for entry in raw:
                if isinstance(entry, dict):
                    name = entry.get("name")
                    if name and name != "self":
                        params[str(name)] = entry.get("type")
                elif isinstance(entry, (list, tuple)) and len(entry) >= 1:
                    name = entry[0]
                    if name and name != "self":
                        params[str(name)] = entry[1] if len(entry) > 1 else None
                else:
                    name = str(entry)
                    if name and name != "self":
                        params[name] = None
            return params
        # Unknown shape — return empty dict so Action.parameters stays typed.
        return {}

    def _extract_action_effects(
        self,
        node_id: str,
        mapping: SemanticMapping
    ) -> list[str]:
        """
        Extract action effects on state variables from graph structure.

        For each action (which maps to a method node), finds:
        1. Direct WRITES edges FROM the action's node → that is the effect
        2. CONTAINS edges TO the action (parent class) → modifying that class is an effect
        3. CALLS edges FROM the action → those methods/functions are called side effects
        4. For __init__ methods, the effect is "initializes <class_name>"
        5. READS edges combined with CONTAINS relationship indicate state mutation

        Args:
            node_id: The action node ID.
            mapping: The semantic mapping.

        Returns:
            List of affected state variable IDs or descriptive names.
        """
        effects = []
        visited = set()

        action_node = self.graph.get_node(node_id)
        if not action_node:
            return effects

        # Strategy 1: Check if this is an __init__ method
        if action_node.name == "__init__" or "__init__" in action_node.name:
            # Find the parent class that this __init__ initializes
            for edge in self.graph.get_edges_to(node_id):
                if edge.kind == EdgeKind.CONTAINS:
                    parent_id = edge.source_id
                    parent_node = self.graph.get_node(parent_id)
                    if parent_node and parent_node.kind == NodeKind.CLASS:
                        effect_name = f"initializes {parent_node.name}"
                        if effect_name not in visited:
                            visited.add(effect_name)
                            effects.append(effect_name)
                    break

        # Strategy 2: Find direct WRITES edges from this action node
        for edge in self.graph.get_edges_from(node_id):
            if edge.kind == EdgeKind.WRITES:
                target_node = self.graph.get_node(edge.target_id)
                effect_name = f"var_{edge.target_id}"
                if effect_name not in visited:
                    visited.add(effect_name)
                    if target_node:
                        effects.append(f"{target_node.name} (writes)")
                    else:
                        effects.append(effect_name)

        # Strategy 3: For methods, check parent class via CONTAINS relationship
        # Methods that are part of a class implicitly modify that class's state
        if action_node.kind == NodeKind.METHOD:
            for edge in self.graph.get_edges_to(node_id):
                if edge.kind == EdgeKind.CONTAINS:
                    parent_id = edge.source_id
                    parent_node = self.graph.get_node(parent_id)
                    if parent_node and parent_node.kind == NodeKind.CLASS:
                        # This method is part of a class - it can modify class state
                        effect_name = f"var_{parent_id}"
                        if effect_name not in visited:
                            visited.add(effect_name)
                            effects.append(f"modifies {parent_node.name}")
                    break

        # Strategy 4: Find CALLS edges - methods called are side effects
        called_methods = []
        for edge in self.graph.get_edges_from(node_id):
            if edge.kind == EdgeKind.CALLS:
                target_node = self.graph.get_node(edge.target_id)
                if target_node:
                    called_methods.append(target_node.name)

        if called_methods and not effects:
            # If no other effects found but we call other methods, those are effects
            for method_name in called_methods[:3]:  # Limit to first 3 to avoid clutter
                effects.append(f"calls {method_name}")

        # Strategy 5: If still no effects, check READS relationship
        # A method that reads from a class typically also modifies it
        if not effects:
            for edge in self.graph.get_edges_from(node_id):
                if edge.kind in (EdgeKind.READS, EdgeKind.OBSERVES):
                    target_node = self.graph.get_node(edge.target_id)
                    if target_node and target_node.kind == NodeKind.CLASS:
                        # This method reads from (and likely modifies) a class
                        effects.append(f"manages {target_node.name}")
                        break

        return effects

    def _extract_action_preconditions(self, node: Node) -> list[str]:
        """
        Extract action preconditions from node metadata, parameters, and graph edges.

        Preconditions can come from:
        1. Explicit metadata in node.metadata["preconditions"]
        2. Required parameters (from method signature)
        3. READS edges showing required state access
        4. Docstring hints

        Args:
            node: The action node.

        Returns:
            List of precondition expressions.
        """
        preconditions = []

        # Strategy 1: Check explicit metadata
        if "preconditions" in node.metadata:
            return node.metadata["preconditions"]

        # Strategy 2: Extract from parameters (method signature)
        if "parameters" in node.metadata:
            params = node.metadata["parameters"]
            if isinstance(params, list):
                # Skip 'self' parameter
                param_list = [p for p in params if p != "self"]
                if param_list:
                    preconditions.append(f"requires: {', '.join(param_list)} to be defined")

        # Strategy 3: Check graph edges for required state
        # READS edges indicate that this action depends on reading certain state
        reads_targets = []
        for edge in self.graph.get_edges_from(node.id):
            if edge.kind in (EdgeKind.READS, EdgeKind.OBSERVES):
                target_node = self.graph.get_node(edge.target_id)
                if target_node:
                    reads_targets.append(target_node.name)

        if reads_targets:
            preconditions.append(f"requires state: {', '.join(set(reads_targets))}")

        # Strategy 4: CONTAINS edge to parent - methods need the parent class instance
        for edge in self.graph.get_edges_to(node.id):
            if edge.kind == EdgeKind.CONTAINS:
                parent_node = self.graph.get_node(edge.source_id)
                if parent_node and parent_node.kind == NodeKind.CLASS:
                    preconditions.append(f"requires {parent_node.name} instance")
                break

        # Strategy 5: Extract from docstring if available
        if "docstring" in node.metadata and node.metadata["docstring"]:
            doc = node.metadata["docstring"].lower()
            if "require" in doc or "expect" in doc or "must" in doc:
                docstring = node.metadata["docstring"]
                preconditions.append(f"docstring: {docstring[:60]}")

        return preconditions

    def _infer_distribution_type(self, variable: StateVariable) -> str:
        """
        Infer distribution type from variable characteristics.

        Args:
            variable: The state variable.

        Returns:
            Distribution type string.
        """
        from cogant.statespace.variables import StateVariableType

        if variable.var_type == StateVariableType.BOOLEAN:
            return "bernoulli"
        elif variable.var_type == StateVariableType.DISCRETE:
            if variable.cardinality == 2:
                return "bernoulli"
            else:
                return "categorical"
        elif variable.var_type == StateVariableType.CONTINUOUS:
            return "gaussian"
        elif variable.var_type == StateVariableType.CATEGORICAL:
            return "categorical"
        else:
            return "unknown"

    def _map_confidence(self, confidence_score: float) -> ConfidenceLevel:
        """Map numeric confidence score to ConfidenceLevel.

        Thresholds (audit 2026-04-09):
            The 0.95 / 0.80 / 0.60 / 0.40 ladder mirrors
            :meth:`cogant.statespace.variables.StateVariableExtractor._map_confidence`
            (see that docstring for full rationale). The two
            implementations are kept in sync intentionally — both
            consume ``SemanticMapping.confidence_score`` and both
            need to align with the translation-rule confidence
            bands (0.65-0.90). TODO(refactor): consolidate into a
            single helper in ``cogant.schemas.semantic`` and
            re-calibrate both call sites at once.

        Args:
            confidence_score: Score from 0.0 to 1.0.

        Returns:
            ConfidenceLevel.
        """
        # Principled-default ladder aligned with rule bands;
        # TODO(refactor) to merge with variables._map_confidence.
        if confidence_score >= 0.95:        # matches "definite"
            return ConfidenceLevel.DEFINITE
        elif confidence_score >= 0.80:      # >= upper-mid rule band
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.60:      # below lowest rule band
            return ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN
