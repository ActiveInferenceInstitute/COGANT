"""Upstream GNN canonical header section formatter.

This mixin emits the GNN-language sections expected by the Active Inference
Institute ``generalized-notation-notation`` reference implementation
(validated against the GNN v5.0.1 release: ``gnn.validate_gnn_syntax``
at the ``standard`` level, the ``5_type_checker`` and ``6_validation``
pipeline steps). The ``GNN v2.0.0`` header value is COGANT's own schema
identifier (:data:`cogant.schema.versions.CURRENT_GNN_VERSION`).

The canonical upstream section ordering is:

    ## GNNSection
    ## GNNVersionAndFlags
    ## ModelName
    ## ModelAnnotation              (optional but recommended)
    ## StateSpaceBlock
    ## Connections
    ## InitialParameterization
    ## Equations
    ## Time
    ## ActInfOntologyAnnotation
    ## ModelParameters
    ## Footer
    ## Signature

COGANT emits these sections at the TOP of ``model.gnn.md`` so that the
resulting file is simultaneously an upstream-valid GNN model and a
COGANT-extended bundle. COGANT's richer sections (``## Model
Metadata``, ``## Source Coverage``, ``## Markov Blanket``, etc.) follow
below and are treated as extensions by the upstream parser.

Variable naming convention (follows upstream examples):
  * hidden states → ``s_fN`` (factor index N)
  * observations → ``o_mN`` (modality index N)
  * actions/controls → ``u_cN`` (control index N)
  * matrices when present → ``A_mN``, ``B_fN``, ``C_mN``, ``D_fN``

Active Inference ontology concepts (upstream canonical):
  ``HiddenState``, ``Observation``, ``Action``, ``Policy``,
  ``LikelihoodMatrix``, ``TransitionMatrix``, ``PreferenceVector``,
  ``PriorBelief``, ``ExpectedFreeEnergy``, ``Time``.

See :class:`cogant.gnn.formatter.base.GNNMarkdownFormatter` for the
main entry point and :mod:`cogant.gnn.formatter` for the package.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from cogant import __version__

if TYPE_CHECKING:
    from cogant.process.extractor import ProcessModel
    from cogant.schemas.graph import ProgramGraph
    from cogant.statespace.compiler import StateSpaceModel


# Upstream canonical section list, in the order COGANT emits it.
UPSTREAM_REQUIRED_SECTIONS: list[str] = [
    "GNNSection",
    "GNNVersionAndFlags",
    "ModelName",
    "StateSpaceBlock",
    "Connections",
    "InitialParameterization",
    "Equations",
    "Time",
    "ActInfOntologyAnnotation",
    "ModelParameters",
    "Footer",
    "Signature",
]

# Optional sections that COGANT emits for human-facing provenance.
UPSTREAM_OPTIONAL_SECTIONS: list[str] = [
    "ModelAnnotation",
]


# Map COGANT StateVariableType values to GNN StateSpaceBlock type strings.
# Upstream examples use int, float, bool, and (by convention) categorical.
_VAR_TYPE_TO_GNN_TYPE: dict[str, str] = {
    "boolean": "bool",
    "discrete": "int",
    "continuous": "float",
    "categorical": "int",
    "vector": "float",
    "composite": "float",
}


def _gnn_type_for(var_type: object) -> str:
    """Return the upstream GNN type string for a StateVariableType."""
    raw = getattr(var_type, "value", None) or str(var_type).lower()
    return _VAR_TYPE_TO_GNN_TYPE.get(raw, "float")


def _identity_like_likelihood(obs_card: int, st_card: int) -> str:
    """Render a column-stochastic ``obs_card x st_card`` likelihood literal.

    Column ``c`` is one-hot on outcome ``c`` when ``c < obs_card``; any
    remaining columns are uniform (``1 / obs_card``), so every column is a
    probability distribution over outcomes.
    """
    uniform = f"{round(1.0 / obs_card, 4)}"
    rows: list[str] = []
    for r in range(obs_card):
        row = [("1.0" if r == c else "0.0") if c < obs_card else uniform for c in range(st_card)]
        rows.append("(" + ", ".join(row) + ")")
    return ", ".join(rows)


class _UpstreamSectionsMixin:
    """Emit upstream-compatible GNN sections.

    This mixin is layered onto :class:`GNNMarkdownFormatter` and expects
    ``self.graph``, ``self.state_space``, ``self.process``, and
    ``self.mappings`` to be populated by the concrete formatter.
    """

    # Attributes populated by the concrete formatter (see base.py).
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]

    # ------------------------------------------------------------------
    # Public aggregate
    # ------------------------------------------------------------------
    def _format_upstream_header(self) -> str:
        """Format the full upstream GNN header block.

        Emits, in order, every upstream-required section plus
        ``ModelAnnotation``.
        """
        blocks = [
            self._format_gnn_section(),
            self._format_gnn_version_and_flags(),
            self._format_model_name(),
            self._format_model_annotation(),
            self._format_state_space_block(),
            self._format_upstream_connections(),
            self._format_initial_parameterization(),
            self._format_equations(),
            self._format_time(),
            self._format_actinf_ontology_annotation(),
            self._format_model_parameters(),
            self._format_upstream_footer(),
            self._format_signature(),
        ]
        return "\n\n".join(block for block in blocks if block)

    # ------------------------------------------------------------------
    # Individual sections
    # ------------------------------------------------------------------
    def _format_gnn_section(self) -> str:
        """Emit ``## GNNSection`` — the canonical model identifier."""
        return "\n".join(
            [
                "## GNNSection",
                self._upstream_model_id(),
            ]
        )

    def _format_gnn_version_and_flags(self) -> str:
        """Emit ``## GNNVersionAndFlags`` — declares GNN version."""
        return "\n".join(
            [
                "## GNNVersionAndFlags",
                "GNN v2.0.0",
            ]
        )

    def _format_model_name(self) -> str:
        """Emit ``## ModelName`` — the human-readable model title."""
        return "\n".join(
            [
                "## ModelName",
                self.state_space.schema_name or self._upstream_model_id(),
            ]
        )

    def _format_model_annotation(self) -> str:
        """Emit ``## ModelAnnotation`` — free-form model description."""
        uri = "unknown source"
        if self.graph.metadata and getattr(self.graph.metadata, "repo_uri", None):
            uri = self.graph.metadata.repo_uri
        n_vars = len(self.state_space.variables)
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)
        lines = [
            "## ModelAnnotation",
            (
                f"COGANT-translated Active Inference model for `{self.state_space.schema_name}`. "
                f"Extracted from {uri} via the COGANT codebase-to-GNN pipeline. "
                f"Contains {n_vars} hidden-state factor(s), {n_obs} observation modality(ies), "
                f"and {n_act} control/action factor(s)."
            ),
            "",
            (
                "This file is simultaneously a GNN model accepted by the upstream "
                "generalized-notation-notation validator and a COGANT-extended bundle. "
                "The sections below the upstream header "
                "(Model Metadata, Source Coverage, Markov Blanket, etc.) are COGANT "
                "extensions that upstream parsers will ignore."
            ),
        ]
        return "\n".join(lines)

    def _format_state_space_block(self) -> str:
        """Emit ``## StateSpaceBlock`` — upstream variable declarations.

        Uses the ``name[card,1,type=X]`` syntax from the upstream GNN examples.
        Hidden states → ``s_fN``, observations → ``o_mN``, actions → ``u_cN``.
        Matrices (A, B, C, D) are emitted when the corresponding structures
        are non-empty so the type-checker sees a complete Active Inference
        shell.
        """
        lines: list[str] = ["## StateSpaceBlock"]
        n_states = len(self.state_space.variables)
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)

        # Hidden state factors
        for i, var in enumerate(self.state_space.variables.values()):
            card = var.cardinality or 2
            t = _gnn_type_for(var.var_type)
            lines.append(f"s_f{i}[{card},1,type={t}] # state factor")

        # Observation modalities
        for i, obs in enumerate(self.state_space.observations.values()):
            card = obs.cardinality or 2
            lines.append(f"o_m{i}[{card},1,type=int] # observation modality")

        # Control/action factors
        for i in range(n_act):
            lines.append(f"u_c{i}[1,1,type=int] # action control")

        # Likelihood A_m: observation | state
        for i, obs in enumerate(self.state_space.observations.values()):
            obs_card = obs.cardinality or 2
            first_state = next(iter(self.state_space.variables.values()), None)
            st_card = (first_state.cardinality if first_state else None) or 2
            lines.append(f"A_m{i}[{obs_card},{st_card},type=float]")

        # Transition B_f: state_next | state, control
        if n_states > 0:
            for i, var in enumerate(self.state_space.variables.values()):
                card = var.cardinality or 2
                act_card = max(n_act, 1)
                lines.append(f"B_f{i}[{card},{card},{act_card},type=float]")

        # Preference C_m: observation preference vector
        if self.state_space.preferences and n_obs > 0:
            for i, obs in enumerate(self.state_space.observations.values()):
                card = obs.cardinality or 2
                lines.append(f"C_m{i}[{card},1,type=float]")

        # Prior D_f: initial state distribution
        for i, var in enumerate(self.state_space.variables.values()):
            card = var.cardinality or 2
            lines.append(f"D_f{i}[{card},1,type=float]")

        # Expected free energy node: declared whenever ``## Connections`` routes
        # preferences into ``G`` so every connection endpoint is a declared
        # variable (upstream ``standard`` validation rejects undeclared ones).
        if self._emits_expected_free_energy():
            lines.append("G[1,type=float] # expected free energy")

        # Time scalar if dynamic
        if self.state_space.transitions:
            lines.append("t[1,1,type=int]")

        if len(lines) == 1:
            lines.append("# No state variables detected; empty block")
        return "\n".join(lines)

    def _format_upstream_connections(self) -> str:
        """Emit ``## Connections`` — upstream arrow-syntax causal edges.

        Produces the standard Active Inference POMDP connection pattern in the
        upstream GNN connection grammar: single-variable endpoints are bare
        identifiers, and multi-source edges group their sources in
        parentheses (``(s_f0, u)>B_f0`` in the upstream examples):

            D_f0>s_f0              (prior -> state)
            s_f0>A_m0              (state -> likelihood)
            (A_m0, s_f0)>o_m0      (likelihood + state -> observation)
            u_c0>B_f0              (control -> transition)
            (s_f0, B_f0)>s_f0      (transition updates state)
            (C_m0, o_m0)>G         (preference over observation -> expected free energy)
            G>u_c0                 (EFE -> action selection)

        Upstream parses a parenthesized source group into its member
        variables; the bare comma form (``A_m0,s_f0>o_m0``) is read as one
        undeclared variable named ``A_m0,s_f0`` and fails ``standard``
        validation (``Undefined variable in connection source``). Single
        endpoints stay unparenthesized: a lone ``(D_f0)`` is not a group.
        """
        lines: list[str] = ["## Connections"]
        n_states = len(self.state_space.variables)
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)

        for i in range(n_states):
            lines.append(f"D_f{i}>s_f{i}")

        if n_states > 0:
            for i in range(n_obs):
                state_idx = min(i, n_states - 1)
                lines.append(f"s_f{state_idx}>A_m{i}")
                lines.append(f"(A_m{i}, s_f{state_idx})>o_m{i}")

        for i in range(n_states):
            lines.append(f"(s_f{i}, B_f{i})>s_f{i}")
            if n_act > 0:
                lines.append(f"u_c{min(i, n_act - 1)}>B_f{i}")

        if self._emits_expected_free_energy():
            for i in range(n_obs):
                lines.append(f"(C_m{i}, o_m{i})>G")
            if n_act > 0:
                lines.append("G>u_c0")

        if len(lines) == 1:
            lines.append("# No connections derivable from empty state space")
        return "\n".join(lines)

    def _format_initial_parameterization(self) -> str:
        """Emit ``## InitialParameterization`` — per-factor A/B/C/D literals.

        The upstream variables are indexed per hidden-state factor
        (``D_f0``, ``B_f0``) and per observation modality (``A_m0``,
        ``C_m0``) over each factor's own categorical cardinality, which is
        a different axis from COGANT's aggregate matrices (one entry per
        variable / observation; see ``model.gnn.json`` ``matrices``). So:

        * ``D_f`` is a uniform prior over the factor's categories;
        * ``B_f`` is an identity ("stay") transition for every action;
        * ``A_m`` is a column-stochastic identity-like likelihood (state
          ``c`` maps to outcome ``c``; extra states get a uniform column);
        * ``C_m`` broadcasts the derived log-preference ``C[m]`` from
          :class:`cogant.gnn.matrices.GNNMatrices` over the modality's
          outcomes (``0.0`` when it cannot be derived).

        Every emitted A/B/D literal is a valid probability distribution;
        C is an unnormalized log-preference. Only ``C`` is derived, so the
        aggregate A/B/D arrays are not computed here.
        """
        # Lazy import to avoid circular imports at module load time.
        from cogant.gnn.matrices import GNNMatrices

        lines: list[str] = ["## InitialParameterization"]
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)

        C: list[Any] = []
        if self.state_space.preferences and n_obs > 0:
            try:
                C = GNNMatrices(
                    graph=self.graph,
                    mappings=self.mappings,
                    state_space=self.state_space,
                ).compute_C()
            except (ValueError, KeyError, AttributeError):
                C = []

        # D_f: uniform prior over each factor's categorical cardinality.
        for i, var in enumerate(self.state_space.variables.values()):
            card = var.cardinality or 2
            share = round(1.0 / card, 4)
            vec = ", ".join([f"{share}"] * card)
            lines.append(f"D_f{i}={{ ({vec}) }}")

        # A_m: emit an identity-like symbolic likelihood over local outcome
        # categories. A is column-stochastic (each column is P(o | s) for one
        # hidden state): state c maps deterministically to outcome c, and
        # states beyond the modality's outcome count carry an uninformative
        # uniform column instead of an all-zero (non-distribution) column.
        # Rows sit directly inside the braces (``A={ (row0), (row1) }``) so
        # upstream reads the declared [obs, state] shape, not one 1xN row.
        for i in range(n_obs):
            obs = list(self.state_space.observations.values())[i]
            obs_card = obs.cardinality or 2
            first_state = next(iter(self.state_space.variables.values()), None)
            st_card = (first_state.cardinality if first_state else None) or 2
            lines.append(f"A_m{i}={{ {_identity_like_likelihood(obs_card, st_card)} }}")

        # B_f: explicit identity transition per action slice. Upstream render
        # processors consume literal tensors; avoid symbolic identity(...)
        # shorthand in publication/current artifacts.
        for i, var in enumerate(self.state_space.variables.values()):
            card = var.cardinality or 2
            act_card = max(n_act, 1)
            slices: list[str] = []
            for next_state in range(card):
                columns: list[str] = []
                for previous_state in range(card):
                    value = "1.0" if next_state == previous_state else "0.0"
                    columns.append("(" + ", ".join([value] * act_card) + ")")
                slices.append("(" + ", ".join(columns) + ")")
            lines.append(f"B_f{i}={{ {', '.join(slices)} }}")

        # C_m: use derived log-preference values.
        if self.state_space.preferences and n_obs > 0:
            for i in range(n_obs):
                obs = list(self.state_space.observations.values())[i]
                card = obs.cardinality or 2
                if C and i < len(C):
                    # Broadcast the aggregate log-preference to the
                    # categorical dimension (uniform over buckets).
                    val = round(float(C[i]), 4)
                    vec = ", ".join([f"{val}"] * card)
                else:
                    vec = ", ".join(["0.0"] * card)
                lines.append(f"C_m{i}={{ ({vec}) }}")

        if len(lines) == 1:
            lines.append("# No parameters to emit; code-derived values live in state_space.json")
        return "\n".join(lines)

    def _format_equations(self) -> str:
        """Emit ``## Equations`` — symbolic summary of the derived payload."""
        return "\n".join(
            [
                "## Equations",
                "# Generative model equations are symbolic summaries of the derived A/B/C/D payload.",
                "Q(s) = softmax(ln(D) + ln(A^T * o))",
                "Q(pi) = softmax(-G(pi))",
            ]
        )

    def _format_time(self) -> str:
        """Emit ``## Time`` — upstream GNN time block.

        Uses ``Static`` when the state space has no transitions and
        ``Dynamic/Discrete/Time=t/ModelTimeHorizon=Unbounded`` when it does.

        The upstream type-checker (``src/type_checker/checker.py``) treats
        these as separate valid keywords:
          * ``Dynamic``        — model has temporal dynamics
          * ``Discrete``       — discrete-time (not continuous)
          * ``Time=t``         — time index variable is ``t``
          * ``ModelTimeHorizon=Unbounded`` — no fixed horizon

        Previously ``DiscreteTime=t`` was emitted as a single fused token,
        which is not in the upstream valid-specification list and would
        generate a warning from the upstream type-checker.
        """
        lines = ["## Time"]
        if self.state_space.transitions:
            lines.append("Dynamic")
            lines.append("Discrete")
            lines.append("Time=t")
            lines.append("ModelTimeHorizon=Unbounded")
        else:
            lines.append("Static")
        return "\n".join(lines)

    def _format_actinf_ontology_annotation(self) -> str:
        """Emit ``## ActInfOntologyAnnotation`` — variable → concept mapping.

        Maps every upstream variable declared in ``StateSpaceBlock`` to a
        canonical Active Inference ontology concept so the upstream ontology
        checker sees a complete annotation block.
        """
        lines = ["## ActInfOntologyAnnotation"]
        n_states = len(self.state_space.variables)
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)

        for i in range(n_states):
            lines.append(f"s_f{i}=HiddenState")
            lines.append(f"D_f{i}=PriorBelief")
            lines.append(f"B_f{i}=TransitionMatrix")
        for i in range(n_obs):
            lines.append(f"A_m{i}=LikelihoodMatrix")
        for i in range(n_obs):
            lines.append(f"o_m{i}=Observation")
            if self.state_space.preferences:
                lines.append(f"C_m{i}=PreferenceVector")
        for i in range(n_act):
            lines.append(f"u_c{i}=Action")
        if self._emits_expected_free_energy():
            lines.append("G=ExpectedFreeEnergy")
        if self.state_space.transitions:
            lines.append("t=Time")

        if len(lines) == 1:
            lines.append("# No variables to annotate")
        return "\n".join(lines)

    def _format_model_parameters(self) -> str:
        """Emit ``## ModelParameters`` — hyperparameters and metadata."""
        lines = ["## ModelParameters"]
        n_states = len(self.state_space.variables)
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)
        lines.append(f"num_hidden_states={n_states}")
        lines.append(f"num_observation_modalities={n_obs}")
        lines.append(f"num_control_factors={n_act}")
        lines.append(f"num_transitions={len(self.state_space.transitions)}")
        lines.append(f"num_preferences={len(self.state_space.preferences)}")
        first_state = next(iter(self.state_space.variables.values()), None)
        first_obs = next(iter(self.state_space.observations.values()), None)
        joint_state_cardinality = (first_state.cardinality if first_state else None) or max(
            n_states, 1
        )
        representative_observation_cardinality = (
            first_obs.cardinality if first_obs else None
        ) or max(n_obs, 1)
        lines.append(f"num_states: {joint_state_cardinality}")
        lines.append(f"num_obs: {representative_observation_cardinality}")
        lines.append(f"num_actions: {max(n_act, 1)}")
        regime = getattr(self.state_space.time_regime, "value", str(self.state_space.time_regime))
        lines.append(f"time_regime={regime}")
        return "\n".join(lines)

    def _format_upstream_footer(self) -> str:
        """Emit ``## Footer`` — generation timestamp and bundle provenance."""
        ts = datetime.now(UTC).isoformat()
        return "\n".join(
            [
                "## Footer",
                f"Generated by COGANT v{__version__} at {ts}; targets GNN v2.0.0.",
                "COGANT — codebase-to-GNN translation engine.",
            ]
        )

    def _format_signature(self) -> str:
        """Emit ``## Signature`` as the required provenance field."""
        return "\n".join(
            [
                "## Signature",
                "pending",
            ]
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _emits_expected_free_energy(self) -> bool:
        """True when the header routes preferences into an EFE node ``G``."""
        return bool(self.state_space.preferences) and len(self.state_space.observations) > 0

    def _upstream_model_id(self) -> str:
        """Return the upstream-safe model identifier.

        GNN identifiers should be alphanumeric (plus underscore); we
        sanitize the COGANT schema name so the upstream parser accepts it.
        """
        raw = self.state_space.schema_name or self.state_space.id or "CogantModel"
        sanitized = "".join((c if (c.isalnum() or c == "_") else "_") for c in raw)
        if not sanitized or not (sanitized[0].isalpha() or sanitized[0] == "_"):
            sanitized = "Cogant_" + sanitized
        return sanitized
