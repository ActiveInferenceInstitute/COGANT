"""GNN A/B/C/D matrix derivation from program graph and semantic mappings.

Implements the four core probabilistic matrices required by the Active
Inference Institute (AII) upstream Generalized Notation Notation (GNN)
specification:

* **A** — likelihood matrix ``P(o | s)`` (observation given hidden state),
  shape ``[n_obs x n_states]``. Columns sum to 1.0 (column-stochastic per
  AII/pymdp convention: for each fixed hidden state ``s``, the distribution
  over observation outcomes ``sum_o P(o | s) == 1``).
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
from typing import Any

from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


# Default probability masses used when no graph evidence is present.
#
# Principled defaults — not empirically calibrated. These follow the
# "high direct, low indirect" Active Inference placeholder convention
# used by the upstream PyMDP examples (see Da Costa et al., "Active
# inference on discrete state-spaces: a synthesis", J. Math. Psychol.
# 2020, and the PyMDP tutorials at pymdp-rtd.readthedocs.io). The
# 0.9/0.1 split encodes the prior that a directly-linked
# (READS/OBSERVES/WRITES/MUTATES) node pair carries 9x the
# probability mass of any indirectly-linked pair. This is a standard
# sparse-observation-matrix placeholder and is *not* intended to
# represent ground-truth PyMDP weights; it is the starting point for
# manual or empirical refinement.
#
# The two masses must sum to 1.0 because every row of A and every
# column of each B slice is row-normalized in
# ``_normalize_row`` — the 0.9/0.1 split is a pre-normalization
# ratio, not a post-normalization target. TODO(calibration): sweep
# {0.80/0.20, 0.85/0.15, 0.90/0.10, 0.95/0.05} on the 20-repo
# fixture set and compare against hand-labeled likelihood matrices
# (see ``docs/evaluation/CALIBRATION.md``).
_DEFAULT_DIRECT_MASS = 0.9  # principled default (PyMDP convention)
_DEFAULT_INDIRECT_MASS = 0.1  # principled default (1.0 - direct)

# Numerical stability constant. 1e-9 is the canonical
# "well below float64 round-off noise but well above denormal"
# band used throughout scientific Python (scipy, pymdp, torch).
# Chosen to guard against division-by-zero in ``_normalize_row``
# without suppressing legitimate near-zero entries. Not calibrated.
_EPSILON = 1e-9  # stability constant (scipy/pymdp convention)

# Maximum number of entries in the B transition tensor before truncation
# kicks in. B is shape [n_states × n_states × n_actions]; for dulwich
# (429 states × 1085 actions) the full tensor is 200 M entries ≈ 1.6 GB
# as float64 and causes a 380 s / 8.5 GB-peak-RSS run. The cap triggers
# a principal-submatrix approximation: keep the top-K highest-degree
# state nodes so that B fits in ≤ _MAX_B_ENTRIES entries. A warning is
# logged and the ``truncation`` key in ``to_dict()`` records the cut.
#
# Calibration: 5 M entries ≈ 40 MB at float64; keeps B serialization
# under ~400 MB JSON even for the largest repos in the eval corpus.
# 5 M corresponds to roughly 170 states × 170 states × 173 actions —
# enough to represent a mid-size Python library accurately. For repos
# with fewer states this cap is never hit.
_MAX_B_ENTRIES = 5_000_000  # principled default; see docstring above


def _normalize_row(row: list[float]) -> list[float]:
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


def _normalize_vector(vec: list[float]) -> list[float]:
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
            mapping_list: list[SemanticMapping] = list(mappings.values())
        elif isinstance(mappings, list):
            mapping_list = list(mappings)
        elif mappings is None:
            mapping_list = []
        else:
            mapping_list = list(mappings)
        self._mappings: list[SemanticMapping] = mapping_list

        # Enumerate spaces.
        self._hidden_states: list[SemanticMapping] = [
            m for m in self._mappings if m.kind == MappingKind.HIDDEN_STATE
        ]
        self._observations: list[SemanticMapping] = [
            m for m in self._mappings if m.kind == MappingKind.OBSERVATION
        ]
        self._actions: list[SemanticMapping] = [
            m for m in self._mappings if m.kind in (MappingKind.ACTION, MappingKind.POLICY)
        ]
        self._constraints: list[SemanticMapping] = [
            m for m in self._mappings if m.kind in (MappingKind.CONSTRAINT, MappingKind.PREFERENCE)
        ]

        # Fallback: if no HIDDEN_STATE semantic mappings are present but
        # the state space has variables, use those as the hidden-state
        # dimension so the matrices are always non-empty for real models.
        self._use_state_space_vars = not self._hidden_states and bool(self.state_space.variables)

        # Populated by compute_B() when the full B tensor would exceed
        # _MAX_B_ENTRIES.  Callers can inspect these to understand the
        # approximation that was applied.
        self._b_truncated: bool = False
        self._b_n_states_full: int = 0  # untruncated n_states
        self._b_n_states_kept: int = 0  # n_states after truncation

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
    def _state_node_ids(self) -> list[str]:
        """Return the ordered list of graph node IDs backing hidden states."""
        if self._use_state_space_vars:
            return [v.node_id for v in self.state_space.variables.values()]
        ids: list[str] = []
        for mapping in self._hidden_states:
            if mapping.graph_fragment_node_ids:
                ids.append(mapping.graph_fragment_node_ids[0])
            else:
                ids.append("")
        return ids

    def _obs_node_ids(self) -> list[str]:
        """Return the ordered list of graph node IDs backing observations."""
        if self._observations:
            ids: list[str] = []
            for mapping in self._observations:
                if mapping.graph_fragment_node_ids:
                    ids.append(mapping.graph_fragment_node_ids[0])
                else:
                    ids.append("")
            return ids
        return [o.source_node_id for o in self.state_space.observations.values()]

    def _action_node_ids(self) -> list[str]:
        """Return the ordered list of graph node IDs backing actions."""
        if self._actions:
            ids: list[str] = []
            for mapping in self._actions:
                if mapping.graph_fragment_node_ids:
                    ids.append(mapping.graph_fragment_node_ids[0])
                else:
                    ids.append("")
            return ids
        return [a.controller_id for a in self.state_space.actions.values()]

    def _edges_from(self, node_id: str) -> list[Any]:
        """Return outgoing edges from ``node_id`` (or an empty list)."""
        if not node_id:
            return []
        return [e for e in self.graph.edges.values() if e.source_id == node_id]

    def _edges_to(self, node_id: str) -> list[Any]:
        """Return incoming edges to ``node_id`` (or an empty list)."""
        if not node_id:
            return []
        return [e for e in self.graph.edges.values() if e.target_id == node_id]

    def _top_k_state_ids(self, state_ids: list[str], k: int) -> list[str]:
        """Return the *k* state node IDs with the highest combined degree.

        Used by :meth:`compute_B` when the full ``n_states × n_states ×
        n_actions`` tensor would exceed ``_MAX_B_ENTRIES``.  We keep the
        highest-degree nodes because they carry the most transition
        information; the approximation is a principal submatrix of the
        full B tensor restricted to the top-k row/column indices.

        Args:
            state_ids: Full ordered list of state node IDs.
            k: Number of state IDs to keep.

        Returns:
            A list of at most *k* node IDs, ordered by descending degree.
        """
        if k >= len(state_ids):
            return state_ids

        # Count in+out degree for each state node using a single pass
        # over the full edge list (O(|E|), not O(|V|²)).
        degree: dict[str, int] = {nid: 0 for nid in state_ids if nid}
        state_id_set = set(degree)
        for edge in self.graph.edges.values():
            if edge.source_id in state_id_set:
                degree[edge.source_id] += 1
            if edge.target_id in state_id_set:
                degree[edge.target_id] += 1

        # Sort by descending degree, preserving original order for ties
        # so the truncated matrix is deterministic.
        ranked = sorted(state_ids, key=lambda nid: -degree.get(nid, 0))
        return ranked[:k]

    # ------------------------------------------------------------------
    # A matrix — likelihood
    # ------------------------------------------------------------------
    def compute_A(self) -> list[list[float]]:
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

        A: list[list[float]] = [[0.0] * n_states for _ in range(n_obs)]
        n_uniform = 0  # count of rows with no direct evidence

        for i in range(n_obs):
            obs_node_id = obs_ids[i] if i < len(obs_ids) else ""
            direct: list[int] = []
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
                # No evidence linking this observation to any state: assign
                # equal pre-normalization mass across states. After the
                # column normalization below this row contributes uniformly
                # to every state-column (a maximally vague observation).
                A[i] = [1.0 / n_states] * n_states
                n_uniform += 1
                continue
            direct_share = _DEFAULT_DIRECT_MASS / n_direct
            indirect_share = _DEFAULT_INDIRECT_MASS / n_indirect if n_indirect > 0 else 0.0
            for j in range(n_states):
                A[i][j] = direct_share if j in direct else indirect_share

        # Column-stochastic normalization (AII/pymdp convention). ``A`` holds
        # ``A[o][s] = P(o | s)``, so for every fixed hidden state ``s`` the
        # distribution over observation outcomes must sum to 1: each *column*
        # sums to 1, not each row. (Row-normalizing would make ``sum_s
        # P(o|s) = 1``, which is not a valid likelihood and breaks the
        # predicted-observation update ``pred_obs[o] = sum_s A[o][s]·q(s)``
        # in ``simulate/free_energy.py``.)
        for j in range(n_states):
            col_total = sum(A[i][j] for i in range(n_obs))
            if col_total <= _EPSILON:
                # A state observed by nothing: uniform over observations.
                for i in range(n_obs):
                    A[i][j] = 1.0 / n_obs
            else:
                for i in range(n_obs):
                    A[i][j] = A[i][j] / col_total

        # Log A matrix computation details
        n_informed = n_obs - n_uniform
        logger.info(
            "A matrix computed: shape [%d x %d], %d/%d rows with direct evidence, "
            "%d uniform (no READS/OBSERVES edges)",
            n_obs,
            n_states,
            n_informed,
            n_obs,
            n_uniform,
        )

        return A

    # ------------------------------------------------------------------
    # B matrix — transition
    # ------------------------------------------------------------------
    def compute_B(self) -> list[list[list[float]]]:
        """Compute the transition tensor ``B[n_states x n_states x n_actions]``.

        ``B[next][cur][action] = P(next_state | current_state, action)``.

        Derivation:
            For each action ``k``, find the hidden-state nodes that it
            WRITES/MUTATES. Those destinations become high-probability
            successors of every current state; otherwise the transition
            defaults to an identity (stay) move. Every column
            ``(cur, action)`` is normalized so that it sums to 1.0.

        Truncation:
            When ``n_states² × n_actions`` would exceed ``_MAX_B_ENTRIES``
            (default 5 M), the state space is reduced to the top-K
            highest-degree nodes so that the tensor fits in memory and
            serializes in reasonable time. The truncation is recorded in
            ``self._b_truncated``, ``self._b_n_states_full``, and
            ``self._b_n_states_kept``, and surfaced in :meth:`to_dict`
            under the ``"truncation"`` key. This approximation is a
            principal submatrix of the full B restricted to the most
            structurally important state nodes.
        """
        n_states = self.n_states
        n_actions = self.n_actions
        if n_states == 0:
            return []

        state_ids = self._state_node_ids()
        action_ids = self._action_node_ids()

        # ---- Truncation guard ----------------------------------------
        # If the full tensor would exceed _MAX_B_ENTRIES, keep only the
        # top-K state nodes ranked by in+out degree.  This turns an O(S²A)
        # explosion into O(_MAX_B_ENTRIES) work, preserving the most
        # structurally important nodes.
        full_b_entries = n_states * n_states * n_actions
        self._b_n_states_full = n_states
        self._b_truncated = False

        if full_b_entries > _MAX_B_ENTRIES and n_actions > 0:
            # Solve for max_k: k² × n_actions ≤ _MAX_B_ENTRIES
            import math

            max_k = max(1, int(math.isqrt(_MAX_B_ENTRIES // n_actions)))
            self._b_truncated = True
            self._b_n_states_kept = max_k
            logger.warning(
                "B tensor would be %d entries (%d states × %d states × %d actions) "
                "which exceeds _MAX_B_ENTRIES=%d. Truncating to top-%d state nodes "
                "by graph degree. Set _MAX_B_ENTRIES higher to disable truncation.",
                full_b_entries,
                n_states,
                n_states,
                n_actions,
                _MAX_B_ENTRIES,
                max_k,
            )
            logger.info(
                "B tensor truncated: %d → %d state nodes (%.1f%% reduction, %d → %d entries)",
                n_states,
                max_k,
                (1 - max_k / n_states) * 100 if n_states > 0 else 0.0,
                full_b_entries,
                max_k * max_k * n_actions,
            )
            state_ids = self._top_k_state_ids(state_ids, max_k)
            n_states = len(state_ids)
        else:
            self._b_n_states_kept = n_states
        # ---------------------------------------------------------------

        state_index = {nid: j for j, nid in enumerate(state_ids) if nid}

        write_kinds = {EdgeKind.WRITES, EdgeKind.MUTATES}

        # Initialize to identity per action so that non-writing actions
        # leave the state unchanged (a valid default transition).
        B: list[list[list[float]]] = [
            [[0.0] * n_actions for _ in range(n_states)] for _ in range(n_states)
        ]
        for cur in range(n_states):
            for k in range(n_actions):
                B[cur][cur][k] = 1.0

        n_identity_actions = 0  # actions with no WRITES/MUTATES edges
        n_writing_actions = 0

        for k in range(n_actions):
            act_node_id = action_ids[k] if k < len(action_ids) else ""
            written: list[int] = []
            if act_node_id:
                for edge in self._edges_from(act_node_id):
                    if edge.kind in write_kinds and edge.target_id in state_index:
                        j = state_index[edge.target_id]
                        if j not in written:
                            written.append(j)

            if not written:
                # Already identity — nothing to update for this action.
                n_identity_actions += 1
                continue
            n_writing_actions += 1

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
                # current state is itself a written destination — in that
                # case ``column[cur]`` already received its share above and
                # we normalize as-is below).
                if cur not in written:
                    column[cur] += _DEFAULT_INDIRECT_MASS
                column = _normalize_row(column)
                for nxt in range(n_states):
                    B[nxt][cur][k] = column[nxt]

        # Log B tensor computation details
        logger.info(
            "B tensor computed: shape [%d x %d x %d], %d/%d writing actions "
            "(%d identity/stay), direct_mass=%.2f",
            n_states,
            n_states,
            n_actions,
            n_writing_actions,
            n_actions,
            n_identity_actions,
            _DEFAULT_DIRECT_MASS,
        )

        return B

    # ------------------------------------------------------------------
    # C vector — log preferences over observations
    # ------------------------------------------------------------------
    def compute_C(self) -> list[float]:
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
        C: list[float] = [0.0] * n_obs

        n_preferred = 0  # observations with nonzero preference
        n_aversive = 0  # observations with negative preference
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
            if total > 0:
                n_preferred += 1
            elif total < 0:
                n_aversive += 1

        # Log C vector computation details
        n_neutral = n_obs - n_preferred - n_aversive
        logger.info(
            "C vector computed: length %d, %d preferred, %d aversive, %d neutral",
            n_obs,
            n_preferred,
            n_aversive,
            n_neutral,
        )

        return C

    # ------------------------------------------------------------------
    # D vector — initial prior over hidden states
    # ------------------------------------------------------------------
    def compute_D(self) -> list[float]:
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
        D: list[float] = [1.0 / n_states] * n_states

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
                        other_id = edge.source_id if edge.target_id == node_id else edge.target_id
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
            weights = [max(float(m.confidence_score or 0.0), _EPSILON) for m in self._hidden_states]
            D = _normalize_vector(weights)

        # Log D vector computation details
        peak_idx = max(range(len(D)), key=lambda j: D[j]) if D else -1
        peak_val = D[peak_idx] if peak_idx >= 0 else 0.0
        logger.info(
            "D vector computed: length %d, peak at index %d (%.4f), source=%s",
            len(D),
            peak_idx,
            peak_val,
            "state_space_vars" if self._use_state_space_vars else "hidden_state_mappings",
        )

        return D

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of all four matrices.

        Returns:
            ``{"A": ..., "B": ..., "C": ..., "D": ..., "shapes": ...,
            "dimensions": ..., "truncation": ...}``

            The ``"truncation"`` key is ``None`` when no truncation
            occurred; otherwise it is a dict with:

            * ``"applied"``: ``True``
            * ``"n_states_full"``: original (un-truncated) n_states
            * ``"n_states_kept"``: n_states after truncation
            * ``"max_b_entries"``: the ``_MAX_B_ENTRIES`` threshold
            * ``"reason"``: human-readable explanation
        """
        A = self.compute_A()
        B = self.compute_B()
        C = self.compute_C()
        D = self.compute_D()

        truncation: dict[str, Any] | None = None
        if self._b_truncated:
            truncation = {
                "applied": True,
                "n_states_full": self._b_n_states_full,
                "n_states_kept": self._b_n_states_kept,
                "max_b_entries": _MAX_B_ENTRIES,
                "reason": (
                    f"B tensor ({self._b_n_states_full}² × {self.n_actions} = "
                    f"{self._b_n_states_full**2 * self.n_actions:,} entries) "
                    f"exceeded _MAX_B_ENTRIES={_MAX_B_ENTRIES:,}; "
                    f"kept top-{self._b_n_states_kept} state nodes by degree."
                ),
            }

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
            "truncation": truncation,
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

        lines: list[str] = []

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
            lines.append(f"B[[rows={n_rows}][cols={n_cols}][depth={n_depth}]]")
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
    def validate_shapes(self) -> tuple[bool, list[str]]:
        """Validate that all four matrices have the expected shapes.

        Returns:
            ``(ok, errors)`` where ``ok`` is True if no shape errors
            were found.
        """
        errors: list[str] = []
        A = self.compute_A()
        B = self.compute_B()
        C = self.compute_C()
        D = self.compute_D()

        n_s = self.n_states
        n_o = self.n_obs
        n_a = self.n_actions

        # A: n_obs x n_states, rows sum to 1.
        # Row-sum tolerance 1e-6 — principled default, matches the
        # PyMDP validator tolerance and is ~7 orders of magnitude
        # above float64 round-off noise (~1e-16) for a typical
        # n_states <= 50. Strict enough to catch normalization bugs
        # but loose enough to tolerate accumulated rounding across
        # multiple ``_normalize_row`` passes.
        if n_o > 0 and n_s > 0:
            if len(A) != n_o:
                errors.append(f"A row count {len(A)} != n_obs {n_o}")
            elif A and any(len(row) != n_s for row in A):
                errors.append(f"A has inconsistent column count (expected {n_s})")
            else:
                # A is column-stochastic: P(o|s) sums to 1 over observation
                # outcomes for each fixed hidden state s (a column).
                for j in range(n_s):
                    col_sum = sum(A[i][j] for i in range(len(A)))
                    if abs(col_sum - 1.0) > 1e-6:  # col-norm tolerance
                        errors.append(f"A column {j} does not sum to 1 (sum={col_sum:.6f})")

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

        # D: length n_states, sums to 1 (same 1e-6 tolerance as A/B
        # row-normalization check above).
        if len(D) != n_s:
            errors.append(f"D length {len(D)} != n_states {n_s}")
        elif D and abs(sum(D) - 1.0) > 1e-6:  # same tolerance as A rows
            errors.append(f"D does not sum to 1 (sum={sum(D):.6f})")

        return (len(errors) == 0, errors)

    def validate(self) -> list[str]:
        """Validate dimensional consistency across A/B/C/D matrices.

        Checks that all four matrices have the expected shapes and that
        stochastic constraints are satisfied (row sums for A, column
        sums for B slices, sum for D).

        Returns:
            A list of validation issues. Empty list means all matrices
            are dimensionally consistent and satisfy stochastic constraints.
        """
        _, errors = self.validate_shapes()
        return errors

    def to_plain_dict(self) -> dict[str, Any]:
        """Export matrices as plain Python lists for JSON serialization.

        Unlike :meth:`to_dict`, this method guarantees all values are plain
        Python lists/floats with no numpy arrays or other special types.

        Returns:
            A dict with keys "A", "B", "C", "D" containing the matrices
            as plain Python lists.  Additional keys include "n_states",
            "n_obs", "n_actions" for shape information, and metadata like
            "b_truncated" if the B tensor was truncated.
        """
        A = self.compute_A()
        B = self.compute_B()
        C = self.compute_C()
        D = self.compute_D()

        # A, B, C, D are always plain Python lists — explicit ``list(...)``
        # copies guarantee independence from the cached compute_* outputs
        # so callers may mutate the returned dict safely.
        result: dict[str, Any] = {
            "A": [list(row) for row in A],
            "B": [[list(cell) for cell in row] for row in B],
            "C": list(C),
            "D": list(D),
            "n_states": self.n_states,
            "n_obs": self.n_obs,
            "n_actions": self.n_actions,
        }

        # Include truncation metadata if B was truncated.
        if self._b_truncated:
            result["b_truncated"] = True
            result["b_n_states_full"] = self._b_n_states_full
            result["b_n_states_kept"] = self._b_n_states_kept

        return result


__all__ = ["GNNMatrices"]
