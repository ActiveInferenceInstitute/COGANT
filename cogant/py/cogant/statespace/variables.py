"""
State variable extraction and classification.

Identifies and classifies state variables from hidden_state nodes in the
program graph, computing cardinality, domain, and factorization.
"""

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping

logger = logging.getLogger(__name__)

__all__ = [
    "StateVariableType",
    "ConfidenceLevel",
    "map_confidence_score",
    "StateVariable",
    "FactorizationInfo",
    "StateVariableExtractor",
    "ObservationVar",
    "VariableRegistry",
]


class StateVariableType(StrEnum):
    """Classification of state variables."""
    BOOLEAN = "boolean"
    DISCRETE = "discrete"
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    VECTOR = "vector"
    COMPOSITE = "composite"


class ConfidenceLevel(StrEnum):
    """Confidence in extracted information."""
    DEFINITE = "definite"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


def map_confidence_score(confidence_score: float) -> ConfidenceLevel:
    """Map a numeric confidence score in [0, 1] to a :class:`ConfidenceLevel`.

    The single source of truth for the state-space layer's categorical
    confidence ladder. Both :meth:`StateVariableExtractor._map_confidence`
    and :meth:`cogant.statespace.compiler.StateSpaceCompiler._map_confidence`
    delegate to this helper so the two call sites cannot drift.

    Thresholds (audit 2026-04-09):
        The 0.95 / 0.80 / 0.60 / 0.40 ladder is a **principled default**
        aligned with the translation-rule confidence bands documented in
        :mod:`cogant.translate.rules` (top/high/upper-mid/mid/bottom/lowest
        at 0.90/0.85/0.80/0.75/0.70/0.65). The ladder is intentionally
        coarser than the rule bands so that adjacent rule bands collapse
        to the same ``ConfidenceLevel`` label, giving downstream consumers
        a stable categorical view. TODO(calibration): validate the mapping
        against the human-reviewed GNN gold standard from the 20-repo
        corpus; thresholds may be re-centered if the resulting LOW/MEDIUM
        split does not match human judgments.

    Args:
        confidence_score: Score from 0.0 to 1.0.

    Returns:
        Corresponding :class:`ConfidenceLevel`.
    """
    if confidence_score >= 0.95:        # matches "definite" (near-1)
        return ConfidenceLevel.DEFINITE
    elif confidence_score >= 0.80:      # >= upper-mid rule band
        return ConfidenceLevel.HIGH
    elif confidence_score >= 0.60:      # below lowest rule band
        return ConfidenceLevel.MEDIUM
    elif confidence_score >= 0.40:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.UNCERTAIN


