"""Records distinguish corrected posterior beliefs from next-step predictions."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AgentStep:
    """One cycle: posterior and VFE precede control; state_dist follows control."""

    t: int
    state_dist: list[float]
    obs: int
    action: int
    free_energy: float
    posterior: list[float] = field(default_factory=list)
    policy_scores: list[float] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EpisodeResult:
    """Observed posterior soft counts and the final corrected posterior."""

    steps: list[AgentStep]
    final_posterior: list[float]
    obs_counts: list[float]
    obs_state_counts: list[list[float]]
    mean_free_energy: float
    final_free_energy: float


@dataclass(frozen=True, slots=True)
class MultiEpisodeResult:
    """Episode metrics and learned-prior snapshots."""

    episodes: list[EpisodeResult]
    vfe_trajectory: list[float]
    final_vfe_trajectory: list[float]
    D_trajectory: list[list[float]]
    learning_rate: float


def summarize_episode(steps: list[AgentStep], initial: list[float], n_obs: int) -> EpisodeResult:
    """Accumulate observation counts using the posterior before action prediction."""
    counts = [0.0] * n_obs
    joint = [[0.0] * len(initial) for _ in range(n_obs)]
    for step in steps:
        counts[step.obs] += 1
        for s, q in enumerate(step.posterior):
            joint[step.obs][s] += q
    return EpisodeResult(
        steps,
        list(steps[-1].posterior) if steps else list(initial),
        counts,
        joint,
        sum(s.free_energy for s in steps) / len(steps) if steps else float("nan"),
        steps[-1].free_energy if steps else float("nan"),
    )
