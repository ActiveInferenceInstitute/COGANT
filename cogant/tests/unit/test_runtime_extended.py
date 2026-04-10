"""Extended behavioral tests for cogant.runtime.

Covers convergence semantics, free energy monotonicity, action selection,
reproducibility, edge cases (zero steps, empty matrices), and integration
with the zoo/12_full_pomdp example.
"""

from __future__ import annotations

import math
import types
from pathlib import Path

from cogant.runtime.config import AgentConfig
from cogant.runtime.loop import AgentRuntime, AgentStep, run_n_steps
from cogant.runtime.metrics import free_energy, kl_divergence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _identity_system() -> types.SimpleNamespace:
    """2-state system with identity transitions (fixed point)."""
    return types.SimpleNamespace(
        A=[[1.0, 0.0], [0.0, 1.0]],
        B=[
            [[1.0], [0.0]],
            [[0.0], [1.0]],
        ],
        C=[0.0, 0.0],
        D=[0.5, 0.5],
        likelihood=lambda s: [
            sum(a * x for a, x in zip(row, s))
            for row in [[1.0, 0.0], [0.0, 1.0]]
        ],
        transition=lambda s, action=0: list(s),
        preference_score=lambda o: 0.0,
    )


def _biased_system() -> types.SimpleNamespace:
    """2-state system where C strongly prefers observation 0."""
    return types.SimpleNamespace(
        A=[[0.9, 0.1], [0.1, 0.9]],
        B=[
            [[1.0, 0.0], [0.0, 1.0]],
            [[0.0, 1.0], [1.0, 0.0]],
        ],
        C=[1.0, -1.0],
        D=[0.5, 0.5],
        likelihood=lambda s: [
            sum(a * x for a, x in zip(row, s))
            for row in [[0.9, 0.1], [0.1, 0.9]]
        ],
        transition=lambda s, action=0: _transition_2x2(s, action),
        preference_score=lambda o: sum(c * x for c, x in zip([1.0, -1.0], o)),
    )


def _transition_2x2(state_dist: list[float], action: int) -> list[float]:
    """B[:,:,action] @ state_dist for a 2x2x2 tensor."""
    B = [
        [[1.0, 0.0], [0.0, 1.0]],
        [[0.0, 1.0], [1.0, 0.0]],
    ]
    n = len(state_dist)
    result = [0.0] * n
    for i in range(n):
        for j in range(n):
            result[i] += B[i][j][action] * state_dist[j]
    total = sum(result)
    if total > 0:
        result = [v / total for v in result]
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_until_convergence_fixed_point() -> None:
    """Identity transition B (no state change) converges in <= 3 steps."""
    ns = _identity_system()
    rt = AgentRuntime(ns)
    cfg = AgentConfig(max_steps=100, convergence_threshold=1e-6)
    steps = rt.run_until_convergence(initial_state=[0.5, 0.5], cfg=cfg)
    # Identity system should converge almost immediately (step 2 at latest)
    assert len(steps) <= 3, f"Expected fast convergence, got {len(steps)} steps"
    assert len(steps) >= 1


def test_run_until_convergence_max_steps_honored() -> None:
    """cfg.max_steps=3 caps the number of returned steps even if not converged."""
    ns = _biased_system()
    rt = AgentRuntime(ns)
    cfg = AgentConfig(max_steps=3, convergence_threshold=1e-20)
    steps = rt.run_until_convergence(initial_state=[0.5, 0.5], cfg=cfg)
    assert len(steps) <= 3


def test_step_free_energy_decreases_on_preferred_obs() -> None:
    """Observing the preferred modality yields lower FE than the dispreferred.

    With a state biased toward s0, A[0] = [0.9, 0.1] gives higher P(obs=0)
    than A[1] = [0.1, 0.9] gives P(obs=1), so FE(obs=0) < FE(obs=1).
    """
    A = [[0.9, 0.1], [0.1, 0.9]]
    C = [1.0, -1.0]
    D = [0.5, 0.5]
    # Bias state toward s0 so obs 0 becomes more likely than obs 1
    state = [0.8, 0.2]

    fe_preferred = free_energy(state, obs_idx=0, A=A, C=C, D=D)
    fe_dispreferred = free_energy(state, obs_idx=1, A=A, C=C, D=D)

    # P(obs=0|state) = 0.9*0.8 + 0.1*0.2 = 0.74  (high)
    # P(obs=1|state) = 0.1*0.8 + 0.9*0.2 = 0.26  (low)
    # -> -log(0.74) < -log(0.26) -> FE(obs=0) < FE(obs=1)
    assert fe_preferred < fe_dispreferred, (
        f"FE(obs=0)={fe_preferred} should be < FE(obs=1)={fe_dispreferred}"
    )


def test_best_action_selects_preferred() -> None:
    """With C strongly preferring obs 0, the agent picks the action leading to obs 0."""
    ns = _biased_system()
    rt = AgentRuntime(ns)
    # State biased toward state 0 -> obs 0 more likely
    step = rt.step(state_dist=[0.8, 0.2], obs_idx=0, t=0)
    # Action 0 preserves state (identity), action 1 swaps.
    # Since state is biased toward s0 which maps to obs0 (preferred),
    # the agent should select action 0 (stay) to maintain preferred obs.
    assert step.action == 0, f"Expected action 0 (stay), got {step.action}"


def test_agent_runtime_from_matrices_dict_minimal() -> None:
    """from_matrices_dict with minimal valid matrices does not crash."""
    d = {
        "A": [[1.0]],
        "B": [[[1.0]]],
        "C": [0.0],
        "D": [1.0],
    }
    rt = AgentRuntime.from_matrices_dict(d)
    steps = rt.run_n_steps(2)
    assert len(steps) == 2
    for step in steps:
        assert math.isfinite(step.free_energy)