@dataclass
class StateVariable:
    """A hidden-state variable extracted from the program graph.

    Represents one factor of the system's hidden state as identified
    by a ``HIDDEN_STATE`` semantic mapping. Downstream consumers
    (``GNNMatrices``, ``StateSpaceCompiler``) use these to build the
    B transition tensor and D prior vector.

    Attributes:
        id: Stable identifier (``var_<node_id>``).
        name: Human-readable name derived from the graph node.
        var_type: Inferred variable type (boolean, discrete, continuous, …).
        node_id: Graph node id marked as HIDDEN_STATE.
        cardinality: Number of discrete states (None for continuous).
        domain: Optional list of explicit domain values.
        factors: Optional list of factor ids for factored representations.
        is_discrete: True when cardinality is finite.
        confidence: Confidence level of the extraction.
        description: Optional free-text description.
        mutations: Edge IDs of WRITES edges touching this variable.
        reads: Edge IDs of READS edges touching this variable.
        observable: True when this variable also has an OBSERVATION mapping.
    """
    id: str
    name: str
    var_type: StateVariableType
    node_id: str  # Reference to graph node marked as hidden_state
    cardinality: int | None = None
    domain: list[Any] | None = None
    factors: list[str] | None = None  # For factorization
    is_discrete: bool = True
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    description: str | None = None
    mutations: list[str] = field(default_factory=list)  # Edge IDs of mutations
    reads: list[str] = field(default_factory=list)  # Edge IDs of reads
    observable: bool = False
    """True when the same underlying node also has an OBSERVATION mapping.

    Used by the state-space compiler and downstream GNN formatter to decide
    whether this hidden-state variable should expose an observation channel
    in the generated A/B/C/D matrices.
    """

    def __repr__(self) -> str:
        """Return a detailed string representation of the variable."""
        return (
            f"StateVariable(id={self.id!r}, name={self.name!r}, "
            f"var_type={self.var_type}, cardinality={self.cardinality}, "
            f"is_discrete={self.is_discrete}, confidence={self.confidence})"
        )

    def merge(self, other: "StateVariable") -> "StateVariable":
        """Merge two StateVariable instances into a single combined variable.

        Combines metadata from both variables, preferring non-None values
        from ``self`` when both are set. Concatenates lists (mutations, reads).

        Args:
            other: Another StateVariable to merge with this one.

        Returns:
            A new StateVariable with merged attributes.

        Raises:
            ValueError: If the variables have conflicting core attributes
                (e.g., different var_type or node_id).

        Example:
            >>> v1 = StateVariable(id="var_x", name="x", ...)
            >>> v2 = StateVariable(id="var_y", name="x_alt", ...)
            >>> merged = v1.merge(v2)
        """
        if self.var_type != other.var_type:
            raise ValueError(
                f"Cannot merge variables with different types: "
                f"{self.var_type} vs {other.var_type}"
            )

        # Merge confidence, preferring higher confidence
        merged_confidence = (
            self.confidence if self.confidence != ConfidenceLevel.MEDIUM
            else other.confidence
        )

        # Merge lists
        merged_mutations = list(set(self.mutations) | set(other.mutations))
        merged_reads = list(set(self.reads) | set(other.reads))

        # Merge domain if both are set
        merged_domain = self.domain if self.domain else other.domain

        # Merge factors
        merged_factors = self.factors if self.factors else other.factors
        if other.factors:
            merged_factors = (
                list(set(self.factors) | set(other.factors))
                if merged_factors else other.factors
            )

        return StateVariable(
            id=self.id,
            name=self.name,
            var_type=self.var_type,
            node_id=self.node_id,
            cardinality=self.cardinality if self.cardinality else other.cardinality,
            domain=merged_domain,
            factors=merged_factors,
            is_discrete=self.is_discrete and other.is_discrete,
            confidence=merged_confidence,
            description=self.description or other.description,
            mutations=merged_mutations,
            reads=merged_reads,
            observable=self.observable or other.observable,
        )


@dataclass
class FactorizationInfo:
    """Information about state variable factorization."""
    factors: list[str]
    independence_score: float  # 0-1: how independent are factors
    dependencies: dict[str, list[str]]  # Factor ID -> list of dependent factors


