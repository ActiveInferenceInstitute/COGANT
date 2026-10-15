"""Real-matrix categorical runtime, episode learning, and rejection controls."""

from __future__ import annotations

import math
import types

import pytest

from cogant.runtime.categorical import CategoricalModel
from cogant.runtime.config import AgentConfig
from cogant.runtime.loop import (
    AgentRuntime,
    AgentStep,
    EpisodeResult,
    MultiEpisodeResult,
    _argmax,
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
    def test_normalize_rejects_zero_mass(self):
        with pytest.raises(ValueError, match="zero probability"):
            _normalize([0.0, 0.0])

    def test_normalize_rejects_empty(self):
        with pytest.raises(ValueError, match="nonempty"):
            _normalize([])

    def test_normalize_scales_to_sum_one(self):
        out = _normalize([2.0, 2.0, 4.0])
        assert math.isclose(sum(out), 1.0)
        assert math.isclose(out[2], 0.5)

    def test_argmax_rejects_empty(self):
        with pytest.raises(ValueError, match="nonempty"):
            _argmax([])

    def test_argmax_picks_max_index(self):
        assert _argmax([0.1, 0.5, 0.4]) == 1

    def test_argmax_first_on_ties(self):
        assert _argmax([0.3, 0.3, 0.3]) == 0

    def test_categorical_likelihood(self):
        A = [[1.0, 0.0], [0.0, 1.0]]
        out = CategoricalModel(A, [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0, 0.0], [0.7, 0.3]).observe(
            [0.7, 0.3]
        )
        assert out == [0.7, 0.3]

    def test_categorical_transition(self):
        # Identity-like B
        B = [[[1.0], [0.0]], [[0.0], [1.0]]]
        out = CategoricalModel([[1.0, 0.0], [0.0, 1.0]], B, [0.0, 0.0], [0.6, 0.4]).predict(
            [0.6, 0.4], 0
        )
        assert math.isclose(sum(out), 1.0)

    def test_preference_diagnostic(self):
        assert math.isclose(
            CategoricalModel(
                [[1.0, 0.0], [0.0, 1.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], [1.0, 0.0], [0.5, 0.5]
            ).preference_score([0.7, 0.3]),
            0.7,
        )


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

    def test_init_uses_declared_matrices(self):
        # Bare namespace with only A/B/C/D — should bind defaults.
        ns = types.SimpleNamespace(**_identity_matrices())
        rt = AgentRuntime(ns)
        # Helpers should still be callable
        out = rt._likelihood([0.5, 0.5])
        assert len(out) == 2

    def test_matrix_contract_overrides_inconsistent_custom_helpers(self):
        ns = types.SimpleNamespace(**_identity_matrices())
        ns.likelihood = lambda sd: [1.0, 0.0]
        ns.transition = lambda sd, a=0: [0.0, 1.0]
        ns.preference_score = lambda od: 42.0
        rt = AgentRuntime(ns)
        assert rt._likelihood([0.5, 0.5]) == [0.5, 0.5]
        assert rt._transition([0.5, 0.5], 0) == [0.5, 0.5]


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

    def test_runtime_rejects_empty_prior(self):
        matrices = _identity_matrices()
        matrices["D"] = []
        with pytest.raises(ValueError, match="prior D"):
            AgentRuntime.from_matrices_dict(matrices)

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

    def test_update_D_rejects_empty_posterior(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        with pytest.raises(ValueError, match="dimensions"):
            rt.update_D_from_posterior([])

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

    def test_update_A_rejects_invalid_rate(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        with pytest.raises(ValueError, match="learning_rate"):
            rt.update_A_from_counts([[1.0, 1.0], [1.0, 1.0]], learning_rate=5.0)

    def test_update_A_rejects_empty_counts(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        with pytest.raises(ValueError, match="dimensions"):
            rt.update_A_from_counts([])

    def test_runtime_rejects_zero_states(self):
        with pytest.raises(ValueError, match="prior D"):
            AgentRuntime(types.SimpleNamespace(A=[[]], B=[], C=[], D=[]))

    def test_runtime_rejects_zero_likelihood_columns(self):
        matrices = _identity_matrices()
        matrices["A"] = [[0.0, 0.0], [0.0, 0.0]]
        with pytest.raises(ValueError, match="sum to"):
            AgentRuntime.from_matrices_dict(matrices)

    def test_run_multi_episode(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        result = rt.run_multi_episode(n_episodes=3, steps_per_episode=2, learning_rate=0.1)
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

    def test_run_multi_episode_rejects_negative_count(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        with pytest.raises(ValueError, match="episode count"):
            rt.run_multi_episode(-3, 2)


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

    def test_benchmark_rejects_zero_episodes(self):
        rt = AgentRuntime.from_matrices_dict(_identity_matrices())
        with pytest.raises(ValueError, match="positive"):
            rt.benchmark(0)

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
