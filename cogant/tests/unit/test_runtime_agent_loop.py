"""Targeted coverage tests for ``cogant.runtime.loop``.

Drives the AgentRuntime end-to-end with real matrices (no mocks).
Covers:
- _normalize / _argmax / _mat_vec helpers (via empty / degenerate cases)
- _default_likelihood / _default_transition / _default_preference_score
- run_until_convergence (default cfg branch)
- run_episode (zero-step branches: with and without initial_state, and
  with empty D)
- update_D_from_posterior (running average + early return + identity preservation)
- update_A_from_counts (zero observations, learning-rate clamping,
  degenerate-column path)
- run_multi_episode (full lifecycle with D and A updates)
- run_episode_with_logging
- benchmark
- reset, get_free_energy
- to_dict / from_dict round trip
- module-level run_n_steps and run_until_convergence convenience wrappers
"""

from __future__ import annotations

import math
import types

from cogant.runtime.config import AgentConfig
from cogant.runtime.loop import (
    AgentRuntime,
    AgentStep,
    EpisodeResult,
    MultiEpisodeResult,
    _argmax,
    _default_likelihood,
    _default_preference_score,
    _default_transition,
    _normalize,
    run_n_steps,
    run_until_convergence,
)


def _identity_matrices() -> dict:
    """Return matrices for a 2-state, 2-obs, 1-action system."""
    return {
        "A": [[0.9, 0.1], [0.1, 0.9]],
        "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        "C": [1.0, 0.0],
        "D": [0.5, 0.5],
    }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestPureHelpers:
    def test_normalize_uniform_when_total_zero(self):
        # Empty / zero-sum lists fall back to uniform distribution.
        assert _normalize([0.0, 0.0]) == [0.5, 0.5]

    def test_normalize_empty_returns_empty(self):
        assert _normalize([]) == []

    def test_normalize_scales_to_sum_one(self):
        out = _normalize([2.0, 2.0, 4.0])
        assert math.isclose(sum(out), 1.0)
        assert math.isclose(out[2], 0.5)

    def test_argmax_empty_returns_zero(self):
        assert _argmax([]) == 0

    def test_argmax_picks_max_index(self):
        assert _argmax([0.1, 0.5, 0.4]) == 1

    def test_argmax_first_on_ties(self):
        assert _argmax([0.3, 0.3, 0.3]) == 0

    def test_default_likelihood(self):
        A = [[1.0, 0.0], [0.0, 1.0]]
        out = _default_likelihood(A, [0.7, 0.3])
        assert out == [0.7, 0.3]

    def test_default_transition(self):
        # Identity-like B
        B = [[[1.0], [0.0]], [[0.0], [1.0]]]
        out = _default_transition(B, [0.6, 0.4], action=0)
        assert math.isclose(sum(out), 1.0)

    def test_default_preference_score(self):
        assert math.isclose(_default_preference_score([1.0, 0.0], [0.7, 0.3]), 0.7)


# ---------------------------------------------------------------------------
# AgentRuntime construction & fallback bindings
# ---------------------------------------------------------------------------