class StateVariableExtractor:
    """
    Identifies and classifies state variables from graph nodes marked as
    hidden_state, computing their cardinality, domain, and factorization.
    """

    def __init__(self, program_graph: ProgramGraph):
        """
        Initialize the extractor.

        Args:
            program_graph: The program graph to analyze.
        """
        self.graph = program_graph
        self.state_variables: dict[str, StateVariable] = {}
        self.factorization_map: dict[str, FactorizationInfo] = {}

    def extract(self, semantic_mappings: dict[str, SemanticMapping]) -> dict[str, StateVariable]:
        """
        Extract state variables from the program graph.

        Walks every ``HIDDEN_STATE`` mapping and builds a
        :class:`StateVariable` for each referenced graph node, inferring type,
        cardinality and domain from node metadata. Variables whose underlying
        node *also* has an ``OBSERVATION`` mapping are flagged as observable,
        so the compiler can wire the corresponding observation channel later.

        Args:
            semantic_mappings: Semantic mappings identifying hidden state nodes.

        Returns:
            Dictionary mapping variable ID to :class:`StateVariable`.
        """
        # Find all hidden_state mappings
        hidden_state_mappings = {
            mid: m for mid, m in semantic_mappings.items()
            if m.kind == MappingKind.HIDDEN_STATE
        }
        # Pre-compute the set of node IDs that carry an OBSERVATION mapping so
        # we can cheaply mark hidden-state variables as observable.
        observation_node_ids: set[str] = set()
        for m in semantic_mappings.values():
            if m.kind == MappingKind.OBSERVATION:
                observation_node_ids.update(m.graph_fragment_node_ids)

        logger.info(f"Found {len(hidden_state_mappings)} hidden state mappings")

        for mapping_id, mapping in hidden_state_mappings.items():
            self._extract_from_mapping(mapping_id, mapping)

        # Mark observable flag for any variable whose node also has an
        # OBSERVATION mapping (POMDP observation channel).
        for var in self.state_variables.values():
            if var.node_id in observation_node_ids:
                var.observable = True

        # Analyze factorization
        self._analyze_factorization()

        logger.info(f"Extracted {len(self.state_variables)} state variables")
        return self.state_variables

    def _extract_from_mapping(self, mapping_id: str, mapping: SemanticMapping) -> None:
        """
        Extract state variable from a single hidden_state mapping.

        Args:
            mapping_id: The mapping ID.
            mapping: The semantic mapping.
        """
        for node_id in mapping.graph_fragment_node_ids:
            node = self.graph.get_node(node_id)
            if not node:
                continue

            var_id = f"var_{node_id}"
            var_name = self._infer_var_name(node, mapping)
            var_type = self._infer_var_type(node, mapping)
            is_discrete = var_type != StateVariableType.CONTINUOUS

            # Find mutations and reads
            mutations = [e.id for e in self.graph.get_edges_from(node_id)
                        if e.kind == EdgeKind.WRITES]
            reads = [e.id for e in self.graph.get_edges_to(node_id)
                    if e.kind == EdgeKind.READS]

            # Infer cardinality and domain
            cardinality, domain = self._infer_cardinality_and_domain(node, var_type, mapping)

            state_var = StateVariable(
                id=var_id,
                name=var_name,
                var_type=var_type,
                node_id=node_id,
                cardinality=cardinality,
                domain=domain,
                is_discrete=is_discrete,
                confidence=self._map_confidence(mapping.confidence_score),
                description=mapping.description,
                mutations=mutations,
                reads=reads,
            )

            self.state_variables[var_id] = state_var
            logger.debug(f"Extracted state variable: {var_name} (type={var_type})")

    def _infer_var_name(self, node: Node, mapping: SemanticMapping) -> str:
        """
        Infer variable name from node and mapping.

        Args:
            node: The node.
            mapping: The semantic mapping.

        Returns:
            Inferred variable name.
        """
        if mapping.semantic_label:
            return mapping.semantic_label
        return node.name

    def _infer_var_type(self, node: Node, mapping: SemanticMapping) -> StateVariableType:
        """
        Infer variable type from node metadata and mapping.

        Args:
            node: The node.
            mapping: The semantic mapping.

        Returns:
            Inferred StateVariableType.
        """
        # Check metadata for type hints
        if "type_hint" in node.metadata:
            type_hint = node.metadata["type_hint"]
            if type_hint in ("bool", "boolean"):
                return StateVariableType.BOOLEAN
            elif type_hint in ("int", "integer"):
                return StateVariableType.DISCRETE
            elif type_hint in ("float", "real"):
                return StateVariableType.CONTINUOUS
            elif type_hint in ("str", "string"):
                return StateVariableType.CATEGORICAL
            elif "list" in type_hint or "array" in type_hint:
                return StateVariableType.VECTOR
            elif type_hint in ("dict", "object"):
                return StateVariableType.COMPOSITE

        # Check description for hints
        desc = (mapping.description or "").lower()
        if "flag" in desc or "enabled" in desc or "active" in desc:
            return StateVariableType.BOOLEAN
        elif "count" in desc or "index" in desc or "num" in desc:
            return StateVariableType.DISCRETE
        elif "rate" in desc or "prob" in desc or "value" in desc:
            return StateVariableType.CONTINUOUS

        # Default: assume discrete
        return StateVariableType.DISCRETE

    def _infer_cardinality_and_domain(
        self,
        node: Node,
        var_type: StateVariableType,
        mapping: SemanticMapping
    ) -> tuple[int | None, list[Any] | None]:
        """
        Infer cardinality and domain from node metadata, class attributes, and type.

        Args:
            node: The node.
            var_type: The variable type.
            mapping: The semantic mapping.

        Returns:
            Tuple of (cardinality, domain) or (None, None) if not inferrable.
        """
        # Check metadata for explicit cardinality
        if "cardinality" in node.metadata:
            card = node.metadata["cardinality"]
            return card, None

        if "enum_values" in node.metadata:
            values = node.metadata["enum_values"]
            return len(values), values

        # For class nodes, extract attributes from graph to infer cardinality
        if node.kind == NodeKind.CLASS:
            cardinality, domain = self._extract_class_attributes_cardinality(node)
            if cardinality is not None or domain is not None:
                return cardinality, domain

        # Type-based defaults
        if var_type == StateVariableType.BOOLEAN:
            return 2, [False, True]
        elif var_type == StateVariableType.CATEGORICAL:
            # Try to infer from description
            desc = (mapping.description or "").lower()
            if "status" in desc:
                return 3, ["pending", "active", "complete"]
            elif "state" in desc:
                return 4, ["init", "active", "paused", "done"]
            return None, None

        return None, None

    def _extract_class_attributes_cardinality(self, class_node: Node) -> tuple[int | None, list[str] | None]:
        """
        Extract cardinality and domain from class attributes in the graph.

        For classes like Request, Response, Middleware, finds contained methods/attributes
        and counts them or infers from known patterns.

        Args:
            class_node: A CLASS node.

        Returns:
            Tuple of (cardinality, domain_list) or (None, None).
        """
        # Find contained methods/attributes
        contained_nodes = []
        for edge in self.graph.edges.values():
            if edge.source_id == class_node.id and edge.kind == EdgeKind.CONTAINS:
                contained_nodes.append(edge.target_id)

        # For methods, cardinality = number of methods
        methods_count = 0
        method_names = []
        for node_id in contained_nodes:
            contained = self.graph.get_node(node_id)
            if contained and contained.kind == NodeKind.METHOD:
                methods_count += 1
                method_names.append(contained.name)

        if methods_count > 0:
            return methods_count, method_names

        # For non-method attributes, try common patterns
        class_name = class_node.name.lower()
        if "middleware" in class_name or "request" in class_name or "response" in class_name:
            # These typically have 3-5 attributes
            return 5, ["headers", "body", "status", "metadata", "config"]

        return None, None

    def _analyze_factorization(self) -> None:
        """
        Analyze factorization of state variables.
        Variables are independent if they don't share mutations or reads.
        """
        var_list = list(self.state_variables.values())

        for i, var in enumerate(var_list):
            var_mutations = set(var.mutations)
            var_reads = set(var.reads)

            # Find dependent variables
            dependencies = []
            for other_var in var_list[i + 1:]:
                other_mutations = set(other_var.mutations)
                set(other_var.reads)

                # Check for shared mutations or data dependencies
                if var_mutations & other_mutations or var_reads & other_mutations:
                    dependencies.append(other_var.id)

            if dependencies:
                # independence_score = 0.5 — principled default
                # ("moderately dependent"). Our current dependency
                # check is binary (shared-edge overlap), so we cannot
                # yet produce a graded score; 0.5 is the maximum-
                # entropy placeholder. TODO(calibration): replace
                # with a proper score derived from the fraction of
                # overlapping mutation/read edges, calibrated against
                # a human-labelled factorization gold standard on
                # the 20-repo corpus.
                self.factorization_map[var.id] = FactorizationInfo(
                    factors=[var.id] + dependencies,
                    independence_score=0.5,  # placeholder (see above)
                    dependencies={var.id: dependencies}
                )

    def _map_confidence(self, confidence_score: float) -> ConfidenceLevel:
        """Map numeric confidence score to :class:`ConfidenceLevel`.

        Thin delegator to the module-level :func:`map_confidence_score`
        helper. Kept as an instance method so that subclasses and existing
        test fixtures that call ``extractor._map_confidence(...)`` continue
        to work without churn. See :func:`map_confidence_score` for the
        full threshold rationale and calibration notes.

        Args:
            confidence_score: Score from 0.0 to 1.0.

        Returns:
            Corresponding :class:`ConfidenceLevel`.
        """
        return map_confidence_score(confidence_score)

    def get_state_variables(self) -> dict[str, StateVariable]:
        """
        Get all extracted state variables.

        Returns:
            Dictionary mapping variable ID to StateVariable.
        """
        return self.state_variables

    def get_factorization(self, var_id: str) -> FactorizationInfo | None:
        """
        Get factorization information for a variable.

        Args:
            var_id: The variable ID.

        Returns:
            FactorizationInfo if available, None otherwise.
        """
        return self.factorization_map.get(var_id)

    def compute_dimensionality(self) -> int:
        """
        Compute the dimensionality of the state space.

        Returns:
            Product of cardinalities of discrete variables (or estimate for continuous).
        """
        cardinality_product = 1
        continuous_count = 0

        for var in self.state_variables.values():
            if var.is_discrete and var.cardinality:
                cardinality_product *= var.cardinality
            elif not var.is_discrete:
                continuous_count += 1

        # Estimate: each continuous variable adds one dimension
        total_dim = cardinality_product * (2 ** continuous_count) if continuous_count else cardinality_product
        return total_dim


