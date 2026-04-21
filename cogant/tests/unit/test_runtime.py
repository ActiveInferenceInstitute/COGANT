"""Tests for cogant.runtime — Active Inference agent loop.

Covers AgentStep structure, run_n_steps, state normalization,
free energy computation, convergence halting, from_matrices_dict,
single-state agents, and integration with rendered matrices modules.
"""

from __future__ import annotations

import math
import types

from cogant.runtime import AgentConfig, AgentRuntime, AgentStep, run_n_steps, run_until_convergence
from cogant.runtime.metrics import free_energy, kl_divergence


def _make_simple_matrices_ns() -> types.SimpleNamespace:
    """Build a minimal 2-state, 2-obs, 2-action matrices namespace."""
    return types.SimpleNamespace(
        A=[[0.9, 0.1], [0.1, 0.9]],
        B=[
            [[1.0, 0.0], [0.0, 1.0]],
            [[0.0, 1.0], [1.0, 0.0]],
        ],
        C=[1.0, -1.0],
        D=[0.5, 0.5],
        likelihood=lambda state_dist: [
            sum(a * s for a, s in zip(row, state_dist, strict=False))
            for row in [[0.9, 0.1], [0.1, 0.9]]
        ],
        transition=lambda state_dist, action=0: _transition_helper(state_dist, action),
        preference_score=lambda obs_dist: sum(
            c * o for c, o in zip([1.0, -1.0], obs_dist, strict=False)
        ),
    )


def _transition_helper(state_dist: list[float], action: int) -> list[float]:
    """Compute B[:,:,action] @ state_dist for the simple 2x2x2 B tensor."""
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


def test_agent_step_is_dataclass() -> None:
    """AgentStep has fields t, state_dist, obs, action, free_energy."""
    step = AgentStep(t=0, state_dist=[0.5, 0.5], obs=0, action=1, free_energy=0.42)
    assert step.t == 0
    assert step.state_dist == [0.5, 0.5]
    assert step.obs == 0
    assert step.action == 1
    assert abs(step.free_energy - 0.42) < 1e-9


def test_run_n_steps_length() -> None:
    """run_n_steps(5, ...) returns exactly 5 steps."""
    ns = _make_simple_matrices_ns()
    rt = AgentRuntime(ns)
    steps = rt.run_n_steps(5, initial_state=[0.5, 0.5])
    assert len(steps) == 5
    for i, step in enumerate(steps):
        assert step.t == i


def test_state_dist_normalized_at_each_step() -> None:
    """sum(step.state_dist) is approximately 1.0 for every step."""
    ns = _make_simple_matrices_ns()
    rt = AgentRuntime(ns)
    steps = rt.run_n_steps(10, initial_state=[0.5, 0.5])
    for step in steps:
        total = sum(step.state_dist)
        assert abs(total - 1.0) < 1e-6, f"step {step.t}: sum={total}"


def test_free_energy_finite() -> None:
    """free_energy(uniform, uniform, A, C) returns a finite float."""
    A = [[0.5, 0.5], [0.5, 0.5]]
    C = [0.0, 0.0]
    D = [0.5, 0.5]
    state = [0.5, 0.5]
    obs_idx = 0
    fe = free_energy(state, obs_idx, A, C, D)
    assert math.isfinite(fe), f"free_energy was {fe}"


def test_convergence_halts() -> None:
    """run_until_convergence on a fixed-point system halts in < 100 steps.

    A 2-state system with identity transitions converges immediately
    because the state distribution does not change between steps.
    """
    ns = types.SimpleNamespace(
        A=[[1.0, 0.0], [0.0, 1.0]],
        B=[
            [[1.0], [0.0]],
            [[0.0], [1.0]],
        ],
        C=[0.0, 0.0],
        D=[0.5, 0.5],
        likelihood=lambda s: [
            sum(a * x for a, x in zip(row, s, strict=False)) for row in [[1.0, 0.0], [0.0, 1.0]]
        ],
        transition=lambda s, action=0: list(s),
        preference_score=lambda o: 0.0,
    )
    cfg = AgentConfig(max_steps=100, convergence_threshold=1e-6)
    rt = AgentRuntime(ns)
    steps = rt.run_until_convergence(initial_state=[0.5, 0.5], cfg=cfg)
    assert len(steps) < 100, f"Took {len(steps)} steps, expected convergence"
    assert len(steps) >= 1


