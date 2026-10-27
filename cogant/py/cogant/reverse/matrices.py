"""Standalone matrix modules embedding the shared categorical numerical kernel."""

from __future__ import annotations

import inspect
import math

from cogant.reverse.parser import (
    ReverseGNNModel,
    ReverseModelError,
    _normalize_reverse_dimensions,
)
from cogant.runtime import categorical


def _format_float(value: float) -> str:
    return repr(float(value))


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
    if model.hidden_states and model.actions and not model.B:
        raise ReverseModelError("B is required to establish the action dimension")

    if len(model.D) != n_states:
        raise ReverseModelError(f"D must contain {n_states} entries; received {len(model.D)}")
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
                raise ReverseModelError("A must contain finite non-negative probabilities")
            if not math.isclose(sum(values), 1.0, abs_tol=tolerance):
                raise ReverseModelError("each A column must sum to 1.0")
    elif model.A:
        raise ReverseModelError(
            "A must be empty when either hidden states or observations are zero"
        )

    if n_states and n_actions:
        if len(model.B) != n_states or any(len(row) != n_states for row in model.B):
            raise ReverseModelError(f"B must have shape ({n_states}, {n_states}, {n_actions})")
        if any(len(cell) != n_actions for row in model.B for cell in row):
            raise ReverseModelError(f"B must have depth {n_actions}")
        for action in range(n_actions):
            for source in range(n_states):
                values = [model.B[target][source][action] for target in range(n_states)]
                if any(value < -tolerance or not math.isfinite(value) for value in values):
                    raise ReverseModelError("B must contain finite non-negative probabilities")
                if not math.isclose(sum(values), 1.0, abs_tol=tolerance):
                    raise ReverseModelError("each B action column must sum to 1.0")
    elif model.B:
        raise ReverseModelError("B must be empty when hidden states or actions are zero")

    if len(model.C) != n_obs:
        raise ReverseModelError(f"C must contain {n_obs} entries; received {len(model.C)}")
    if any(not math.isfinite(value) for value in model.C):
        raise ReverseModelError("C must contain finite values")

    if model.hidden_states and not model.degraded and model.matrix_source != "fenced":
        declared_cards = [model.cardinalities.get(slot, 0) for slot in model.hidden_states]
        if any(card <= 0 for card in declared_cards):
            raise ReverseModelError("every hidden-state declaration needs a positive cardinality")
        product = math.prod(declared_cards)
        if product != n_states:
            raise ReverseModelError("hidden-state cardinalities do not match the D dimension")
    for label, declarations, dimension, established in (
        ("observation", model.observations, n_obs, True),
        # Without hidden states there is no B tensor, so no emitted matrix
        # establishes an action dimension to cross-check declarations against.
        ("action", model.actions, n_actions, bool(model.B)),
    ):
        if declarations and established and not model.degraded and model.matrix_source != "fenced":
            cards = [model.cardinalities.get(slot, 0) for slot in declarations]
            if any(card <= 0 for card in cards):
                raise ReverseModelError(f"every {label} declaration needs a positive cardinality")
            if math.prod(cards) != dimension:
                raise ReverseModelError(
                    f"{label} cardinalities do not match the emitted matrix dimension"
                )


def render_matrices_module(model: ReverseGNNModel) -> str:
    """Embed the shared stdlib categorical kernel with the exact source matrices."""
    _validate_matrix_semantics(model)
    kernel = inspect.getsource(categorical).replace("from __future__ import annotations\n", "")
    constants = [
        f"N_HIDDEN_STATES: int = {model.n_states}",
        f"N_OBSERVATIONS: int = {model.n_obs}",
        f"N_ACTIONS: int = {model.n_actions}",
        f"DEGRADED_SOURCE_PROJECTION = {model.degraded!r}",
        f"SOURCE_DIAGNOSTICS = {model.diagnostics!r}",
        f"A = {_format_matrix_2d(model.A)}",
        f"B = {_format_tensor_3d(model.B)}",
        f"C = {_format_vector(model.C)}",
        f"D = {_format_vector(model.D)}",
        "INITIAL_STATE_PRIOR = list(D)",
    ]
    helpers = """
def likelihood(state_dist: list[float]) -> list[float]:
    return CategoricalModel(A, B, C, D).observe(state_dist)


def transition(state_dist: list[float], action: int = 0) -> list[float]:
    return CategoricalModel(A, B, C, D).predict(state_dist, action)


def preference_score(obs_dist: list[float]) -> float:
    return CategoricalModel(A, B, C, D).preference_score(obs_dist)


def expected_free_energy(state_dist: list[float], action: int) -> float:
    return CategoricalModel(A, B, C, D).score(state_dist, [action])


def score_preference_gradient(state_dist: list[float], policy: list[int]) -> list[float]:
    '''Return fixed-policy score sensitivity along the C observation axis.'''
    return CategoricalModel(A, B, C, D).score_preference_gradient(state_dist, policy)


def best_action(state_dist: list[float]) -> int:
    scores = CategoricalModel(A, B, C, D).action_scores(state_dist)
    return min(range(N_ACTIONS), key=scores.__getitem__)


def inference_step(state_dist: list[float], observation: int | None = None) -> CategoricalStep:
    return CategoricalModel(A, B, C, D).step(state_dist, observation)
"""
    return kernel + "\n" + "\n".join(constants) + "\n" + helpers


__all__ = ["render_matrices_module"]