@dataclass
class ObservationVar:
    """An observable variable in the system.

    Represents one observation modality (sensor, log, metric, event, etc.)
    that the system can sense. May or may not correspond to a hidden state
    variable (observable vs hidden state distinction in Active Inference).

    Attributes:
        id: Stable identifier (``obs_<node_id>``).
        name: Human-readable name.
        source_node_id: Graph node id that emits this observation.
        modality_type: Channel classification (sensor, log, metric, event, other).
        cardinality: Number of discrete observation outcomes (None if continuous).
        confidence: Confidence level of the extraction.
        description: Optional free-text description.
    """
    id: str
    name: str
    source_node_id: str
    modality_type: str
    cardinality: int | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    description: str | None = None

    def __repr__(self) -> str:
        """Return a detailed string representation of the variable."""
        return (
            f"ObservationVar(id={self.id!r}, name={self.name!r}, "
            f"modality_type={self.modality_type}, cardinality={self.cardinality}, "
            f"confidence={self.confidence})"
        )

    def is_compatible_with(self, hidden: StateVariable) -> bool:
        """Check dimension compatibility between this observation and a hidden state.

        Two variables are compatible if:
        * Both are discrete with matching cardinality, OR
        * Both are continuous, OR
        * One has unknown cardinality (None).

        Args:
            hidden: A StateVariable to check compatibility with.

        Returns:
            True if the observation and hidden state can be paired in A matrix.

        Example:
            >>> obs = ObservationVar(id="obs_x", ..., cardinality=3)
            >>> hidden = StateVariable(..., cardinality=3)
            >>> obs.is_compatible_with(hidden)
            True
        """
        # If either has unknown cardinality, assume compatible
        if self.cardinality is None or hidden.cardinality is None:
            return True

        # Both discrete: cardinality must match
        if hidden.is_discrete and self.cardinality == hidden.cardinality:
            return True

        # Both continuous: compatible
        if not hidden.is_discrete and self.cardinality is None:
            return True

        return False