def test_from_matrices_dict() -> None:
    """AgentRuntime.from_matrices_dict works with a minimal {A,B,C,D}."""
    d = {
        "A": [[0.7, 0.3], [0.3, 0.7]],
        "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        "C": [0.5, -0.5],
        "D": [0.6, 0.4],
    }
    rt = AgentRuntime.from_matrices_dict(d)
    steps = rt.run_n_steps(3, initial_state=[0.6, 0.4])
    assert len(steps) == 3
    for step in steps:
        assert math.isfinite(step.free_energy)


def test_single_state_agent() -> None:
    """AgentRuntime with n_states=1 runs without error."""
    ns = types.SimpleNamespace(
        A=[[1.0]],
        B=[[[1.0]]],
        C=[0.0],
        D=[1.0],
        likelihood=lambda s: [sum(a * x for a, x in zip([1.0], s, strict=False))],
        transition=lambda s, action=0: [1.0],
        preference_score=lambda o: 0.0,
    )
    rt = AgentRuntime(ns)
    steps = rt.run_n_steps(3, initial_state=[1.0])
    assert len(steps) == 3
    for step in steps:
        assert abs(sum(step.state_dist) - 1.0) < 1e-9


def test_runtime_with_rendered_matrices() -> None:
    """Create a ReverseGNNModel, render_matrices_module, exec it, pass to AgentRuntime."""
    from cogant.reverse.matrices import render_matrices_module
    from cogant.reverse.parser import ReverseGNNModel

    model = ReverseGNNModel(
        model_name="test_model",
        raw_model_name="TestModel",
        hidden_states=["s_f0", "s_f1"],
        observations=["o_m0", "o_m1"],
        actions=["u_c0"],
        A=[[0.8, 0.2], [0.2, 0.8]],
        B=[[[1.0], [0.0]], [[0.0], [1.0]]],
        C=[1.0, -1.0],
        D=[0.5, 0.5],
    )

    source = render_matrices_module(model)
    ns = types.ModuleType("matrices")
    exec(source, ns.__dict__)  # noqa: S102

    rt = AgentRuntime(ns)
    steps = rt.run_n_steps(5, initial_state=[0.5, 0.5])
    assert len(steps) == 5
    for step in steps:
        assert math.isfinite(step.free_energy)
        assert abs(sum(step.state_dist) - 1.0) < 1e-6


def test_kl_divergence_identical() -> None:
    """KL divergence of identical distributions is 0."""
    p = [0.3, 0.7]
    assert abs(kl_divergence(p, p)) < 1e-9


def test_kl_divergence_positive() -> None:
    """KL divergence of different distributions is positive."""
    p = [0.9, 0.1]
    q = [0.5, 0.5]
    assert kl_divergence(p, q) > 0.0


def test_module_level_run_functions() -> None:
    """Module-level run_n_steps and run_until_convergence work."""
    ns = _make_simple_matrices_ns()
    rt = AgentRuntime(ns)
    steps = run_n_steps(rt, 3, [0.5, 0.5])
    assert len(steps) == 3

    cfg = AgentConfig(max_steps=50, convergence_threshold=1e-4)
    ns_fixed = types.SimpleNamespace(
        A=[[1.0, 0.0], [0.0, 1.0]],
        B=[[[1.0], [0.0]], [[0.0], [1.0]]],
        C=[0.0, 0.0],
        D=[0.5, 0.5],
        likelihood=lambda s: [
            sum(a * x for a, x in zip(row, s, strict=False)) for row in [[1.0, 0.0], [0.0, 1.0]]
        ],
        transition=lambda s, action=0: list(s),
        preference_score=lambda o: 0.0,
    )
    rt2 = AgentRuntime(ns_fixed)
    steps2 = run_until_convergence(rt2, [0.5, 0.5], cfg)
    assert len(steps2) >= 1
