"""Tests for cogant.reverse.callable — runtime-callable matrix functions.

Validates that MatrixFunctions provides numerically identical results to
the code-generated matrices module (render_matrices_module) without any
exec() or code generation.

No mocks: all tests use real in-memory ReverseGNNModel instances.
"""

from __future__ import annotations

import math

from cogant.reverse.callable import MatrixFunctions, make_matrix_functions
from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.parser import ReverseGNNModel, parse_gnn

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_GNN = """\
## ModelName
TestModel

## StateSpaceBlock
s_f0[3,1,type=int]
s_f1[2,1,type=int]
s_f2[2,1,type=int]
o_m0[2,1,type=float]
o_m1[2,1,type=float]
u_c0[4,1,type=int]

## Connections
(D_f0) > (s_f0)

## InitialParameterization
D_f0={ (0.6, 0.2, 0.2) }
D_f1={ (0.5, 0.5) }
D_f2={ (0.3, 0.7) }
C_m0={ (0.8, 0.2) }
C_m1={ (0.4, 0.6) }
A_m0={ ( (0.9, 0.05, 0.05), (0.1, 0.8, 0.1) ) }

## ActInfOntologyAnnotation
s_f0=HiddenState
s_f1=HiddenState
s_f2=HiddenState
o_m0=Observation
o_m1=Observation
u_c0=Action

## State Space

### Active Inference Matrices

```gnn-matrices
A[[rows=2][cols=3]]
0.9 0.05 0.05
0.1 0.8 0.1
B[[rows=3][cols=3][depth=2]]
# action=0
1.0 0.0 0.0
0.0 1.0 0.0
0.0 0.0 1.0
# action=1
0.0 1.0 0.0
0.0 0.0 1.0
1.0 0.0 0.0
D[[rows=3][cols=1]]
0.5
0.3
0.2
C[[rows=2][cols=1]]
0.8
0.2
```
"""


def _make_model() -> ReverseGNNModel:
    """Parse the minimal GNN fixture into a model."""
    return parse_gnn(MINIMAL_GNN)


def _make_no_actions_model() -> ReverseGNNModel:
    """Create a model with n_actions=0 for edge-case testing."""
    m = ReverseGNNModel(
        model_name="no_actions",
        raw_model_name="NoActions",
        hidden_states=["s_f0", "s_f1"],
        observations=["o_m0"],
        actions=[],
        A=[[0.6, 0.4], [0.3, 0.7]],
        B=[],
        C=[0.5, 0.5],
        D=[0.5, 0.5],
    )
    return m


# ---------------------------------------------------------------------------
# Core instantiation
# ---------------------------------------------------------------------------


def test_matrix_functions_from_model() -> None:
    """MatrixFunctions(model) instantiates without error."""
    model = _make_model()
    mf = MatrixFunctions(model)
    assert mf is not None


# ---------------------------------------------------------------------------
# likelihood
# ---------------------------------------------------------------------------


def test_likelihood_uniform_state() -> None:
    """likelihood([1/3, 1/3, 1/3]) with 2x3 A produces len == 2."""
    model = _make_model()
    mf = MatrixFunctions(model)
    result = mf.likelihood([1.0 / 3, 1.0 / 3, 1.0 / 3])
    assert len(result) == 2


def test_likelihood_sums_approx_one() -> None:
    """For row-stochastic A with uniform state, likelihood sums to n_obs/n_states.

    Each row of A sums to 1.0 (row-stochastic). With uniform state
    [1/n, 1/n, 1/n], each obs_i = (1/n)*sum_j(A[i][j]) = 1/n.
    Total = n_obs * (1/n_states). For a column-stochastic A the sum
    would be 1.0, but our fixture A is row-stochastic, so we verify
    each element is non-negative and the total is consistent.
    """
    model = _make_model()
    mf = MatrixFunctions(model)
    result = mf.likelihood([1.0 / 3, 1.0 / 3, 1.0 / 3])
    # Each element should be non-negative
    assert all(v >= 0.0 for v in result)
    # Each row of A sums to 1.0 => each obs element = 1/3
    # Total = 2/3 for a 2x3 row-stochastic A with uniform input
    expected_sum = len(result) / 3.0
    assert abs(sum(result) - expected_sum) < 1e-9


# ---------------------------------------------------------------------------
# transition
# ---------------------------------------------------------------------------


