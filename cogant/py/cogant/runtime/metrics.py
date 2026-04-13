"""Variational free energy and KL divergence for Active Inference.

All functions are pure-Python with no external dependencies. Numerical
safety is ensured by adding a small epsilon (1e-10) inside logarithms
to avoid domain errors on zero-probability entries.

Variational Free Energy (VFE) approximation
--------------------------------------------
Given a state distribution ``q(s)``, an observation index ``obs_idx``,
a likelihood matrix ``A`` (shape ``[n_obs x n_states]``), a
log-preference vector ``C`` (shape ``[n_obs]``), and a prior ``D``
(shape ``[n_states]``):

    VFE = -log P(o | q) + KL(q || D)

where ``P(o | q) = sum_s A[o][s] * q(s)`` is the marginal likelihood
of the observed modality under the current belief.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_EPS = 1e-10


def kl_divergence(p: list[float], q: list[float]) -> float:
    """Compute KL(p || q) = sum_i p[i] * log(p[i] / (q[i] + eps)).

    Args:
        p: First distribution (the one we are measuring from).
        q: Second distribution (the reference).

    Returns:
        Non-negative KL divergence value.
    """
    kl = 0.0
    for pi, qi in zip(p, q, strict=False):
        if pi > _EPS:
            kl += pi * math.log(pi / (qi + _EPS))
    return kl


def free_energy(
    state_dist: list[float],
    obs_idx: int,
    A: list[list[float]],
    C: list[float],
    D: list[float],
) -> float:
    """Compute variational free energy for a single observation.

    VFE = -log P(o=obs_idx | state_dist) + KL(state_dist || D)

    The first term is the negative log-evidence (surprise) of the
    observed modality under the current belief about hidden states.
    The second term penalises deviation from the prior.

    Args:
        state_dist: Current belief over hidden states (sums to 1).
        obs_idx: Index of the observed modality.
        A: Likelihood matrix ``[n_obs x n_states]``.
        C: Log-preference vector ``[n_obs]`` (unused in basic VFE
            but available for expected free energy extensions).
        D: Prior distribution over hidden states.

    Returns:
        Variational free energy (finite float).
    """
    # Marginal likelihood: P(o=obs_idx) = sum_s A[obs_idx][s] * q(s)
    n_obs = len(A)
    if obs_idx < 0 or obs_idx >= n_obs:
        obs_idx = 0
    row = A[obs_idx] if obs_idx < n_obs else []
    p_obs = _EPS
    for a_val, s_val in zip(row, state_dist, strict=False):
        p_obs += a_val * s_val

    neg_log_evidence = -math.log(max(p_obs, _EPS))

    # KL divergence from prior
    kl = kl_divergence(state_dist, D)

    return neg_log_evidence + kl


@dataclass
class EpisodeMetrics:
    """Metrics for a single learning episode.

    Attributes:
        episode_id: Unique episode identifier.
        n_steps: Number of steps in the episode.
        mean_free_energy: Mean VFE across the episode.
        final_free_energy: VFE at the last step.
        n_unique_obs: Number of unique observations seen.
        action_entropy: Shannon entropy of action distribution.
    """
    episode_id: int
    n_steps: int
    mean_free_energy: float
    final_free_energy: float
    n_unique_obs: int = 0
    action_entropy: float = 0.0

    def to_csv_row(self) -> dict[str, Any]:
        """Convert metrics to a dictionary suitable for CSV logging.

        Returns:
            Dictionary with string keys and scalar values for CSV export.

        Example:
            >>> metrics = EpisodeMetrics(episode_id=1, n_steps=5, ...)
            >>> row = metrics.to_csv_row()
            >>> import csv
            >>> csv.DictWriter(f, fieldnames=row.keys()).writerow(row)
        """
        return {
            "episode_id": self.episode_id,
            "n_steps": self.n_steps,
            "mean_free_energy": self.mean_free_energy,
            "final_free_energy": self.final_free_energy,
            "n_unique_obs": self.n_unique_obs,
            "action_entropy": self.action_entropy,
        }


@dataclass
class RunMetrics:
    """Aggregate metrics for a multi-episode learning run.

    Attributes:
        episodes: List of per-episode metrics.
        total_steps: Total inference steps across all episodes.
    """
    episodes: list[EpisodeMetrics]
    total_steps: int = 0

    def summary_statistics(self) -> dict[str, float]:
        """Compute summary statistics over all episodes.

        Returns:
            Dictionary with mean/std/min/max for:
            * ``mean_free_energy_mean``, ``mean_free_energy_std``, etc.
            * ``final_free_energy_mean``, ``final_free_energy_std``, etc.

        Example:
            >>> metrics = RunMetrics(episodes=[...])
            >>> stats = metrics.summary_statistics()
            >>> print(f"Mean VFE: {stats['mean_free_energy_mean']:.4f}")
        """
        if not self.episodes:
            logger.warning("No episodes in RunMetrics; returning NaN-filled stats")
            nan = float("nan")
            return {
                "n_episodes": 0,
                "total_steps": 0,
                "mean_free_energy_mean": nan,
                "mean_free_energy_std": nan,
                "mean_free_energy_min": nan,
                "mean_free_energy_max": nan,
                "final_free_energy_mean": nan,
                "final_free_energy_std": nan,
                "final_free_energy_min": nan,
                "final_free_energy_max": nan,
                "steps_per_episode_mean": nan,
                "steps_per_episode_std": nan,
            }

        mean_fes = [e.mean_free_energy for e in self.episodes]
        final_fes = [e.final_free_energy for e in self.episodes]
        step_counts = [e.n_steps for e in self.episodes]

        def _stats(values: list[float]) -> tuple[float, float, float, float]:
            """Compute mean, std, min, max."""
            if not values:
                return 0.0, 0.0, 0.0, 0.0
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = variance ** 0.5
            return mean, std, min(values), max(values)

        mean_fe_mean, mean_fe_std, mean_fe_min, mean_fe_max = _stats(mean_fes)
        final_fe_mean, final_fe_std, final_fe_min, final_fe_max = _stats(final_fes)
        step_mean, step_std, step_min, step_max = _stats([float(s) for s in step_counts])

        return {
            "n_episodes": len(self.episodes),
            "total_steps": sum(step_counts),
            "mean_free_energy_mean": mean_fe_mean,
            "mean_free_energy_std": mean_fe_std,
            "mean_free_energy_min": mean_fe_min,
            "mean_free_energy_max": mean_fe_max,
            "final_free_energy_mean": final_fe_mean,
            "final_free_energy_std": final_fe_std,
            "final_free_energy_min": final_fe_min,
            "final_free_energy_max": final_fe_max,
            "steps_per_episode_mean": step_mean,
            "steps_per_episode_std": step_std,
        }

    def plot_free_energy(self) -> Any:
        """Plot mean and final VFE trajectories (if matplotlib available).

        Returns:
            A matplotlib Figure object if matplotlib is installed and there
            are episodes to plot; None otherwise.

        Example:
            >>> metrics = RunMetrics(episodes=[...])
            >>> fig = metrics.plot_free_energy()
            >>> if fig:
            ...     fig.show()
        """
        if not self.episodes:
            logger.warning("No episodes to plot")
            return None

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping plot_free_energy()")
            return None

        episode_ids = list(range(len(self.episodes)))
        mean_fes = [e.mean_free_energy for e in self.episodes]
        final_fes = [e.final_free_energy for e in self.episodes]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(episode_ids, mean_fes, "b-o", label="Mean VFE", linewidth=2)
        ax.plot(episode_ids, final_fes, "r--s", label="Final VFE", linewidth=2)
        ax.set_xlabel("Episode", fontsize=12)
        ax.set_ylabel("Free Energy", fontsize=12)
        ax.set_title("VFE Trajectory Over Episodes", fontsize=14)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)

        return fig


__all__ = ["free_energy", "kl_divergence", "EpisodeMetrics", "RunMetrics"]
