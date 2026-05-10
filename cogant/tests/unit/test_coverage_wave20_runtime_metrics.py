"""Coverage wave 20: cogant.runtime.metrics — EpisodeMetrics, RunMetrics, edge cases.

Targets uncovered lines in py/cogant/runtime/metrics.py:
* line 78: out-of-range obs_idx fallback in free_energy
* line 124: EpisodeMetrics.to_csv_row
* lines 159-194: RunMetrics.summary_statistics (empty + non-empty)
* lines 222-245: RunMetrics.plot_free_energy (empty + populated branches)

No mocks: real distributions, real EpisodeMetrics instances, real arithmetic.
"""

from __future__ import annotations

import csv
import io
import math

import pytest

from cogant.runtime.metrics import (
    EpisodeMetrics,
    RunMetrics,
    free_energy,
    kl_divergence,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# free_energy: out-of-range obs_idx clamping
# --------------------------------------------------------------------------- #


def test_free_energy_negative_obs_idx_clamps_to_zero() -> None:
    """obs_idx<0 is silently rewritten to 0 (line 78 branch)."""
    A = [[0.9, 0.1], [0.1, 0.9]]
    C = [0.0, 0.0]
    D = [0.5, 0.5]
    state = [0.5, 0.5]

    fe_neg = free_energy(state, obs_idx=-1, A=A, C=C, D=D)
    fe_zero = free_energy(state, obs_idx=0, A=A, C=C, D=D)
    assert math.isfinite(fe_neg)
    assert abs(fe_neg - fe_zero) < 1e-12


def test_free_energy_obs_idx_beyond_range_clamps() -> None:
    """obs_idx>=n_obs falls back to the obs_idx=0 row."""
    A = [[0.9, 0.1], [0.1, 0.9]]
    C = [0.0, 0.0]
    D = [0.5, 0.5]
    state = [0.5, 0.5]

    fe_high = free_energy(state, obs_idx=99, A=A, C=C, D=D)
    fe_zero = free_energy(state, obs_idx=0, A=A, C=C, D=D)
    assert math.isfinite(fe_high)
    assert abs(fe_high - fe_zero) < 1e-12


def test_kl_divergence_skips_zero_p() -> None:
    """kl_divergence ignores entries where p[i] is below epsilon."""
    p = [0.0, 1.0]
    q = [0.5, 0.5]
    # Only the second term contributes: 1.0 * log(1.0 / (0.5 + eps))
    val = kl_divergence(p, q)
    assert math.isfinite(val)
    assert val > 0.0


# --------------------------------------------------------------------------- #
# EpisodeMetrics: to_csv_row
# --------------------------------------------------------------------------- #


def test_episode_metrics_to_csv_row_keys_and_values() -> None:
    """to_csv_row returns all six fields with their assigned values."""
    em = EpisodeMetrics(
        episode_id=7,
        n_steps=42,
        mean_free_energy=1.25,
        final_free_energy=0.75,
        n_unique_obs=5,
        action_entropy=0.9,
    )
    row = em.to_csv_row()
    assert row == {
        "episode_id": 7,
        "n_steps": 42,
        "mean_free_energy": 1.25,
        "final_free_energy": 0.75,
        "n_unique_obs": 5,
        "action_entropy": 0.9,
    }


def test_episode_metrics_to_csv_row_writable_via_dictwriter() -> None:
    """to_csv_row plugs directly into csv.DictWriter without modification."""
    em = EpisodeMetrics(
        episode_id=0,
        n_steps=3,
        mean_free_energy=0.1,
        final_free_energy=0.05,
    )
    row = em.to_csv_row()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(row.keys()))
    writer.writeheader()
    writer.writerow(row)
    output = buf.getvalue()
    assert "episode_id" in output
    assert "0" in output  # episode_id value
    assert "3" in output  # n_steps value


def test_episode_metrics_default_optional_fields() -> None:
    """n_unique_obs and action_entropy default to 0 / 0.0."""
    em = EpisodeMetrics(
        episode_id=1, n_steps=2, mean_free_energy=0.0, final_free_energy=0.0
    )
    assert em.n_unique_obs == 0
    assert em.action_entropy == 0.0
    row = em.to_csv_row()
    assert row["n_unique_obs"] == 0
    assert row["action_entropy"] == 0.0


# --------------------------------------------------------------------------- #
# RunMetrics.summary_statistics — empty branch
# --------------------------------------------------------------------------- #


def test_run_metrics_summary_empty_returns_nan_filled() -> None:
    """Empty episodes returns a NaN-filled scaffold with zero counts."""
    rm = RunMetrics(episodes=[])
    stats = rm.summary_statistics()

    # Counts are zero (not NaN)
    assert stats["n_episodes"] == 0
    assert stats["total_steps"] == 0

    # All other stats are NaN
    nan_keys = [
        "mean_free_energy_mean",
        "mean_free_energy_std",
        "mean_free_energy_min",
        "mean_free_energy_max",
        "final_free_energy_mean",
        "final_free_energy_std",
        "final_free_energy_min",
        "final_free_energy_max",
        "steps_per_episode_mean",
        "steps_per_episode_std",
    ]
    for k in nan_keys:
        assert math.isnan(stats[k]), f"{k} = {stats[k]} should be NaN"


# --------------------------------------------------------------------------- #
# RunMetrics.summary_statistics — populated branch
# --------------------------------------------------------------------------- #


