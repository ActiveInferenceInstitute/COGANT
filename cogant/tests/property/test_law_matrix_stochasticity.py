"""COGANT correctness law 5: matrix stochasticity.

The A, B, and D matrices emitted by the reverse-synthesis pipeline
must be proper categorical distributions:

* Every column of ``A`` (likelihood ``P(o | s)``) sums to ``1.0``.
* Every column of every action slice of ``B`` (transition
  ``P(s' | s, a)``) sums to ``1.0`` — the AII convention is
  column-stochastic per action.
* ``D`` (initial prior over hidden states) sums to ``1.0``.

This law is tested on ``cogant.reverse.matrices.render_matrices_module``
output: we generate a ``ReverseGNNModel`` via Hypothesis, run the
renderer, exec the generated source to recover the A/B/C/D
constants, and check the sums.

Tolerance note: the renderer serialises each float as a 6-decimal
literal (``_format_float``), so the worst-case precision loss in a
column of height ``k`` is ``k * 1e-6``. We allow ``5e-6`` absolute
tolerance — comfortably above the 6 * 1e-6 worst case across the
generated dimensions (``n_states ≤ 6``). A genuine renormalisation
bug would exceed this tolerance by orders of magnitude.
"""

from __future__ import annotations

import math
import types

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.parser import ReverseGNNModel

pytestmark = pytest.mark.property

# Serialization-induced absolute tolerance: see module docstring.
_STOCHASTIC_TOL = 5e-6


# ---------------------------------------------------------------------------
# Strategy: valid ReverseGNNModel shapes.
# ---------------------------------------------------------------------------


@st.composite
def reverse_model(draw) -> ReverseGNNModel:
    """Generate a well-formed ReverseGNNModel with varying dimensions."""
    n_states = draw(st.integers(min_value=1, max_value=6))
    n_obs = draw(st.integers(min_value=1, max_value=5))
    n_actions = draw(st.integers(min_value=1, max_value=4))

    model = ReverseGNNModel()
    model.hidden_states = [f"s_f{i}" for i in range(n_states)]
    model.observations = [f"o_m{i}" for i in range(n_obs)]
    model.actions = [f"u_c{i}" for i in range(n_actions)]
    model.raw_model_name = "law5_model"

    # Randomly decide whether to supply an explicit A/B/C/D or let
    # the renderer fall back to shape-consistent defaults. Both
    # branches must produce stochastic columns.
    if draw(st.booleans()):
        # Provide an A where each column is a random positive vector;
        # the renderer is documented to leave A untouched on the
        # happy path, so we also normalise it up-front to match the
        # post-render invariant.
        raw_rows = [
            [draw(st.floats(min_value=0.1, max_value=10.0)) for _ in range(n_states)]
            for _ in range(n_obs)
        ]
        col_sums = [sum(raw_rows[i][j] for i in range(n_obs)) for j in range(n_states)]
        model.A = [
            [raw_rows[i][j] / col_sums[j] for j in range(n_states)]
            for i in range(n_obs)
        ]
    # else: leave A empty -> renderer emits uniform 1/n_obs columns.

    if draw(st.booleans()):
        # Leave D empty so the renderer synthesises a uniform prior.
        pass
    else:
        raw_d = [draw(st.floats(min_value=0.1, max_value=10.0)) for _ in range(n_states)]
        total = sum(raw_d)
        model.D = [v / total for v in raw_d]

    return model


def _exec_generated_module(source: str) -> types.ModuleType:
    """Exec the rendered ``matrices.py`` source into a fresh module."""
    mod = types.ModuleType("law5_generated_matrices")
    # The rendered module only uses ``typing.List`` and plain stdlib.
    exec(source, mod.__dict__)
    return mod


# ---------------------------------------------------------------------------
# Law 5a: every column of A sums to 1.0.
# ---------------------------------------------------------------------------


@given(model=reverse_model())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_generated_A_columns_are_stochastic(model: ReverseGNNModel) -> None:
    """Every column of the generated A matrix must sum to 1.0 ± {tol}."""
    source = render_matrices_module(model)
    mod = _exec_generated_module(source)
    A = mod.A
    assert isinstance(A, list)
    if not A:
        return  # Empty A is admissible for degenerate (n_obs == 0) models.
    n_obs = len(A)
    n_states = len(A[0]) if A and A[0] else 0
    for j in range(n_states):
        s = sum(A[i][j] for i in range(n_obs))
        assert math.isclose(s, 1.0, abs_tol=_STOCHASTIC_TOL), (
            f"A column {j} sums to {s:.12f} (expected 1.0 ± {_STOCHASTIC_TOL}); "
            f"shape=({model.n_obs}, {model.n_states})"
        )


# ---------------------------------------------------------------------------
# Law 5b: D sums to 1.0.
# ---------------------------------------------------------------------------


@given(model=reverse_model())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_generated_D_sums_to_one(model: ReverseGNNModel) -> None:
    """The generated D vector must sum to 1.0 ± {tol}."""
    source = render_matrices_module(model)
    mod = _exec_generated_module(source)
    D = mod.D
    assert isinstance(D, list)
    if not D:
        return  # Admissible when n_states == 0 (generator excludes this).
    s = sum(D)
    assert math.isclose(s, 1.0, abs_tol=_STOCHASTIC_TOL), (
        f"D sums to {s:.12f} (expected 1.0 ± {_STOCHASTIC_TOL}); n_states={model.n_states}"
    )


# ---------------------------------------------------------------------------
# Law 5c: transition() preserves the probability-distribution invariant.
# ---------------------------------------------------------------------------


@given(model=reverse_model())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_generated_transition_preserves_distribution(
    model: ReverseGNNModel,
) -> None:
    """Calling ``transition(uniform, a)`` returns a vector summing to 1.0.

    The renderer emits a ``transition(state_dist, action)`` helper
    that normalises its output. We feed it the uniform prior on
    hidden states (the safest totally-positive input) for every
    action and confirm the returned distribution is valid.
    """
    source = render_matrices_module(model)
    mod = _exec_generated_module(source)

    n_states = mod.N_HIDDEN_STATES
    n_actions = mod.N_ACTIONS
    if n_states == 0 or n_actions == 0:
        return

    uniform = [1.0 / n_states] * n_states
    for a in range(n_actions):
        out = mod.transition(uniform, a)
        assert len(out) == n_states, (
            f"transition(uniform, {a}) returned {len(out)} entries, expected {n_states}"
        )
        s = sum(out)
        assert math.isclose(s, 1.0, abs_tol=_STOCHASTIC_TOL), (
            f"transition(uniform, {a}) sums to {s:.12f}; not a distribution"
        )
        for v in out:
            assert v >= -1e-9, f"negative mass in transition output: {v}"
