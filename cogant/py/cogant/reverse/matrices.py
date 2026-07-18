"""Runtime Python code generation for GNN A/B/C/D matrices.

This module converts parsed ``ReverseGNNModel`` matrices into Python
source code that can be embedded in the synthesized package. The
generated code is deliberately dependency-free — no numpy, no pymdp —
so the resulting package runs with a standard-library-only Python
install, matching COGANT's preference for hermetic generated code.

Matrix semantics
----------------
* **A** (likelihood) — each column is a categorical distribution over
  observations given a hidden state. The generated code implements
  ``sample_obs(state_vec)`` via the forward equation ``P(o) = A · s``
  and a deterministic argmax selector.
* **B** (transition) — per action slice, the generated code computes
  the next-state distribution ``P(s') = B[:,:,a] · s``.
* **C** (log preferences) — a static vector of log-preferences over
  observations, used by the default policy implementation as the
  objective for expected free-energy minimisation (simplified).
* **D** (initial prior) — the initial state distribution; exposed as
  a module-level constant ``INITIAL_STATE_PRIOR``.

The generated matrix module is called ``matrices.py`` inside the
synthesized package and is imported by ``observe.py``, ``act.py``, and
``policy.py``.
"""

from __future__ import annotations

import math

from cogant.reverse.parser import (
    ReverseGNNModel,
    ReverseModelError,
    _normalize_reverse_dimensions,
)


def _format_float(value: float) -> str:
    """Format a float with bounded precision for embedding in source."""
    return f"{round(float(value), 6)!r}"


def _format_vector(vec: list[float]) -> str:
    """Format a 1D list as a Python list literal."""
    return "[" + ", ".join(_format_float(v) for v in vec) + "]"


def _format_matrix_2d(mat: list[list[float]]) -> str:
    """Format a 2D matrix as nested list literal with one row per line."""
    if not mat:
        return "[]"
    rows = ["    " + _format_vector(row) for row in mat]
    return "[\n" + ",\n".join(rows) + ",\n]"


def _format_tensor_3d(ten: list[list[list[float]]]) -> str:
    """Format a 3D tensor ``[n_states][n_states][n_actions]``."""
    if not ten:
        return "[]"
    outer_rows: list[str] = []
    for row in ten:
        inner = []
        for cell in row:
            inner.append(_format_vector(cell))
        outer_rows.append("    [" + ", ".join(inner) + "]")
    return "[\n" + ",\n".join(outer_rows) + ",\n]"