def test_run_metrics_summary_two_episodes_arithmetic() -> None:
    """Mean / std / min / max are computed correctly for two episodes."""
    e0 = EpisodeMetrics(
        episode_id=0,
        n_steps=4,
        mean_free_energy=1.0,
        final_free_energy=0.5,
        n_unique_obs=2,
        action_entropy=0.0,
    )
    e1 = EpisodeMetrics(
        episode_id=1,
        n_steps=6,
        mean_free_energy=3.0,
        final_free_energy=1.5,
        n_unique_obs=3,
        action_entropy=0.0,
    )
    rm = RunMetrics(episodes=[e0, e1])
    stats = rm.summary_statistics()

    assert stats["n_episodes"] == 2
    assert stats["total_steps"] == 10  # 4 + 6

    # Mean of [1.0, 3.0] is 2.0
    assert abs(stats["mean_free_energy_mean"] - 2.0) < 1e-12
    # Population std (uses /N, not /N-1) of [1.0, 3.0]: variance=1.0, std=1.0
    assert abs(stats["mean_free_energy_std"] - 1.0) < 1e-12
    assert stats["mean_free_energy_min"] == 1.0
    assert stats["mean_free_energy_max"] == 3.0

    # Final FE: mean of [0.5, 1.5] = 1.0
    assert abs(stats["final_free_energy_mean"] - 1.0) < 1e-12
    # Population std of [0.5, 1.5]: variance=0.25, std=0.5
    assert abs(stats["final_free_energy_std"] - 0.5) < 1e-12
    assert stats["final_free_energy_min"] == 0.5
    assert stats["final_free_energy_max"] == 1.5

    # Steps: mean of [4.0, 6.0] = 5.0, std = 1.0
    assert abs(stats["steps_per_episode_mean"] - 5.0) < 1e-12
    assert abs(stats["steps_per_episode_std"] - 1.0) < 1e-12


def test_run_metrics_summary_single_episode_zero_std() -> None:
    """A single-episode RunMetrics has std == 0.0 across the board."""
    em = EpisodeMetrics(
        episode_id=0,
        n_steps=5,
        mean_free_energy=2.5,
        final_free_energy=2.0,
    )
    rm = RunMetrics(episodes=[em], total_steps=5)
    stats = rm.summary_statistics()

    assert stats["n_episodes"] == 1
    assert stats["total_steps"] == 5
    assert stats["mean_free_energy_mean"] == 2.5
    assert stats["mean_free_energy_std"] == 0.0
    assert stats["mean_free_energy_min"] == 2.5
    assert stats["mean_free_energy_max"] == 2.5
    assert stats["final_free_energy_std"] == 0.0
    assert stats["steps_per_episode_std"] == 0.0


def test_run_metrics_summary_three_episodes_min_max() -> None:
    """min/max across three episodes pick the right extremes."""
    eps = [
        EpisodeMetrics(episode_id=i, n_steps=i + 1, mean_free_energy=float(v),
                       final_free_energy=float(v) / 2)
        for i, v in enumerate([10, 1, 5])
    ]
    rm = RunMetrics(episodes=eps)
    stats = rm.summary_statistics()
    assert stats["mean_free_energy_min"] == 1.0
    assert stats["mean_free_energy_max"] == 10.0
    assert stats["final_free_energy_min"] == 0.5
    assert stats["final_free_energy_max"] == 5.0
    assert stats["n_episodes"] == 3
    assert stats["total_steps"] == 1 + 2 + 3


# --------------------------------------------------------------------------- #
# RunMetrics.plot_free_energy
# --------------------------------------------------------------------------- #


def test_plot_free_energy_empty_returns_none() -> None:
    """Empty episodes → plot returns None and warns."""
    rm = RunMetrics(episodes=[])
    fig = rm.plot_free_energy()
    assert fig is None


def test_plot_free_energy_with_episodes_returns_figure_or_none() -> None:
    """With episodes, returns a matplotlib Figure when matplotlib available.

    On systems without matplotlib (very rare in this repo) the function
    returns None and logs a warning. We accept either outcome to keep the
    test environment-agnostic, but exercise both code paths' coverage.
    """
    eps = [
        EpisodeMetrics(episode_id=i, n_steps=2, mean_free_energy=float(i),
                       final_free_energy=float(i) * 0.5)
        for i in range(3)
    ]
    rm = RunMetrics(episodes=eps)
    fig = rm.plot_free_energy()
    if fig is None:
        # Path: matplotlib import failed
        return
    # Path: matplotlib import succeeded — verify Figure-like object
    # (avoid hard import dependency in test module by duck-typing)
    assert hasattr(fig, "axes")
    # At least one Axes was created
    assert len(fig.axes) >= 1
    ax = fig.axes[0]
    # Title and labels were set
    assert "VFE" in ax.get_title() or "Free Energy" in ax.get_title()
    assert ax.get_xlabel() == "Episode"


def test_plot_free_energy_single_episode_does_not_crash() -> None:
    """Plotting a single-episode RunMetrics succeeds (no division-by-zero)."""
    em = EpisodeMetrics(episode_id=0, n_steps=1, mean_free_energy=1.0,
                        final_free_energy=0.5)
    rm = RunMetrics(episodes=[em])
    fig = rm.plot_free_energy()
    # Either a real Figure or None (no matplotlib) — both are valid.
    assert fig is None or hasattr(fig, "axes")


# --------------------------------------------------------------------------- #
# RunMetrics dataclass field defaults
# --------------------------------------------------------------------------- #


def test_run_metrics_total_steps_default_zero() -> None:
    rm = RunMetrics(episodes=[])
    assert rm.total_steps == 0


def test_run_metrics_total_steps_explicit() -> None:
    rm = RunMetrics(episodes=[], total_steps=99)
    assert rm.total_steps == 99
