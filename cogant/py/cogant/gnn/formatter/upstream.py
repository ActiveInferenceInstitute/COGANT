"""Upstream GNN v1.1 canonical header section formatter.

This mixin emits the five required and three recommended GNN v1.1 sections
expected by the upstream Active Inference Institute GNN type-checker
(``src/5_type_checker.py``) and the broader GNN pipeline.

The canonical upstream section ordering is:

    ## GNNSection
    ## GNNVersionAndFlags
    ## ModelName
    ## ModelAnnotation              (optional but recommended)
    ## StateSpaceBlock
    ## Connections
    ## InitialParameterization
    ## Time
    ## ActInfOntologyAnnotation
    ## ModelParameters              (optional)
    ## Footer                        (recommended)
    ## Signature                     (optional)

COGANT emits these sections at the TOP of ``model.gnn.md`` so that the
resulting file is simultaneously a valid upstream GNN v1 file AND a
COGANT-extended bundle. COGANT's richer sections (``## Model Metadata``,
``## Source Coverage``, ``## Markov Blanket``, etc.) follow below and are
treated as extensions by the upstream parser.

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

from datetime import datetime, timezone
from typing import Dict, List

from cogant.schemas.core import EdgeKind, NodeKind


# Upstream canonical section list, in the order the type-checker expects.
# Required sections per the upstream syntax spec at
# doc/gnn/gnn_syntax.md (v1.1):
UPSTREAM_REQUIRED_SECTIONS: List[str] = [
    "GNNSection",
    "GNNVersionAndFlags",
    "ModelName",
    "StateSpaceBlock",
    "Connections",
    "InitialParameterization",
    "Time",
    "ActInfOntologyAnnotation",
]

# Recommended/optional sections that COGANT also emits for completeness.
UPSTREAM_OPTIONAL_SECTIONS: List[str] = [
    "ModelAnnotation",
    "ModelParameters",
    "Equations",
    "Footer",
    "Signature",
]


# Map COGANT StateVariableType values to GNN v1 StateSpaceBlock type strings.
# Upstream examples use int, float, bool, and (by convention) categorical.
_VAR_TYPE_TO_GNN_TYPE: Dict[str, str] = {
    "boolean": "bool",
    "discrete": "int",
    "continuous": "float",
    "categorical": "int",
    "vector": "float",
    "composite": "float",
}


def _gnn_type_for(var_type: object) -> str:
    """Return the upstream GNN v1 type string for a StateVariableType."""
    raw = getattr(var_type, "value", None) or str(var_type).lower()
    return _VAR_TYPE_TO_GNN_TYPE.get(raw, "float")


class _UpstreamSectionsMixin:
    """Emit upstream-compatible GNN v1.1 sections.

    This mixin is layered onto :class:`GNNMarkdownFormatter` and expects
    ``self.graph``, ``self.state_space``, ``self.process``, and
    ``self.mappings`` to be populated by the concrete formatter.
    """

    # ------------------------------------------------------------------
    # Public aggregate
    # ------------------------------------------------------------------
    def _format_upstream_header(self) -> str:
        """Format the full upstream GNN v1.1 header block.

        Emits, in order, every upstream-required section plus
        ``ModelAnnotation``, ``ModelParameters``, and ``Footer``.
        """
        blocks = [
            self._format_gnn_section(),
            self._format_gnn_version_and_flags(),
            self._format_model_name(),
            self._format_model_annotation(),
            self._format_state_space_block(),
            self._format_upstream_connections(),
            self._format_initial_parameterization(),
            self._format_time(),
            self._format_actinf_ontology_annotation(),
            self._format_model_parameters(),
            self._format_upstream_footer(),
        ]
        return "\n\n".join(block for block in blocks if block)

    # ------------------------------------------------------------------
    # Individual sections
    # ------------------------------------------------------------------
    def _format_gnn_section(self) -> str:
        """Emit ``## GNNSection`` — the canonical model identifier."""
        return "\n".join([
            "## GNNSection",
            self._upstream_model_id(),
        ])

    def _format_gnn_version_and_flags(self) -> str:
        """Emit ``## GNNVersionAndFlags`` — declares GNN version."""
        return "\n".join([
            "## GNNVersionAndFlags",
            "GNN v1",
        ])

    def _format_model_name(self) -> str:
        """Emit ``## ModelName`` — the human-readable model title."""
        return "\n".join([
            "## ModelName",
            self.state_space.schema_name or self._upstream_model_id(),
        ])

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
                "This file is simultaneously a valid upstream GNN v1.1 model and a "
                "COGANT-extended bundle. The sections below the upstream header "
                "(Model Metadata, Source Coverage, Markov Blanket, etc.) are COGANT "
                "extensions that upstream parsers will ignore."
            ),
        ]
        return "\n".join(lines)

    def _format_state_space_block(self) -> str:
        """Emit ``## StateSpaceBlock`` — upstream variable declarations.

        Uses the ``name[card,1,type=X]`` syntax from GNN v1.1 examples.
        Hidden states → ``s_fN``, observations → ``o_mN``, actions → ``u_cN``.
        Matrices (A, B, C, D) are emitted when the corresponding structures
        are non-empty so the type-checker sees a complete Active Inference
        shell.
        """
        lines: List[str] = ["## StateSpaceBlock"]
        n_states = len(self.state_space.variables)
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)

        # Hidden state factors
        for i, var in enumerate(self.state_space.variables.values()):
            card = var.cardinality or 2
            t = _gnn_type_for(var.var_type)
            lines.append(f"s_f{i}[{card},1,type={t}]")

        # Observation modalities
        for i, obs in enumerate(self.state_space.observations.values()):
            card = obs.cardinality or 2
            lines.append(f"o_m{i}[{card},1,type=int]")

        # Control/action factors
        for i in range(n_act):
            lines.append(f"u_c{i}[1,1,type=int]")

        # Likelihood A_m: observation | state
        for i in range(min(n_obs, max(n_states, 1))):
            obs_card = list(self.state_space.observations.values())[i].cardinality or 2
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

        # Time scalar if dynamic
        if self.state_space.transitions:
            lines.append("t[1,1,type=int]")

        if len(lines) == 1:
            lines.append("# No state variables detected; empty block")
        return "\n".join(lines)

    def _format_upstream_connections(self) -> str:
        """Emit ``## Connections`` — upstream arrow-syntax causal edges.

        Produces the standard Active Inference POMDP connection pattern:
            D_f > s_f      (prior → state)
            s_f > A_m      (state → likelihood)
            (A_m, s_f) > o_m (likelihood + state → observation)
            u_c > B_f      (control → transition)
            (B_f, s_f) > s_f' (transition updates state)
            (C_m, o_m) > G  (preference over observation → expected free energy)
            G > u_c        (EFE → action selection)
        """
        lines: List[str] = ["## Connections"]
        n_states = len(self.state_space.variables)
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)

        for i in range(n_states):
            lines.append(f"(D_f{i}) > (s_f{i})")

        for i in range(min(n_states, n_obs)):
            lines.append(f"(s_f{i}) > (A_m{i})")
            lines.append(f"(A_m{i}, s_f{i}) > (o_m{i})")

        for i in range(n_states):
            lines.append(f"(s_f{i}, B_f{i}) > (s_f{i})")
            if n_act > 0:
                lines.append(f"(u_c{min(i, n_act - 1)}) > (B_f{i})")

        if self.state_space.preferences and n_obs > 0:
            for i in range(n_obs):
                lines.append(f"(C_m{i}, o_m{i}) > G")
            if n_act > 0:
                lines.append("G > (u_c0)")

        if len(lines) == 1:
            lines.append("# No connections derivable from empty state space")
        return "\n".join(lines)

    def _format_initial_parameterization(self) -> str:
        """Emit ``## InitialParameterization`` — placeholder identity/uniform priors.

        COGANT cannot in general recover the numeric parameters of an
        Active Inference model from arbitrary source code. We emit sensible
        identity/uniform placeholders so the upstream type-checker can
        accept the file; real parameter values live in ``state_space.json``.
        """
        lines: List[str] = ["## InitialParameterization"]
        n_states = len(self.state_space.variables)
        n_obs = len(self.state_space.observations)
        n_act = len(self.state_space.actions)

        # D_f: uniform prior over hidden states
        for i, var in enumerate(self.state_space.variables.values()):
            card = var.cardinality or 2
            share = round(1.0 / card, 4)
            vec = ", ".join([f"{share}"] * card)
            lines.append(f"D_f{i}={{ ({vec}) }}")

        # A_m: identity-like likelihood
        for i in range(min(n_obs, max(n_states, 1))):
            obs = list(self.state_space.observations.values())[i]
            obs_card = obs.cardinality or 2
            first_state = next(iter(self.state_space.variables.values()), None)
            st_card = (first_state.cardinality if first_state else None) or 2
            rows = []
            for r in range(obs_card):
                row = [
                    "1.0" if (r == c and r < st_card) else "0.0"
                    for c in range(st_card)
                ]
                rows.append("(" + ", ".join(row) + ")")
            lines.append(f"A_m{i}={{ ({', '.join(rows)}) }}")

        # B_f: identity transition per action slice.
        # Emitted as symbolic identity, not a comment, because any line
        # beginning with '#' in the markdown body would parse as an H1
        # heading and confuse the upstream parser.
        for i, var in enumerate(self.state_space.variables.values()):
            card = var.cardinality or 2
            act_card = max(n_act, 1)
            lines.append(f"B_f{i}=identity({card},{card},{act_card})")

        if self.state_space.preferences and n_obs > 0:
            for i in range(n_obs):
                obs = list(self.state_space.observations.values())[i]
                card = obs.cardinality or 2
                vec = ", ".join(["0.0"] * card)
                lines.append(f"C_m{i}={{ ({vec}) }}")

        if len(lines) == 1:
            lines.append(
                "# No parameters to emit; code-derived values live in state_space.json"
            )
        return "\n".join(lines)

    def _format_time(self) -> str:
        """Emit ``## Time`` — GNN v1.1 time block.

        Uses ``Static`` when the state space has no transitions and
        ``Dynamic/DiscreteTime=t/ModelTimeHorizon=Unbounded`` when it does.
        """
        lines = ["## Time"]
        if self.state_space.transitions:
            lines.append("Dynamic")
            lines.append("DiscreteTime=t")
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
        for i in range(min(n_states, n_obs)):
            lines.append(f"A_m{i}=LikelihoodMatrix")
        for i in range(n_obs):
            lines.append(f"o_m{i}=Observation")
            if self.state_space.preferences:
                lines.append(f"C_m{i}=PreferenceVector")
        for i in range(n_act):
            lines.append(f"u_c{i}=Action")
        if self.state_space.preferences and n_act > 0:
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
        regime = getattr(self.state_space.time_regime, "value", str(self.state_space.time_regime))
        lines.append(f"time_regime={regime}")
        return "\n".join(lines)

    def _format_upstream_footer(self) -> str:
        """Emit ``## Footer`` — generation timestamp and signature."""
        ts = datetime.now(timezone.utc).isoformat()
        return "\n".join([
            "## Footer",
            f"Generated by COGANT v0.1.0 at {ts}.",
            "COGANT — codebase-to-GNN translation engine.",
            "",
            "## Signature",
            "Cryptographic signature: not signed (COGANT development build).",
        ])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _upstream_model_id(self) -> str:
        """Return the upstream-safe model identifier.

        GNN v1 identifiers should be alphanumeric (plus underscore); we
        sanitize the COGANT schema name so the upstream parser accepts it.
        """
        raw = self.state_space.schema_name or self.state_space.id or "CogantModel"
        sanitized = "".join(
            (c if (c.isalnum() or c == "_") else "_") for c in raw
        )
        if not sanitized or not (sanitized[0].isalpha() or sanitized[0] == "_"):
            sanitized = "Cogant_" + sanitized
        return sanitized