class VariableRegistry:
    """Registry of all variables (hidden and observed) in a state space.

    Provides convenient lookup and filtering methods for upstream and
    downstream stages that need to query variables by role, type, or
    other metadata.

    Example:
        >>> registry = VariableRegistry()
        >>> registry.add_hidden(var1)
        >>> registry.add_observation(obs1)
        >>> hidden_vars = registry.find_by_role("hidden_state")
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self.hidden_vars: dict[str, StateVariable] = {}
        self.observation_vars: dict[str, ObservationVar] = {}

    def add_hidden(self, var: StateVariable) -> None:
        """Add a hidden state variable to the registry.

        Args:
            var: StateVariable to add.
        """
        self.hidden_vars[var.id] = var

    def add_observation(self, obs: ObservationVar) -> None:
        """Add an observation variable to the registry.

        Args:
            obs: ObservationVar to add.
        """
        self.observation_vars[obs.id] = obs

    def get_hidden(self, var_id: str) -> StateVariable | None:
        """Retrieve a hidden variable by id.

        Args:
            var_id: Variable id.

        Returns:
            StateVariable if found, None otherwise.
        """
        return self.hidden_vars.get(var_id)

    def get_observation(self, obs_id: str) -> ObservationVar | None:
        """Retrieve an observation variable by id.

        Args:
            obs_id: Observation id.

        Returns:
            ObservationVar if found, None otherwise.
        """
        return self.observation_vars.get(obs_id)

    def find_by_role(self, role: str) -> list[StateVariable | ObservationVar]:
        """Find variables by AII role string.

        Supported roles: ``"hidden_state"``, ``"observation"``.

        Args:
            role: Role string to filter by.

        Returns:
            List of matching variables.

        Example:
            >>> hidden = registry.find_by_role("hidden_state")
        """
        if role == "hidden_state":
            return list(self.hidden_vars.values())
        elif role == "observation":
            return list(self.observation_vars.values())
        else:
            logger.warning(f"Unknown role: {role}")
            return []

    def to_list(self) -> list[dict[str, Any]]:
        """Convert registry to tabular output as list of dicts.

        Each dict represents one variable with keys:
        * ``id``, ``name``, ``type``, ``role`` (hidden_state or observation)
        * ``cardinality``, ``confidence``, ``description``

        Returns:
            List of dictionaries suitable for CSV/tabular export.

        Example:
            >>> rows = registry.to_list()
            >>> import csv
            >>> csv.DictWriter(f, fieldnames=rows[0].keys()).writerows(rows)
        """
        rows: list[dict[str, Any]] = []

        for var in self.hidden_vars.values():
            rows.append({
                "id": var.id,
                "name": var.name,
                "type": var.var_type.value,
                "role": "hidden_state",
                "cardinality": var.cardinality,
                "confidence": var.confidence.value,
                "description": var.description or "",
                "is_discrete": var.is_discrete,
                "observable": var.observable,
            })

        for obs in self.observation_vars.values():
            rows.append({
                "id": obs.id,
                "name": obs.name,
                "type": "observation",
                "role": "observation",
                "cardinality": obs.cardinality,
                "confidence": obs.confidence.value,
                "description": obs.description or "",
                "modality_type": obs.modality_type,
            })

        return rows
