"""Integration tests for multi-episode learning in AgentRuntime.

Covers :meth:`AgentRuntime.run_episode`, :meth:`update_D_from_posterior`,
:meth:`update_A_from_counts`, and :meth:`run_multi_episode`. No mocks —
each test constructs concrete matrices and checks numerical invariants of
the Bayesian D update and frequency-based A update.

The tests deliberately avoid external dependencies (numpy, matplotlib) so
that the runtime learning contract can be validated in isolation from the
reverse-synthesis toolchain.
"""

from __future__ import annotations

import math
import types

from cogant.runtime.loop import (
    AgentRuntime,
    EpisodeResult,
    MultiEpisodeResult,
)

_EPS = 1e-9


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _biased_system() -> types.SimpleNamespace:
    """2-state / 2-obs / 2-action system with a clear preferred observation.

    A is a noisy identity (0.9 / 0.1) so hidden state and observation are
    strongly coupled. C prefers obs 0 so the agent will tend to drive its
    belief toward state 0 (which maps to obs 0).
    """
    A = [[0.9, 0.1], [0.1, 0.9]]
    B = [
        [[1.0, 0.0], [0.0, 1.0]],  # row 0: to state 0
        [[0.0, 1.0], [1.0, 0.0]],  # row 1: to state 1
    ]
    C = [1.0, -1.0]
    D = [0.5, 0.5]

    def likelihood(s: list[float]) -> list[float]:
        return [sum(a * x for a, x in zip(row, s)) for row in A]

    def transition(s: list[float], action: int = 0) -> list[float]:
        n = len(s)
        out = [0.0] * n
        for i in range(n):
            for j in range(n):
                out[i] += B[i][j][action] * s[j]
        tot = sum(out)
        return [v / tot for v in out] if tot > 0 else list(s)

    def preference_score(o: list[float]) -> float:
        return sum(c * x for c, x in zip(C, o))

    return types.SimpleNamespace(
        A=[row[:] for row in A],
        B=[[inner[:] for inner in row] for row in B],
        C=C[:],
        D=D[:],
        likelihood=likelihood,
        transition=transition,
        preference_score=preference_score,
    )