def _validate_matrix_semantics(model: ReverseGNNModel) -> None:
    """Reject incomplete or non-stochastic source matrix semantics.

    Reverse synthesis is a code-generation boundary, so silently creating a
    matrix here would make the generated package claim semantics that were
    never present in the source model. Empty matrices are valid only for the
    corresponding zero-dimensional model component.
    """
    _normalize_reverse_dimensions(model)
    n_states = model.n_states
    n_obs = model.n_obs
    n_actions = model.n_actions
    tolerance = 1e-6

    model_errors = model.validate()
    if model_errors:
        raise ReverseModelError("; ".join(model_errors))

    if model.hidden_states and not model.D:
        raise ReverseModelError("D is required to establish the hidden-state dimension")
    if model.observations and not model.C:
        raise ReverseModelError("C is required to establish the observation dimension")
    if model.actions and not model.B:
        raise ReverseModelError("B is required to establish the action dimension")

    if len(model.D) != n_states:
        raise ReverseModelError(
            f"D must contain {n_states} entries; received {len(model.D)}"
        )
    if model.D:
        if any(value < -tolerance or not math.isfinite(value) for value in model.D):
            raise ReverseModelError("D must contain finite non-negative probabilities")
        if not math.isclose(sum(model.D), 1.0, abs_tol=tolerance):
            raise ReverseModelError("D must sum to 1.0")

    if n_states and n_obs:
        if len(model.A) != n_obs or any(len(row) != n_states for row in model.A):
            raise ReverseModelError(f"A must have shape ({n_obs}, {n_states})")
        for column in range(n_states):
            values = [model.A[row][column] for row in range(n_obs)]
            if any(value < -tolerance or not math.isfinite(value) for value in values):
                raise ReverseModelError(
                    "A must contain finite non-negative probabilities"
                )
            if not math.isclose(sum(values), 1.0, abs_tol=tolerance):
                raise ReverseModelError("each A column must sum to 1.0")
    elif model.A:
        raise ReverseModelError(
            "A must be empty when either hidden states or observations are zero"
        )

    if n_states and n_actions:
        if len(model.B) != n_states or any(len(row) != n_states for row in model.B):
            raise ReverseModelError(
                f"B must have shape ({n_states}, {n_states}, {n_actions})"
            )
        if any(len(cell) != n_actions for row in model.B for cell in row):
            raise ReverseModelError(f"B must have depth {n_actions}")
        for action in range(n_actions):
            for source in range(n_states):
                values = [model.B[target][source][action] for target in range(n_states)]
                if any(value < -tolerance or not math.isfinite(value) for value in values):
                    raise ReverseModelError(
                        "B must contain finite non-negative probabilities"
                    )
                if not math.isclose(sum(values), 1.0, abs_tol=tolerance):
                    raise ReverseModelError("each B action column must sum to 1.0")
    elif model.B:
        raise ReverseModelError("B must be empty when hidden states or actions are zero")

    if len(model.C) != n_obs:
        raise ReverseModelError(
            f"C must contain {n_obs} entries; received {len(model.C)}"
        )
    if any(not math.isfinite(value) for value in model.C):
        raise ReverseModelError("C must contain finite values")

    if model.hidden_states and not model.degraded:
        declared_cards = [model.cardinalities.get(slot, 0) for slot in model.hidden_states]
        if any(card <= 0 for card in declared_cards):
            raise ReverseModelError(
                "every hidden-state declaration needs a positive cardinality"
            )
        product = math.prod(declared_cards)
        if product != n_states:
            raise ReverseModelError(
                "hidden-state cardinalities do not match the D dimension"
            )
    for label, declarations, dimension in (
        ("observation", model.observations, n_obs),
        ("action", model.actions, n_actions),
    ):
        if declarations and not model.degraded:
            cards = [model.cardinalities.get(slot, 0) for slot in declarations]
            if any(card <= 0 for card in cards):
                raise ReverseModelError(
                    f"every {label} declaration needs a positive cardinality"
                )
            if math.prod(cards) != dimension:
                raise ReverseModelError(
                    f"{label} cardinalities do not match the emitted matrix dimension"
                )


