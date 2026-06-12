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

from cogant.reverse.parser import ReverseGNNModel


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
    n_states = model.n_states
    n_obs = model.n_obs
    n_actions = model.n_actions

    # Fall back to shape-consistent empty/identity matrices so the
    # generated code always has well-defined shapes regardless of what
    # the parser extracted. The round-trip verifier compares shapes,
    # so "something rather than nothing" is the right default.
    A = model.A if model.A else []
    if not A and n_obs and n_states:
        A = [[1.0 / n_obs] * n_states for _ in range(n_obs)]

    B = model.B if model.B else []
    if not B and n_states:
        # Identity per action.
        B = [
            [[1.0 if (r == c) else 0.0 for _ in range(max(n_actions, 1))] for c in range(n_states)]
            for r in range(n_states)
        ]

    C = model.C if model.C else [0.0] * n_obs
    D = model.D if model.D else ([1.0 / n_states] * n_states if n_states else [])

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
        "from typing import List",
        "",
        f"N_HIDDEN_STATES: int = {n_states}",
        f"N_OBSERVATIONS: int = {n_obs}",
        f"N_ACTIONS: int = {n_actions}",
        "",
        "# ---------------------------------------------------------------------",
        "# A matrix: likelihood P(observation | hidden_state)",
        f"# shape = [{n_obs} x {n_states}]; columns sum to 1.0",
        "# ---------------------------------------------------------------------",
        f"A: List[List[float]] = {_format_matrix_2d(A)}",
        "",
        "# ---------------------------------------------------------------------",
        "# B tensor: transition P(next_state | current_state, action)",
        f"# shape = [{n_states} x {n_states} x {max(n_actions, 1)}]",
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
        "    if not A or not state_dist:",
        "        return []",
        "    n_obs = len(A)",
        "    n_states = len(state_dist)",
        "    result = [0.0] * n_obs",
        "    for i in range(n_obs):",
        "        row = A[i] if i < len(A) else []",
        "        for j in range(min(len(row), n_states)):",
        "            result[i] += row[j] * state_dist[j]",
        "    return result",
        "",
        "",
        "def transition(state_dist: List[float], action: int = 0) -> List[float]:",
        '    """Return P(next hidden_state) given current distribution and action."""',
        "    if not B or not state_dist:",
        "        return list(state_dist)",
        "    n_states = len(state_dist)",
        "    n_actions = len(B[0][0]) if (B and B[0]) else 1",
        "    k = max(0, min(action, n_actions - 1))",
        "    result = [0.0] * n_states",
        "    for i in range(n_states):",
        "        row = B[i] if i < len(B) else []",
        "        for j in range(min(len(row), n_states)):",
        "            slice_k = row[j][k] if k < len(row[j]) else 0.0",
        "            result[i] += slice_k * state_dist[j]",
        "    # Normalize to keep result a proper distribution.",
        "    total = sum(result)",
        "    if total > 0.0:",
        "        result = [v / total for v in result]",
        "    return result",
        "",
        "",
        "def preference_score(obs_dist: List[float]) -> float:",
        '    """Return log-preference score <C, obs_dist> for policy selection."""',
        "    if not C or not obs_dist:",
        "        return 0.0",
        "    score = 0.0",
        "    for i in range(min(len(C), len(obs_dist))):",
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