def _three_state_system() -> types.SimpleNamespace:
    """3 hidden states / 3 observations / 1 action with diagonal A.

    Used to exercise convergence plus A learning on a slightly larger
    model where column normalisation is non-trivial.
    """
    A = [
        [0.8, 0.1, 0.1],
        [0.1, 0.8, 0.1],
        [0.1, 0.1, 0.8],
    ]
    # Identity transition.
    B = [
        [[1.0], [0.0], [0.0]],
        [[0.0], [1.0], [0.0]],
        [[0.0], [0.0], [1.0]],
    ]
    C = [0.0, 0.0, 1.0]
    D = [1.0 / 3, 1.0 / 3, 1.0 / 3]

    def likelihood(s: list[float]) -> list[float]:
        return [sum(a * x for a, x in zip(row, s)) for row in A]

    def transition(s: list[float], action: int = 0) -> list[float]:
        return list(s)

    def preference_score(o: list[float]) -> float:
        return sum(c * x for c, x in zip(C, o))

    return types.SimpleNamespace(
        A=[row[:] for row in A],
        B=[[inner[:] for inner in row] for row in B],
        C=C[:],
        D=D[:],
        likelihood=likelihood,
        transition=transition,
        preference_score=preference_score,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_episode_returns_episode_result_with_populated_fields() -> None:
    """run_episode yields the sufficient statistics required for learning."""
    rt = AgentRuntime(_biased_system())
    result = rt.run_episode(n_steps=8)

    assert isinstance(result, EpisodeResult)
    assert len(result.steps) == 8
    assert len(result.final_posterior) == 2
    assert abs(sum(result.final_posterior) - 1.0) < 1e-6
    # Every step must contribute one observation to the histogram.
    assert abs(sum(result.obs_counts) - 8.0) < 1e-6
    # Joint soft counts must match per-observation marginals.
    for o in range(2):
        assert abs(sum(result.obs_state_counts[o]) - result.obs_counts[o]) < 1e-6
    assert math.isfinite(result.mean_free_energy)
    assert math.isfinite(result.final_free_energy)


def test_run_episode_zero_steps_returns_empty_result() -> None:
    """n_steps=0 is a valid no-op that still returns a well-formed result."""
    rt = AgentRuntime(_biased_system())
    result = rt.run_episode(n_steps=0, initial_state=[0.7, 0.3])

    assert result.steps == []
    assert abs(sum(result.final_posterior) - 1.0) < 1e-6
    assert result.final_posterior == [0.7, 0.3]
    assert sum(result.obs_counts) == 0.0
    assert math.isnan(result.mean_free_energy)
    assert math.isnan(result.final_free_energy)


def test_update_D_running_average_matches_closed_form() -> None:
    """D_new = (D_old * k + posterior) / (k + 1) verified at k=0 and k=1."""
    rt = AgentRuntime(_biased_system())
    # k = 0: first update replaces D with the posterior (then renormalised).
    rt.update_D_from_posterior([1.0, 0.0])
    assert rt._episode_count == 1
    assert abs(rt.D[0] - 1.0) < 1e-9
    assert abs(rt.D[1] - 0.0) < 1e-9

    # k = 1: mix old (1, 0) with new (0, 1) -> (0.5, 0.5).
    rt.update_D_from_posterior([0.0, 1.0])
    assert rt._episode_count == 2
    assert abs(rt.D[0] - 0.5) < 1e-9
    assert abs(rt.D[1] - 0.5) < 1e-9

    # k = 2: mix (0.5, 0.5) * 2 with (1, 0) -> (2/3, 1/3).
    rt.update_D_from_posterior([1.0, 0.0])
    assert abs(rt.D[0] - 2.0 / 3.0) < 1e-9
    assert abs(rt.D[1] - 1.0 / 3.0) < 1e-9


def test_update_D_stays_normalised_over_many_updates() -> None:
    """Repeated running-average updates preserve sum(D) == 1."""
    rt = AgentRuntime(_three_state_system())
    posteriors = [
        [0.8, 0.1, 0.1],
        [0.1, 0.8, 0.1],
        [0.1, 0.1, 0.8],
        [0.6, 0.2, 0.2],
        [0.2, 0.6, 0.2],
    ]
    for p in posteriors:
        rt.update_D_from_posterior(p)
        assert abs(sum(rt.D) - 1.0) < 1e-9
        for x in rt.D:
            assert 0.0 <= x <= 1.0


def test_update_A_columns_remain_normalised() -> None:
    """After A learning every column sums to 1 (valid likelihood matrix)."""
    rt = AgentRuntime(_three_state_system())
    # Fake joint counts that heavily associate obs 2 with state 2.
    counts = [
        [5.0, 1.0, 0.0],
        [1.0, 5.0, 0.0],
        [0.0, 0.0, 10.0],
    ]
    rt.update_A_from_counts(counts, learning_rate=0.5)

    n_states = len(rt.A[0])
    n_obs = len(rt.A)
    for s in range(n_states):
        col_sum = sum(rt.A[o][s] for o in range(n_obs))
        assert abs(col_sum - 1.0) < 1e-9, f"column {s} sum = {col_sum}"
    # Strong evidence for (obs=2, state=2) should have increased that entry.
    assert rt.A[2][2] > 0.8


def test_update_A_zero_learning_rate_is_noop() -> None:
    """learning_rate=0 leaves A unchanged (within fp tolerance)."""
    rt = AgentRuntime(_three_state_system())
    original = [row[:] for row in rt.A]
    counts = [
        [10.0, 0.0, 0.0],
        [0.0, 10.0, 0.0],
        [0.0, 0.0, 10.0],
    ]
    rt.update_A_from_counts(counts, learning_rate=0.0)
    for o in range(3):
        for s in range(3):
            assert abs(rt.A[o][s] - original[o][s]) < 1e-9


def test_update_A_unseen_observation_row_unchanged() -> None:
    """Rows with zero empirical counts survive the update without row blending.

    Column normalisation may still rescale an unseen row per-column, but the
    row must not be *blended* against empirical frequencies (so none of its
    entries should collapse to zero when the original was non-zero).
    """
    rt = AgentRuntime(_three_state_system())
    original_row1 = rt.A[1][:]
    counts = [
        [10.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],  # obs 1 never seen
        [0.0, 0.0, 10.0],
    ]
    rt.update_A_from_counts(counts, learning_rate=0.8)
    # Positive entries must remain positive (no row blending toward freq=0).
    for s in range(3):
        if original_row1[s] > _EPS:
            assert rt.A[1][s] > _EPS, f"unseen-row entry A[1][{s}] collapsed"
    # Columns are still proper distributions.
    for s in range(3):
        col_sum = sum(rt.A[o][s] for o in range(3))
        assert abs(col_sum - 1.0) < 1e-9


def test_run_multi_episode_records_vfe_trajectory() -> None:
    """run_multi_episode returns parallel lists of length n_episodes."""
    rt = AgentRuntime(_biased_system())
    result = rt.run_multi_episode(
        n_episodes=5,
        steps_per_episode=4,
        learning_rate=0.2,
    )
    assert isinstance(result, MultiEpisodeResult)
    assert len(result.episodes) == 5
    assert len(result.vfe_trajectory) == 5
    assert len(result.final_vfe_trajectory) == 5
    assert len(result.D_trajectory) == 5
    for vfe in result.vfe_trajectory:
        assert math.isfinite(vfe)
    for d_snapshot in result.D_trajectory:
        assert abs(sum(d_snapshot) - 1.0) < 1e-6


def test_multi_episode_vfe_decreases_for_learning_agent() -> None:
    """Mean VFE in the last episode is not worse than the first.

    With a biased preference and a working learning rule, the agent should
    drive its free energy downward (or at worst hold steady) as D and A are
    updated between episodes. We assert a weak inequality to keep the test
    deterministic under the simplified argmax sensory model.
    """
    rt = AgentRuntime(_biased_system())
    result = rt.run_multi_episode(
        n_episodes=6,
        steps_per_episode=6,
        learning_rate=0.3,
    )
    first_vfe = result.vfe_trajectory[0]
    last_vfe = result.vfe_trajectory[-1]
    assert math.isfinite(first_vfe) and math.isfinite(last_vfe)
    assert last_vfe <= first_vfe + 1e-6, (
        f"VFE increased during learning: {first_vfe} -> {last_vfe}"
    )


def test_multi_episode_updates_D_toward_visited_states() -> None:
    """After learning, D should concentrate on states the agent actually visits."""
    rt = AgentRuntime(_biased_system())
    initial_D = list(rt.D)
    rt.run_multi_episode(
        n_episodes=10,
        steps_per_episode=8,
        learning_rate=0.2,
    )
    # Agent prefers obs 0 which maps to state 0 — D should shift toward s0.
    assert rt.D[0] >= initial_D[0] - 1e-6
    # D is still a proper distribution.
    assert abs(sum(rt.D) - 1.0) < 1e-6


def test_multi_episode_preserves_A_column_stochasticity() -> None:
    """Every A column is a valid distribution after multi-episode learning."""
    rt = AgentRuntime(_three_state_system())
    rt.run_multi_episode(
        n_episodes=4,
        steps_per_episode=5,
        learning_rate=0.25,
    )
    n_obs = len(rt.A)
    n_states = len(rt.A[0])
    for s in range(n_states):
        col_sum = sum(rt.A[o][s] for o in range(n_obs))
        assert abs(col_sum - 1.0) < 1e-9


def test_run_until_convergence_still_works_after_learning() -> None:
    """Existing convergence API is unaffected by the learning additions."""
    rt = AgentRuntime(_biased_system())
    rt.run_multi_episode(n_episodes=3, steps_per_episode=4, learning_rate=0.1)
    steps = rt.run_until_convergence(initial_state=list(rt.D))
    assert len(steps) >= 1
    for s in steps:
        assert math.isfinite(s.free_energy)
        assert abs(sum(s.state_dist) - 1.0) < 1e-6


def test_episode_count_increments_exactly_once_per_episode() -> None:
    """_episode_count tracks the number of D updates applied."""
    rt = AgentRuntime(_biased_system())
    assert rt._episode_count == 0
    rt.run_multi_episode(n_episodes=4, steps_per_episode=3, learning_rate=0.1)
    assert rt._episode_count == 4