def render_matrices_module(model: ReverseGNNModel) -> str:
    """Render ``matrices.py`` for the synthesized package.

    The emitted module declares the four matrices as module-level
    constants plus three helper functions:

    * ``likelihood(state_dist)`` — returns ``P(o) = A · state_dist``.
    * ``transition(state_dist, action)`` — returns next-state distribution.
    * ``preference_score(obs_dist)`` — returns ``sum(C · obs_dist)``.

    Args:
        model: The parsed GNN model containing A/B/C/D.

    Returns:
        Full Python source text for ``matrices.py``.
    """
    _validate_matrix_semantics(model)
    # Validation normalizes legacy factorized declarations before dimensions
    # are rendered.  Re-read them afterwards so comments, constants, and
    # tensor literals cannot advertise a pre-normalization shape.
    n_states = model.n_states
    n_obs = model.n_obs
    n_actions = model.n_actions

    # Preserve source values exactly (within the bounded source formatting
    # precision). No matrix is invented when the source is incomplete.
    A = model.A
    B = model.B
    C = model.C
    D = model.D

    lines: list[str] = [
        '"""Generated Active Inference matrices from the GNN.',
        "",
        f"Model: {model.raw_model_name}",
        f"n_hidden_states={n_states}  n_observations={n_obs}  n_actions={n_actions}",
        "",
        "This module was synthesized by cogant.reverse.synthesizer and",
        "contains no external dependencies beyond the Python stdlib.",
        '"""',
        "",
        "import math",
        "from typing import List",
        "",
        f"N_HIDDEN_STATES: int = {n_states}",
        f"N_OBSERVATIONS: int = {n_obs}",
        f"N_ACTIONS: int = {n_actions}",
        f"DEGRADED_SOURCE_PROJECTION: bool = {model.degraded!r}",
        f"SOURCE_DIAGNOSTICS: list[str] = {model.diagnostics!r}",
        "",
        "# ---------------------------------------------------------------------",
        "# A matrix: likelihood P(observation | hidden_state)",
        f"# shape = [{n_obs} x {n_states}]; columns sum to 1.0",
        "# ---------------------------------------------------------------------",
        f"A: List[List[float]] = {_format_matrix_2d(A)}",
        "",
        "# ---------------------------------------------------------------------",
        "# B tensor: transition P(next_state | current_state, action)",
        f"# shape = [{n_states} x {n_states} x {n_actions}]",
        "# ---------------------------------------------------------------------",
        f"B: List[List[List[float]]] = {_format_tensor_3d(B)}",
        "",
        "# ---------------------------------------------------------------------",
        "# C vector: log-preferences over observations",
        f"# shape = [{n_obs}]",
        "# ---------------------------------------------------------------------",
        f"C: List[float] = {_format_vector(C)}",
        "",
        "# ---------------------------------------------------------------------",
        "# D vector: initial prior over hidden states",
        f"# shape = [{n_states}]; sums to 1.0",
        "# ---------------------------------------------------------------------",
        f"D: List[float] = {_format_vector(D)}",
        "",
        "INITIAL_STATE_PRIOR: List[float] = list(D)",
        "",
        "",
        "def likelihood(state_dist: List[float]) -> List[float]:",
        '    """Return P(observation) given a hidden-state distribution."""',
        "    if len(state_dist) != N_HIDDEN_STATES:",
        "        raise ValueError('state distribution has incompatible dimensions')",
        "    if any(value < 0.0 or not math.isfinite(value) for value in state_dist):",
        "        raise ValueError('state distribution must be finite and non-negative')",
        "    if state_dist and not math.isclose(sum(state_dist), 1.0, abs_tol=1e-6):",
        "        raise ValueError('state distribution must sum to 1.0')",
        "    if not A:",
        "        return []",
        "    n_obs = len(A)",
        "    n_states = len(state_dist)",
        "    result = [0.0] * n_obs",
        "    for i in range(n_obs):",
        "        row = A[i] if i < len(A) else []",
        "        for j in range(n_states):",
        "            result[i] += row[j] * state_dist[j]",
        "    return result",
        "",
        "",
        "def transition(state_dist: List[float], action: int = 0) -> List[float]:",
        '    """Return P(next hidden_state) given current distribution and action."""',
        "    if len(state_dist) != N_HIDDEN_STATES:",
        "        raise ValueError('state distribution has incompatible dimensions')",
        "    if any(value < 0.0 or not math.isfinite(value) for value in state_dist):",
        "        raise ValueError('state distribution must be finite and non-negative')",
        "    if state_dist and not math.isclose(sum(state_dist), 1.0, abs_tol=1e-6):",
        "        raise ValueError('state distribution must sum to 1.0')",
        "    if not B and not state_dist:",
        "        return []",
        "    if not B:",
        "        raise ValueError('transition matrix B is unavailable for this model')",
        "    n_states = len(state_dist)",
        "    n_actions = len(B[0][0]) if (B and B[0]) else 1",
        "    if action < 0 or action >= n_actions:",
        "        raise ValueError('action index is outside the declared B dimension')",
        "    k = action",
        "    result = [0.0] * n_states",
        "    for i in range(n_states):",
        "        row = B[i] if i < len(B) else []",
        "        for j in range(n_states):",
        "            slice_k = row[j][k]",
        "            result[i] += slice_k * state_dist[j]",
        "    # Normalize to keep result a proper distribution.",
        "    total = sum(result)",
        "    if total <= 0.0:",
        "        raise ValueError('transition matrix produced no probability mass')",
        "    result = [v / total for v in result]",
        "    return result",
        "",
        "",
        "def preference_score(obs_dist: List[float]) -> float:",
        '    """Return log-preference score <C, obs_dist> for policy selection."""',
        "    if len(obs_dist) != N_OBSERVATIONS:",
        "        raise ValueError('observation distribution has incompatible dimensions')",
        "    if any(value < 0.0 or not math.isfinite(value) for value in obs_dist):",
        "        raise ValueError('observation distribution must be finite and non-negative')",
        "    if not C:",
        "        return 0.0",
        "    score = 0.0",
        "    for i in range(N_OBSERVATIONS):",
        "        score += C[i] * obs_dist[i]",
        "    return score",
        "",
        "",
        "__all__ = [",
        '    "A", "B", "C", "D",',
        '    "N_HIDDEN_STATES", "N_OBSERVATIONS", "N_ACTIONS",',
        '    "INITIAL_STATE_PRIOR",',
        '    "likelihood", "transition", "preference_score",',
        "]",
        "",
    ]
    return "\n".join(lines)


__all__ = ["render_matrices_module"]
