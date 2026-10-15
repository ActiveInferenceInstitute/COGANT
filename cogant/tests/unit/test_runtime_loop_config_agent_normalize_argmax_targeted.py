#!/usr/bin/env python3
import pytest

from cogant.runtime.categorical import CategoricalModel

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# runtime/config.py — AgentConfig
# ---------------------------------------------------------------------------


class TestAgentConfig:
    def test_agent_config_defaults(self):
        from cogant.runtime.config import AgentConfig

        cfg = AgentConfig()
        assert hasattr(cfg, "max_steps")
        assert isinstance(cfg.max_steps, int)

    def test_agent_config_custom(self):
        from cogant.runtime.config import AgentConfig

        cfg = AgentConfig(max_steps=50)
        assert cfg.max_steps == 50


# ---------------------------------------------------------------------------
# runtime/loop.py — module-level pure functions
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_normalize_uniform(self):
        from cogant.runtime.loop import _normalize

        result = _normalize([1.0, 1.0, 1.0])
        assert len(result) == 3
        assert abs(sum(result) - 1.0) < 1e-9

    def test_normalize_zero_vector_rejected(self):
        from cogant.runtime.loop import _normalize

        with pytest.raises(ValueError):
            _normalize([0.0, 0.0])

    def test_normalize_empty_rejected(self):
        from cogant.runtime.loop import _normalize

        with pytest.raises(ValueError):
            _normalize([])

    def test_normalize_already_normalized(self):
        from cogant.runtime.loop import _normalize

        result = _normalize([0.3, 0.7])
        assert abs(result[0] - 0.3) < 1e-9
        assert abs(result[1] - 0.7) < 1e-9


class TestArgmax:
    def test_argmax_basic(self):
        from cogant.runtime.loop import _argmax

        assert _argmax([0.1, 0.9, 0.3]) == 1

    def test_argmax_empty_rejected(self):
        from cogant.runtime.loop import _argmax

        with pytest.raises(ValueError):
            _argmax([])

    def test_argmax_single(self):
        from cogant.runtime.loop import _argmax

        assert _argmax([5.0]) == 0

    def test_argmax_tie(self):
        from cogant.runtime.loop import _argmax

        result = _argmax([0.5, 0.5])
        assert result in [0, 1]


class TestMatVec:
    def test_mat_vec_basic(self):

        mat = [[1.0, 0.0], [0.0, 1.0]]
        vec = [0.3, 0.7]
        result = CategoricalModel(mat, [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0, 0.0], vec).observe(
            vec
        )
        assert len(result) == 2
        assert abs(result[0] - 0.3) < 1e-9
        assert abs(result[1] - 0.7) < 1e-9

    def test_likelihood_zero_columns_rejected(self):
        with pytest.raises(ValueError, match="sum to"):
            CategoricalModel(
                [[0.0, 0.0], [0.0, 0.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0, 0.0], [1.0, 0.0]
            )


class TestCategoricalHelpers:
    def test_categorical_likelihood(self):

        A = [[0.9, 0.1], [0.1, 0.9]]
        state_dist = [0.5, 0.5]
        result = CategoricalModel(
            A, [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0, 0.0], state_dist
        ).observe(state_dist)
        assert len(result) == 2
        assert abs(sum(result) - 1.0) < 1e-9

    def test_categorical_transition(self):

        B = [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]]
        state_dist = [0.5, 0.5]
        result = CategoricalModel([[1.0, 0.0], [0.0, 1.0]], B, [0.0, 0.0], state_dist).predict(
            state_dist, 0
        )
        assert len(result) == 2
        assert abs(sum(result) - 1.0) < 1e-9

    def test_preference_diagnostic(self):

        C = [1.0, 0.0]
        obs_idx = [0.8, 0.2]
        result = CategoricalModel(
            [[1.0, 0.0], [0.0, 1.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], C, [0.5, 0.5]
        ).preference_score(obs_idx)
        assert abs(result - 0.8) < 1e-9


# ---------------------------------------------------------------------------
# runtime/loop.py — AgentRuntime
# ---------------------------------------------------------------------------


def _make_runtime():
    from cogant.runtime.loop import AgentRuntime

    return AgentRuntime.from_matrices_dict(
        {
            "A": [[0.9, 0.1], [0.1, 0.9]],
            "B": [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]],
            "C": [1.0, 0.0],
            "D": [0.5, 0.5],
        }
    )


class TestAgentRuntime:
    def test_from_matrices_dict(self):
        from cogant.runtime.loop import AgentRuntime

        rt = _make_runtime()
        assert isinstance(rt, AgentRuntime)

    def test_n_states(self):
        rt = _make_runtime()
        assert rt._n_states == 2

    def test_n_obs(self):
        rt = _make_runtime()
        assert rt._n_obs == 2

    def test_step_returns_agent_step(self):
        from cogant.runtime.loop import AgentStep

        rt = _make_runtime()
        state_dist = [0.5, 0.5]
        step = rt.step(state_dist, obs_idx=0)
        assert isinstance(step, AgentStep)

    def test_step_has_action(self):
        rt = _make_runtime()
        step = rt.step([0.5, 0.5], obs_idx=0)
        assert hasattr(step, "action")
        assert isinstance(step.action, int)

    def test_run_n_steps(self):
        rt = _make_runtime()
        steps = rt.run_n_steps(3)
        assert len(steps) == 3

    def test_run_n_steps_zero(self):
        rt = _make_runtime()
        steps = rt.run_n_steps(0)
        assert steps == []

    def test_run_n_steps_returns_agent_steps(self):
        from cogant.runtime.loop import AgentStep

        rt = _make_runtime()
        steps = rt.run_n_steps(2)
        for step in steps:
            assert isinstance(step, AgentStep)


# ---------------------------------------------------------------------------
# runtime/loop.py — AgentStep, EpisodeResult, MultiEpisodeResult dataclasses
# ---------------------------------------------------------------------------


class TestRuntimeDataclasses:
    def test_agent_step_init(self):
        from cogant.runtime.loop import AgentStep

        step = AgentStep(
            t=0,
            state_dist=[0.5, 0.5],
            obs=0,
            action=1,
            free_energy=0.5,
        )
        assert step.t == 0
        assert step.action == 1
        assert step.obs == 0

    def test_episode_result_init(self):
        from cogant.runtime.loop import AgentStep, EpisodeResult

        step = AgentStep(t=0, state_dist=[0.5, 0.5], obs=0, action=0, free_energy=0.3)
        result = EpisodeResult(
            steps=[step],
            final_posterior=[0.5, 0.5],
            obs_counts=[1.0, 0.0],
            obs_state_counts=[[0.5, 0.5], [0.0, 0.0]],
            mean_free_energy=0.3,
            final_free_energy=0.3,
        )
        assert len(result.steps) == 1
        assert result.mean_free_energy == 0.3