def test_agent_step_t_field_increments() -> None:
    """step.t == 0, 1, 2, ... in order across run_n_steps output."""
    ns = _biased_system()
    rt = AgentRuntime(ns)
    steps = rt.run_n_steps(7, initial_state=[0.5, 0.5])
    for i, step in enumerate(steps):
        assert step.t == i, f"Expected t={i}, got t={step.t}"


def test_agent_runtime_reproducible_with_same_seed() -> None:
    """Same initial state and matrices -> same action sequence (deterministic)."""
    ns = _biased_system()
    rt1 = AgentRuntime(ns)
    rt2 = AgentRuntime(ns)

    steps1 = rt1.run_n_steps(10, initial_state=[0.6, 0.4])
    steps2 = rt2.run_n_steps(10, initial_state=[0.6, 0.4])

    actions1 = [s.action for s in steps1]
    actions2 = [s.action for s in steps2]
    assert actions1 == actions2, "Identical setup should yield identical actions"

    states1 = [s.state_dist for s in steps1]
    states2 = [s.state_dist for s in steps2]
    for s1, s2 in zip(states1, states2):
        for a, b in zip(s1, s2):
            assert abs(a - b) < 1e-12


def test_free_energy_lower_for_better_prediction() -> None:
    """Concentrated A (good predictor) yields lower FE than uniform A."""
    state = [0.7, 0.3]
    D = [0.5, 0.5]
    C = [0.0, 0.0]

    # Good predictor: obs 0 strongly linked to state 0
    A_good = [[0.95, 0.05], [0.05, 0.95]]
    # Bad predictor: uniform likelihood (no information)
    A_bad = [[0.5, 0.5], [0.5, 0.5]]

    fe_good = free_energy(state, obs_idx=0, A=A_good, C=C, D=D)
    fe_bad = free_energy(state, obs_idx=0, A=A_bad, C=C, D=D)

    # Good predictor has higher P(obs=0|state) when state is biased to s0
    # -> lower surprise -> lower FE
    assert fe_good < fe_bad, (
        f"FE(good A)={fe_good} should be < FE(bad A)={fe_bad}"
    )


def test_convergence_metric_kl_non_negative() -> None:
    """KL divergence between any two valid distributions is >= 0.

    Only tests distributions where q has no zero entries (KL is
    undefined when q_i=0 and p_i>0, so we restrict to strictly
    positive q).
    """
    distributions = [
        [0.5, 0.5],
        [0.9, 0.1],
        [0.1, 0.9],
        [0.01, 0.99],
        [0.333, 0.333, 0.334],
        [0.1, 0.2, 0.7],
    ]
    for p in distributions:
        for q in distributions:
            if len(p) == len(q):
                kl = kl_divergence(p, q)
                assert kl >= -1e-9, f"KL({p}, {q}) = {kl} is negative"


def test_runtime_with_zoo_full_pomdp() -> None:
    """Build a 5-state POMDP matching zoo/12_full_pomdp, run 5 steps via AgentRuntime.

    The parser does not populate hidden_states for all GNN formats, so we
    construct the ReverseGNNModel directly using the InitialParameterization
    values from the zoo example.
    """
    from cogant.reverse.parser import ReverseGNNModel
    from cogant.reverse.callable import MatrixFunctions

    # Values from zoo/12_full_pomdp/model.gnn.md InitialParameterization
    n = 5
    accuracy = 0.8
    off_diag = (1.0 - accuracy) / (n - 1)  # 0.05
    A = [
        [accuracy if i == j else off_diag for j in range(n)]
        for i in range(n)
    ]
    # Identity transition tensor (3 actions, all identity)
    B = [
        [[1.0 if i == j else 0.0 for _ in range(3)] for j in range(n)]
        for i in range(n)
    ]
    C = [0.05, 0.05, 0.80, 0.05, 0.05]
    D = [0.2] * n

    model = ReverseGNNModel(
        model_name="full_pomdp",
        raw_model_name="full_pomdp",
        hidden_states=[f"s_f{i}" for i in range(n)],
        observations=[f"o_m{i}" for i in range(n)],
        actions=[f"u_c{i}" for i in range(3)],
        A=A,
        B=B,
        C=C,
        D=D,
    )
    assert model.n_states == 5
    assert model.n_obs == 5

    mf = MatrixFunctions(model)
    # MatrixFunctions stores matrices as private attrs (_A, _B, etc.)
    # but AgentRuntime expects public A, B, C, D attributes.
    # Wrap with a namespace that exposes both matrices and callables.
    ns = types.SimpleNamespace(
        A=mf._A, B=mf._B, C=mf._C, D=mf._D,
        likelihood=mf.likelihood,
        transition=mf.transition,
        preference_score=mf.preference_score,
    )
    rt = AgentRuntime(ns)
    steps = rt.run_n_steps(5)
    assert len(steps) == 5
    for step in steps:
        assert math.isfinite(step.free_energy)
        assert abs(sum(step.state_dist) - 1.0) < 1e-6


def test_agent_config_validates_max_steps() -> None:
    """max_steps=0 means run_until_convergence returns an empty list."""
    ns = _biased_system()
    rt = AgentRuntime(ns)
    cfg = AgentConfig(max_steps=0, convergence_threshold=1e-4)
    steps = rt.run_until_convergence(initial_state=[0.5, 0.5], cfg=cfg)
    assert steps == []


def test_run_n_steps_with_zero_returns_empty() -> None:
    """run_n_steps(0, ...) returns an empty list."""
    ns = _biased_system()
    rt = AgentRuntime(ns)
    steps = rt.run_n_steps(0, initial_state=[0.5, 0.5])
    assert steps == []