class TestAgentRuntimeConstruction:
    def test_from_matrices_dict_creates_runtime(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        assert isinstance(rt, AgentRuntime)
        assert rt._n_states == 2
        assert rt._n_obs == 2
        assert rt._n_actions == 1

    def test_init_uses_default_helpers_when_missing(self):
        # Bare namespace with only A/B/C/D — should bind defaults.
        ns = types.SimpleNamespace(**_identity_matrices())
        rt = AgentRuntime(ns)
        # Helpers should still be callable
        out = rt._likelihood([0.5, 0.5])
        assert len(out) == 2

    def test_init_uses_provided_callables(self):
        ns = types.SimpleNamespace(**_identity_matrices())
        ns.likelihood = lambda sd: [1.0, 0.0]
        ns.transition = lambda sd, a=0: [0.0, 1.0]
        ns.preference_score = lambda od: 42.0
        rt = AgentRuntime(ns)
        assert rt._likelihood([0.5, 0.5]) == [1.0, 0.0]
        assert rt._transition([0.5, 0.5], 0) == [0.0, 1.0]
        assert rt._preference_score([0.5, 0.5]) == 42.0


# ---------------------------------------------------------------------------
# step / run_n_steps / run_until_convergence
# ---------------------------------------------------------------------------


class TestStepAndRun:
    def test_single_step_returns_agent_step(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        s = rt.step([0.5, 0.5], obs_idx=0, t=0)
        assert isinstance(s, AgentStep)
        assert math.isclose(sum(s.state_dist), 1.0, abs_tol=1e-9)

    def test_run_n_steps_emits_n_steps(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        steps = rt.run_n_steps(4)
        assert len(steps) == 4
        for i, st in enumerate(steps):
            assert st.t == i

    def test_run_n_steps_with_initial_state(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        steps = rt.run_n_steps(2, initial_state=[1.0, 0.0])
        assert len(steps) == 2

    def test_run_until_convergence_default_cfg(self):
        rt = AgentRuntime.from_matrices_dict(
            {
                "A": [[0.99, 0.01], [0.01, 0.99]],
                "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
                "C": [1.0, 0.0],
                "D": [0.5, 0.5],
            }
        )
        # cfg=None → triggers AgentConfig() default branch
        steps = rt.run_until_convergence()
        assert 1 <= len(steps) <= AgentConfig().max_steps

    def test_run_until_convergence_with_initial_state_and_cfg(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        cfg = AgentConfig(max_steps=10, convergence_threshold=0.001)
        steps = rt.run_until_convergence(initial_state=[0.6, 0.4], cfg=cfg)
        assert 1 <= len(steps) <= 10


# ---------------------------------------------------------------------------
# Episode / multi-episode learning
# ---------------------------------------------------------------------------


class TestEpisodeAndLearning:
    def test_run_episode_basic(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result = rt.run_episode(3)
        assert isinstance(result, EpisodeResult)
        assert len(result.steps) == 3
        assert len(result.final_posterior) == 2
        assert sum(result.obs_counts) == 3.0
        assert not math.isnan(result.mean_free_energy)
        assert not math.isnan(result.final_free_energy)

    def test_run_episode_zero_steps_uses_initial_state(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result = rt.run_episode(0, initial_state=[1.0, 0.0])
        assert result.steps == []
        assert result.final_posterior == [1.0, 0.0]
        assert math.isnan(result.mean_free_energy)
        assert math.isnan(result.final_free_energy)

    def test_run_episode_zero_steps_falls_back_to_D(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result = rt.run_episode(0)
        assert result.final_posterior == [0.5, 0.5]

    def test_run_episode_zero_steps_uniform_when_D_empty(self):
        ns = types.SimpleNamespace(
            A=[[1.0, 0.0], [0.0, 1.0]],
            B=[[[1.0], [0.0]], [[0.0], [1.0]]],
            C=[1.0, 0.0],
            D=[],  # forces uniform fallback
        )
        rt = AgentRuntime(ns)
        result = rt.run_episode(0)
        # Uniform over n_states (defaulted to 1 when D is empty + A row size)
        assert math.isclose(sum(result.final_posterior), 1.0)

    def test_update_D_from_posterior_running_average(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        new_D = rt.update_D_from_posterior([1.0, 0.0])
        assert rt._episode_count == 1
        # First update with k=0 ⇒ new_D == normalised posterior [1, 0]
        assert math.isclose(new_D[0], 1.0)
        assert math.isclose(new_D[1], 0.0)
        # Second update with episode_count=1 averages D=[1,0] with [0,1]
        # weighted (1/2, 1/2) ⇒ [0.5, 0.5]
        rt.update_D_from_posterior([0.0, 1.0])
        assert rt._episode_count == 2
        assert math.isclose(rt.D[0], 0.5)
        assert math.isclose(rt.D[1], 0.5)

    def test_update_D_from_posterior_empty_inputs(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        # Empty posterior => return D unchanged
        assert rt.update_D_from_posterior([]) is rt.D
        # Empty D => same
        rt.D = []
        assert rt.update_D_from_posterior([0.5, 0.5]) is rt.D

    def test_update_A_from_counts_blends_frequencies(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        before = [row[:] for row in rt.A]
        # Strong evidence for obs 0 from state 0
        counts = [[3.0, 0.0], [0.0, 3.0]]
        new_A = rt.update_A_from_counts(counts, learning_rate=0.5)
        assert new_A is rt.A
        # Each column normalised to sum 1
        for s in range(2):
            col = sum(rt.A[o][s] for o in range(2))
            assert math.isclose(col, 1.0, abs_tol=1e-9)
        assert before != rt.A

    def test_update_A_from_counts_no_obs_leaves_row(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        before = [row[:] for row in rt.A]
        # Zero counts => columns still normalise from prior values.
        rt.update_A_from_counts([[0.0, 0.0], [0.0, 0.0]], learning_rate=0.5)
        # Rows unchanged before column normalisation; column normalisation
        # may still re-normalise if columns sum != 1.
        for s in range(2):
            col = sum(rt.A[o][s] for o in range(2))
            assert math.isclose(col, 1.0, abs_tol=1e-9)
        # Prior was already normalised so values should match.
        assert before == rt.A

    def test_update_A_from_counts_clamps_lr(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        # lr > 1 should be clamped to 1
        rt.update_A_from_counts([[1.0, 1.0], [1.0, 1.0]], learning_rate=5.0)
        for s in range(2):
            col = sum(rt.A[o][s] for o in range(2))
            assert math.isclose(col, 1.0, abs_tol=1e-9)

    def test_update_A_from_counts_empty_inputs(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        # Empty counts => return A unchanged
        same = rt.update_A_from_counts([], learning_rate=0.1)
        assert same is rt.A

    def test_update_A_from_counts_no_states_returns_early(self):
        # Build a runtime whose A has zero columns
        ns = types.SimpleNamespace(A=[[]], B=[], C=[], D=[])
        rt = AgentRuntime(ns)
        result = rt.update_A_from_counts([[0.0]], learning_rate=0.5)
        assert result is rt.A

    def test_update_A_from_counts_degenerate_column_uniform(self):
        # Force a column of all-zeros so the degenerate branch fires.
        ns = types.SimpleNamespace(
            A=[[0.0, 0.0], [0.0, 0.0]],
            B=[[[1.0], [0.0]], [[0.0], [1.0]]],
            C=[1.0, 0.0],
            D=[0.5, 0.5],
        )
        rt = AgentRuntime(ns)
        # All counts zero => freq blend leaves row at zeros, hits degenerate
        # column branch.
        rt.update_A_from_counts([[0.0, 0.0], [0.0, 0.0]], learning_rate=0.5)
        for s in range(2):
            col = sum(rt.A[o][s] for o in range(2))
            # Uniform => column sums to 1
            assert math.isclose(col, 1.0, abs_tol=1e-9)
            # And every entry equals 1/n_obs
            for o in range(2):
                assert math.isclose(rt.A[o][s], 0.5)

    def test_run_multi_episode(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result = rt.run_multi_episode(
            n_episodes=3, steps_per_episode=2, learning_rate=0.1
        )
        assert isinstance(result, MultiEpisodeResult)
        assert len(result.episodes) == 3
        assert len(result.D_trajectory) == 3
        assert len(result.vfe_trajectory) == 3
        assert len(result.final_vfe_trajectory) == 3
        assert result.learning_rate == 0.1

    def test_run_multi_episode_zero_episodes_yields_empty(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result = rt.run_multi_episode(n_episodes=0, steps_per_episode=2)
        assert result.episodes == []
        assert result.D_trajectory == []

    def test_run_multi_episode_negative_clamped(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result = rt.run_multi_episode(n_episodes=-3, steps_per_episode=2)
        assert result.episodes == []


# ---------------------------------------------------------------------------
# Logging / benchmarking / introspection
# ---------------------------------------------------------------------------


class TestRuntimeIntrospection:
    def test_run_episode_with_logging_returns_logs(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result, logs = rt.run_episode_with_logging([0, 1, 0])
        assert len(result.steps) == 3
        assert len(logs) == 3
        for i, log in enumerate(logs):
            assert log["step"] == i
            assert log["observation"] in (0, 1)
            assert "action" in log
            assert "free_energy" in log

    def test_run_episode_with_logging_empty_sequence(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result, logs = rt.run_episode_with_logging([])
        assert result.steps == []
        assert logs == []
        assert math.isnan(result.mean_free_energy)
        assert math.isnan(result.final_free_energy)

    def test_benchmark_reports_stats(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        stats = rt.benchmark(n_episodes=3)
        assert set(stats) == {"mean_ms", "std_ms", "min_ms", "max_ms"}
        assert stats["mean_ms"] >= 0
        assert stats["min_ms"] <= stats["max_ms"]

    def test_benchmark_clamps_to_one_when_zero(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        # n_episodes=0 should clamp to 1 via max(1, ...)
        stats = rt.benchmark(n_episodes=0)
        assert stats["mean_ms"] >= 0

    def test_reset_clears_episode_state(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        rt.run_n_steps(2)
        assert not math.isnan(rt.get_free_energy())
        rt._episode_count = 5
        rt.reset()
        assert rt._episode_count == 0
        assert math.isnan(rt.get_free_energy())

    def test_get_free_energy_initial_nan(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        # Before any step, last VFE is nan.
        assert math.isnan(rt.get_free_energy())

    def test_get_free_energy_after_step_finite(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        rt.run_n_steps(1)
        fe = rt.get_free_energy()
        assert isinstance(fe, float)
        assert not math.isnan(fe)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_dict_returns_full_state(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        rt._episode_count = 7
        d = rt.to_dict()
        assert d["A"] == [[0.9, 0.1], [0.1, 0.9]]
        assert d["episode_count"] == 7
        assert d["n_states"] == 2

    def test_from_dict_restores_episode_count(self):
        d = _identity_matrices()
        d["episode_count"] = 4
        rt = AgentRuntime.from_dict(d)
        assert rt._episode_count == 4

    def test_from_dict_without_episode_count_defaults_to_zero(self):
        rt = AgentRuntime.from_dict(_identity_matrices())
        assert rt._episode_count == 0


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


class TestModuleLevelConvenience:
    def test_run_n_steps_module_level(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        steps = run_n_steps(rt, 3)
        assert len(steps) == 3

    def test_run_n_steps_module_level_with_initial_state(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        steps = run_n_steps(rt, 2, initial_state=[0.7, 0.3])
        assert len(steps) == 2

    def test_run_until_convergence_module_level(self):
        rt = AgentRuntime.from_matrices_dict(
            {
                "A": [[0.99, 0.01], [0.01, 0.99]],
                "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
                "C": [1.0, 0.0],
                "D": [0.5, 0.5],
            }
        )
        steps = run_until_convergence(rt)
        assert len(steps) >= 1

    def test_run_until_convergence_module_level_with_cfg(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        cfg = AgentConfig(max_steps=5)
        steps = run_until_convergence(rt, initial_state=[0.5, 0.5], cfg=cfg)
        assert 1 <= len(steps) <= 5