def test_transition_normalized() -> None:
    """sum(transition(uniform, 0)) is approximately 1.0."""
    model = _make_model()
    mf = MatrixFunctions(model)
    result = mf.transition([1.0 / 3, 1.0 / 3, 1.0 / 3], action=0)
    assert abs(sum(result) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# prior
# ---------------------------------------------------------------------------


def test_prior_sums_to_one() -> None:
    """sum(prior()) is approximately 1.0 for non-empty D."""
    model = _make_model()
    mf = MatrixFunctions(model)
    result = mf.prior()
    assert len(result) > 0
    assert abs(sum(result) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# preference_score
# ---------------------------------------------------------------------------


def test_preference_score_type() -> None:
    """preference_score returns a float."""
    model = _make_model()
    mf = MatrixFunctions(model)
    score = mf.preference_score([0.5, 0.5])
    assert isinstance(score, float)


# ---------------------------------------------------------------------------
# expected_free_energy
# ---------------------------------------------------------------------------


def test_expected_free_energy_finite() -> None:
    """EFE returns a finite float for valid state_dist."""
    model = _make_model()
    mf = MatrixFunctions(model)
    efe = mf.expected_free_energy([1.0 / 3, 1.0 / 3, 1.0 / 3], action=0)
    assert isinstance(efe, float)
    assert math.isfinite(efe)


# ---------------------------------------------------------------------------
# best_action
# ---------------------------------------------------------------------------


def test_best_action_type() -> None:
    """best_action returns an int."""
    model = _make_model()
    mf = MatrixFunctions(model)
    action = mf.best_action([1.0 / 3, 1.0 / 3, 1.0 / 3])
    assert isinstance(action, int)


def test_best_action_no_actions_returns_zero() -> None:
    """Model with n_actions=0 returns best_action == 0."""
    model = _make_no_actions_model()
    mf = MatrixFunctions(model)
    action = mf.best_action([0.5, 0.5])
    assert action == 0


# ---------------------------------------------------------------------------
# from_gnn_text convenience constructor
# ---------------------------------------------------------------------------


def test_from_gnn_text() -> None:
    """MatrixFunctions.from_gnn_text(MINIMAL_GNN) works end-to-end."""
    mf = MatrixFunctions.from_gnn_text(MINIMAL_GNN)
    assert mf is not None
    result = mf.likelihood([1.0 / 3, 1.0 / 3, 1.0 / 3])
    assert len(result) == 2


# ---------------------------------------------------------------------------
# make_matrix_functions convenience wrapper
# ---------------------------------------------------------------------------


def test_make_matrix_functions_wrapper() -> None:
    """make_matrix_functions(model) returns a MatrixFunctions instance."""
    model = _make_model()
    mf = make_matrix_functions(model)
    assert isinstance(mf, MatrixFunctions)


# ---------------------------------------------------------------------------
# Numerical equivalence with render_matrices_module (exec'd generated code)
# ---------------------------------------------------------------------------


def _exec_generated_module(model: ReverseGNNModel) -> dict[str, object]:
    """Generate and exec the matrices module, returning its namespace."""
    source = render_matrices_module(model)
    ns: dict[str, object] = {}
    exec(source, ns)  # noqa: S102 — intentional for test comparison
    return ns


def test_likelihood_matches_generated_code() -> None:
    """Callable likelihood is numerically identical to generated code."""
    model = _make_model()
    mf = MatrixFunctions(model)
    ns = _exec_generated_module(model)

    state_dist = [0.5, 0.3, 0.2]
    callable_result = mf.likelihood(state_dist)
    generated_fn = ns["likelihood"]
    assert callable(generated_fn)
    generated_result = generated_fn(state_dist)

    assert len(callable_result) == len(generated_result)
    for a, b in zip(callable_result, generated_result, strict=False):
        assert abs(a - b) < 1e-9, f"likelihood mismatch: {a} vs {b}"


def test_transition_matches_generated_code() -> None:
    """Callable transition is numerically identical to generated code."""
    model = _make_model()
    mf = MatrixFunctions(model)
    ns = _exec_generated_module(model)

    state_dist = [0.5, 0.3, 0.2]
    for action in range(2):
        callable_result = mf.transition(state_dist, action=action)
        generated_fn = ns["transition"]
        assert callable(generated_fn)
        generated_result = generated_fn(state_dist, action)

        assert len(callable_result) == len(generated_result)
        for a, b in zip(callable_result, generated_result, strict=False):
            assert abs(a - b) < 1e-9, f"transition(action={action}) mismatch: {a} vs {b}"


def test_expected_free_energy_empty_distribution() -> None:
    """EFE returns inf for empty distribution."""
    model = _make_model()
    mf = MatrixFunctions(model)
    efe = mf.expected_free_energy([], action=0)
    assert efe == float("inf")
