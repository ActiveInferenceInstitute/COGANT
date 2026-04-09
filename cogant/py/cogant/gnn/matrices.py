"""GNN A/B/C/D matrix derivation from program graph and semantic mappings.

Implements the four core probabilistic matrices required by the Active
Inference Institute (AII) upstream Generalized Notation Notation (GNN)
specification:

* **A** — likelihood matrix ``P(o | s)`` (observation given hidden state),
  shape ``[n_obs x n_states]``. Rows sum to 1.0.
* **B** — transition tensor ``P(s' | s, a)`` (next state given current
  state and action), shape ``[n_states x n_states x n_actions]``. For
  each action slice, columns sum to 1.0 (column-stochastic per AII
  convention).
* **C** — log-preference vector over observations, shape ``[n_obs]``.
  Positive values indicate preferred observations, negative values
  indicate aversive observations. This is NOT a probability — it is a
  log-preference in the sense of the Friston expected-free-energy
  functional.
* **D** — initial prior over hidden states, shape ``[n_states]``.
  Entries sum to 1.0.

These matrices are derived deterministically from the COGANT program
graph (``ProgramGraph``), the extracted semantic mappings
(``SemanticMapping``), and the compiled state space (``StateSpaceModel``)
without any external numerical dependencies. COGANT cannot in general
recover the ground-truth parameters of an Active Inference model from
arbitrary source code, so the derivation uses principled heuristics:

* A comes from READS/OBSERVES edges between observation nodes and
  hidden-state nodes.
* B comes from WRITES/MUTATES edges from action nodes to hidden-state
  nodes.
* C comes from CONSTRAINT/PREFERENCE mapping confidence scores.
* D comes from CONFIGURATION nodes and any initial-value metadata.

All arithmetic uses plain Python lists — ``numpy`` is intentionally not a
dependency of this module.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


# Default probability masses used when no graph evidence is present.
# These follow the standard "high direct, low indirect" Active Inference
# placeholder convention used by the upstream PyMDP examples.
_DEFAULT_DIRECT_MASS = 0.9
_DEFAULT_INDIRECT_MASS = 0.1
_EPSILON = 1e-9


def _normalize_row(row: List[float]) -> List[float]:
    """Normalize a row of non-negative floats so that it sums to 1.0.

    If the row is empty or sums to zero, returns a uniform distribution.
    """
    total = sum(row)
    n = len(row)
    if n == 0:
        return []
    if total <= _EPSILON:
        return [1.0 / n] * n
    return [v / total for v in row]


def _normalize_vector(vec: List[float]) -> List[float]:
    """Normalize a non-negative vector so it sums to 1.0."""
    return _normalize_row(vec)


class GNNMatrices:
    """Derives GNN A/B/C/D matrices from COGANT analysis artifacts.

    The matrices are computed once on construction-time demand via the
    ``compute_*`` methods. Callers that need all four at once should use
    :meth:`to_dict` or :meth:`to_gnn_markdown_block`.
    """

    def __init__(
        self,
        graph: ProgramGraph,
        mappings: Any,
        state_space: StateSpaceModel,
    ) -> None:
        """Initialize the matrix deriver.

        Args:
            graph: The program graph with nodes and edges.
            mappings: Semantic mappings; accepted as either a ``dict``
                keyed by mapping ID or a list of ``SemanticMapping``.
            state_space: The compiled state space model.
        """
        self.graph = graph
        self.state_space = state_space

        # Normalize mappings to a list for convenient filtering while
        # preserving a stable ordering.
        if isinstance(mappings, dict):
            mapping_list: List[SemanticMapping] = list(mappings.values())
        elif isinstance(mappings, list):
            mapping_list = list(mappings)
        elif mappings is None:
            mapping_list = []
        else:
            mapping_list = list(mappings)
        self._mappings: List[SemanticMapping] = mapping_list

        # Enumerate spaces.
        self._hidden_states: List[SemanticMapping] = [
            m for m in self._mappings if m.kind == MappingKind.HIDDEN_STATE
        ]
        self._observations: List[SemanticMapping] = [
            m for m in self._mappings if m.kind == MappingKind.OBSERVATION
        ]
        self._actions: List[SemanticMapping] = [
            m
            for m in self._mappings
            if m.kind in (MappingKind.ACTION, MappingKind.POLICY)
        ]
        self._constraints: List[SemanticMapping] = [
            m
            for m in self._mappings
            if m.kind in (MappingKind.CONSTRAINT, MappingKind.PREFERENCE)
        ]

        # Fallback: if no HIDDEN_STATE semantic mappings are present but
        # the state space has variables, use those as the hidden-state
        # dimension so the matrices are always non-empty for real models.
        self._use_state_space_vars = (
            not self._hidden_states and bool(self.state_space.variables)
        )

    # ------------------------------------------------------------------
    # Dimensions
    # ------------------------------------------------------------------
    @property
    def n_states(self) -> int:
        """Number of hidden-state dimensions."""
        if self._use_state_space_vars:
            return len(self.state_space.variables)
        return len(self._hidden_states)

    @property
    def n_obs(self) -> int:
        """Number of observation dimensions."""
        if self._observations:
            return len(self._observations)
        # Fallback to compiled observation modalities.
        return len(self.state_space.observations)

    @property
    def n_actions(self) -> int:
        """Number of action dimensions (must be at least 1 for a valid B)."""
        if self._actions:
            return len(self._actions)
        n_act = len(self.state_space.actions)
        return n_act if n_act > 0 else 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _state_node_ids(self) -> List[str]:
        """Return the ordered list of graph node IDs backing hidden states."""
        if self._use_state_space_vars:
            return [v.node_id for v in self.state_space.variables.values()]
        ids: List[str] = []
        for mapping in self._hidden_states:
            if mapping.graph_fragment_node_ids:
                ids.append(mapping.graph_fragment_node_ids[0])
            else:
                ids.append("")
        return ids

    def _obs_node_ids(self) -> List[str]:
        """Return the ordered list of graph node IDs backing observations."""
        if self._observations:
            ids: List[str] = []
            for mapping in self._observations:
                if mapping.graph_fragment_node_ids:
                    ids.append(mapping.graph_fragment_node_ids[0])
                else:
                    ids.append("")
            return ids
        return [o.source_node_id for o in self.state_space.observations.values()]

    def _action_node_ids(self) -> List[str]:
        """Return the ordered list of graph node IDs backing actions."""
        if self._actions:
            ids: List[str] = []
            for mapping in self._actions:
                if mapping.graph_fragment_node_ids:
                    ids.append(mapping.graph_fragment_node_ids[0])
                else:
                    ids.append("")
            return ids
        return [a.controller_id for a in self.state_space.actions.values()]

    def _edges_from(self, node_id: str) -> List[Any]:
        """Return outgoing edges from ``node_id`` (or an empty list)."""
        if not node_id:
            return []
        return [e for e in self.graph.edges.values() if e.source_id == node_id]

    def _edges_to(self, node_id: str) -> List[Any]:
        """Return incoming edges to ``node_id`` (or an empty list)."""
        if not node_id:
            return []
        return [e for e in self.graph.edges.values() if e.target_id == node_id]

    # ------------------------------------------------------------------
    # A matrix — likelihood
    # ------------------------------------------------------------------
    def compute_A(self) -> List[List[float]]:
        """Compute the likelihood matrix ``A[n_obs x n_states]``.

        ``A[i][j] = P(observation_i | hidden_state_j)``.

        Derivation:
            For each observation ``i``, find the set of hidden-state
            nodes that it directly reads (READS/OBSERVES edges from the
            observation's node). Those direct reads receive a high
            probability mass; all other states share the residual mass
            uniformly. Each row is then normalized so it sums to 1.0.
        """
        n_obs = self.n_obs
        n_states = self.n_states
        if n_obs == 0 or n_states == 0:
            return []

        state_ids = self._state_node_ids()
        obs_ids = self._obs_node_ids()
        state_index = {nid: j for j, nid in enumerate(state_ids) if nid}

        direct_kinds = {EdgeKind.READS, EdgeKind.OBSERVES, EdgeKind.DEPENDS_ON}

        A: List[List[float]] = [[0.0] * n_states for _ in range(n_obs)]

        for i in range(n_obs):
            obs_node_id = obs_ids[i] if i < len(obs_ids) else ""
            direct: List[int] = []
            if obs_node_id:
                for edge in self._edges_from(obs_node_id):
                    if edge.kind in direct_kinds and edge.target_id in state_index:
                        j = state_index[edge.target_id]
                        if j not in direct:
                            direct.append(j)
                # Also look at incoming edges that go TO this observation
                # node (e.g., state->obs "OBSERVES" edges in the reverse
                # direction).
                for edge in self._edges_to(obs_node_id):
                    if edge.kind in direct_kinds and edge.source_id in state_index:
                        j = state_index[edge.source_id]
                        if j not in direct:
                            direct.append(j)

            n_direct = len(direct)
            n_indirect = n_states - n_direct
            if n_direct == 0:
                # Uniform likelihood if no edges found — safer than zero.
                A[i] = [1.0 / n_states] * n_states
                continue
            direct_share = _DEFAULT_DIRECT_MASS / n_direct
            indirect_share = (
                _DEFAULT_INDIRECT_MASS / n_indirect if n_indirect > 0 else 0.0
            )
            for j in range(n_states):
                A[i][j] = direct_share if j in direct else indirect_share
            A[i] = _normalize_row(A[i])

        return A

    # ------------------------------------------------------------------
    # B matrix — transition
    # ------------------------------------------------------------------
    def compute_B(self) -> List[List[List[float]]]:
        """Compute the transition tensor ``B[n_states x n_states x n_actions]``.

        ``B[next][cur][action] = P(next_state | current_state, action)``.

        Derivation:
            For each action ``k``, find the hidden-state nodes that it
            WRITES/MUTATES. Those destinations become high-probability
            successors of every current state; otherwise the transition
            defaults to an identity (stay) move. Every column
            ``(cur, action)`` is normalized so that it sums to 1.0.
        """
        n_states = self.n_states
        n_actions = self.n_actions
        if n_states == 0:
            return []

        state_ids = self._state_node_ids()
        action_ids = self._action_node_ids()
        state_index = {nid: j for j, nid in enumerate(state_ids) if nid}

        write_kinds = {EdgeKind.WRITES, EdgeKind.MUTATES}

        # Initialize to identity per action so that non-writing actions
        # leave the state unchanged (a valid default transition).
        B: List[List[List[float]]] = [
            [[0.0] * n_actions for _ in range(n_states)] for _ in range(n_states)
        ]
        for cur in range(n_states):
            for k in range(n_actions):
                B[cur][cur][k] = 1.0

        for k in range(n_actions):
            act_node_id = action_ids[k] if k < len(action_ids) else ""
            written: List[int] = []
            if act_node_id:
                for edge in self._edges_from(act_node_id):
                    if edge.kind in write_kinds and edge.target_id in state_index:
                        j = state_index[edge.target_id]
                        if j not in written:
                            written.append(j)

            if not written:
                # Already identity — nothing to update for this action.
                continue

            # For every current state ``cur``, redistribute mass so the
            # written destinations receive _DEFAULT_DIRECT_MASS and the
            # identity "stay" move receives _DEFAULT_INDIRECT_MASS.
            for cur in range(n_states):
                column = [0.0] * n_states
                n_w = len(written)
                direct_share = _DEFAULT_DIRECT_MASS / n_w
                for j in written:
                    column[j] = direct_share
                # Residual mass on the identity move (or uniform if the
                # current state is itself a written destination).
                if cur in written:
                    # Everything was written — normalize as-is.
                    pass
                else:
                    column[cur] += _DEFAULT_INDIRECT_MASS
                column = _normalize_row(column)
                for nxt in range(n_states):
                    B[nxt][cur][k] = column[nxt]

        return B

    # ------------------------------------------------------------------
    # C vector — log preferences over observations
    # ------------------------------------------------------------------
    def compute_C(self) -> List[float]:
        """Compute the log-preference vector ``C[n_obs]``.

        Derivation:
            Each observation receives a log-preference derived from the
            confidence scores of CONSTRAINT/PREFERENCE mappings whose
            graph fragments intersect with the observation's node set.
            Preferences with CONSTRAINT kind contribute a positive
            preference (the constraint describes a desired observation);
            absent any matching constraint, C defaults to 0.0 (neutral).
        """
        n_obs = self.n_obs
        if n_obs == 0:
            return []

        obs_node_ids = self._obs_node_ids()
        C: List[float] = [0.0] * n_obs

        for i in range(n_obs):
            obs_nid = obs_node_ids[i] if i < len(obs_node_ids) else ""
            if not obs_nid:
                continue
            # Sum signed log-preference contributions from constraints
            # that touch the observation's node (or any graph neighbor).
            total = 0.0
            for mapping in self._constraints:
                if obs_nid in mapping.graph_fragment_node_ids:
                    # Constraint: higher confidence → stronger preference.
                    sign = 1.0
                    if mapping.kind == MappingKind.CONSTRAINT:
                        # Constraints are "must hold" → strongly preferred.
                        sign = 1.0
                    elif mapping.kind == MappingKind.PREFERENCE:
                        # Preferences can be soft and may be aversive if
                        # the mapping semantic label starts with "avoid"
                        # or "reject".
                        label = (mapping.semantic_label or "").lower()
                        if label.startswith(("avoid", "reject", "!")):
                            sign = -1.0
                    total += sign * float(mapping.confidence_score or 0.0)
            C[i] = total

        return C

    # ------------------------------------------------------------------
    # D vector — initial prior over hidden states
    # ------------------------------------------------------------------
    def compute_D(self) -> List[float]:
        """Compute the initial prior ``D[n_states]``.

        Derivation:
            If any hidden state has an explicit ``default_value`` or an
            attached CONFIGURATION node with a value, concentrate mass
            on that state. Otherwise return a uniform prior. The vector
            always sums to 1.0.
        """
        n_states = self.n_states
        if n_states == 0:
            return []

        # Base: uniform prior.
        D: List[float] = [1.0 / n_states] * n_states

        if self._use_state_space_vars:
            # Bias toward any variable whose StateVariable has a default
            # value or a CONFIGURATION neighbor in the graph.
            biased = [0.0] * n_states
            any_bias = False
            for j, var in enumerate(self.state_space.variables.values()):
                bias = 1.0
                # Explicit domain/default bias.
                meta_default = getattr(var, "domain", None)
                if meta_default:
                    any_bias = True
                    bias += 1.0
                # CONFIGURATION neighbor in the graph → stronger prior.
                node_id = getattr(var, "node_id", "")
                if node_id and node_id in self.graph.nodes:
                    for edge in self._edges_to(node_id) + self._edges_from(node_id):
                        other_id = (
                            edge.source_id
                            if edge.target_id == node_id
                            else edge.target_id
                        )
                        other = self.graph.nodes.get(other_id)
                        if other and other.kind == NodeKind.CONFIGURATION:
                            any_bias = True
                            bias += 2.0
                            break
                biased[j] = bias
            if any_bias:
                D = _normalize_vector(biased)
            else:
                D = _normalize_vector(D)
        else:
            # Hidden-state semantic mappings: use mapping confidence as
            # a soft prior weight so that high-confidence hidden states
            # receive more prior mass.
            weights = [
                max(float(m.confidence_score or 0.0), _EPSILON)
                for m in self._hidden_states
            ]
            D = _normalize_vector(weights)

        return D

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of all four matrices.

        Returns:
            ``{"A": ..., "B": ..., "C": ..., "D": ..., "shapes": ...}``
        """
        A = self.compute_A()
        B = self.compute_B()
        C = self.compute_C()
        D = self.compute_D()
        return {
            "A": A,
            "B": B,
            "C": C,
            "D": D,
            "shapes": {
                "A": [len(A), len(A[0]) if A else 0],
                "B": [
                    len(B),
                    len(B[0]) if B else 0,
                    len(B[0][0]) if B and B[0] else 0,
                ],
                "C": [len(C)],
                "D": [len(D)],
            },
            "dimensions": {
                "n_states": self.n_states,
                "n_obs": self.n_obs,
                "n_actions": self.n_actions,
            },
        }

    def to_gnn_markdown_block(self) -> str:
        """Format the matrices as a GNN-compatible markdown block.

        Emits AII-style sections with ``rows=``, ``cols=``, ``depth=``
        bracket headers. This block is additive to the existing
        ``StateSpaceBlock`` / ``InitialParameterization`` sections; it is
        meant to be embedded as a COGANT extension.
        """
        A = self.compute_A()
        B = self.compute_B()
        C = self.compute_C()
        D = self.compute_D()

        lines: List[str] = []

        # --- A matrix ---
        if A:
            n_rows = len(A)
            n_cols = len(A[0])
            lines.append(f"A[[rows={n_rows}][cols={n_cols}]]")
            for row in A:
                lines.append("  " + " ".join(f"{v:.6f}" for v in row))
            lines.append("")

        # --- B tensor ---
        if B:
            n_rows = len(B)
            n_cols = len(B[0]) if B else 0
            n_depth = len(B[0][0]) if (B and B[0]) else 0
            lines.append(
                f"B[[rows={n_rows}][cols={n_cols}][depth={n_depth}]]"
            )
            for k in range(n_depth):
                lines.append(f"  # action={k}")
                for r in range(n_rows):
                    row_vals = [B[r][c][k] for c in range(n_cols)]
                    lines.append("  " + " ".join(f"{v:.6f}" for v in row_vals))
            lines.append("")

        # --- C vector ---
        if C:
            lines.append(f"C[[rows={len(C)}]]")
            for v in C:
                lines.append(f"  {v:.6f}")
            lines.append("")

        # --- D vector ---
        if D:
            lines.append(f"D[[rows={len(D)}]]")
            for v in D:
                lines.append(f"  {v:.6f}")
            lines.append("")

        return "\n".join(lines).rstrip()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_shapes(self) -> Tuple[bool, List[str]]:
        """Validate that all four matrices have the expected shapes.

        Returns:
            ``(ok, errors)`` where ``ok`` is True if no shape errors
            were found.
        """
        errors: List[str] = []
        A = self.compute_A()
        B = self.compute_B()
        C = self.compute_C()
        D = self.compute_D()

        n_s = self.n_states
        n_o = self.n_obs
        n_a = self.n_actions

        # A: n_obs x n_states, rows sum to 1.
        if n_o > 0 and n_s > 0:
            if len(A) != n_o:
                errors.append(f"A row count {len(A)} != n_obs {n_o}")
            elif A and any(len(row) != n_s for row in A):
                errors.append(f"A has inconsistent column count (expected {n_s})")
            else:
                for i, row in enumerate(A):
                    if abs(sum(row) - 1.0) > 1e-6:
                        errors.append(
                            f"A row {i} does not sum to 1 (sum={sum(row):.6f})"
                        )

        # B: n_states x n_states x n_actions
        if n_s > 0:
            if len(B) != n_s:
                errors.append(f"B first dim {len(B)} != n_states {n_s}")
            elif any(len(row) != n_s for row in B):
                errors.append(f"B second dim != n_states {n_s}")
            elif any(len(cell) != n_a for row in B for cell in row):
                errors.append(f"B third dim != n_actions {n_a}")

        # C: length n_obs
        if len(C) != n_o:
            errors.append(f"C length {len(C)} != n_obs {n_o}")

        # D: length n_states, sums to 1
        if len(D) != n_s:
            errors.append(f"D length {len(D)} != n_states {n_s}")
        elif D and abs(sum(D) - 1.0) > 1e-6:
            errors.append(f"D does not sum to 1 (sum={sum(D):.6f})")

        return (len(errors) == 0, errors)


__all__ = ["GNNMatrices"]
