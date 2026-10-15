"""Matrix-based perception, finite-policy selection, and episode learning."""

from __future__ import annotations

import math
import time
import types
from typing import Any

from cogant.runtime.categorical import CategoricalModel, distribution
from cogant.runtime.config import AgentConfig
from cogant.runtime.metrics import kl_divergence
from cogant.runtime.records import AgentStep, EpisodeResult, MultiEpisodeResult, summarize_episode


def _normalize(dist: list[float]) -> list[float]:
    if not dist or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in dist):
        raise ValueError("distribution must be nonempty, finite and non-negative")
    total = math.fsum(dist)
    if total <= 0:
        raise ValueError("distribution has zero probability mass")
    return [v / total for v in dist]


def _argmax(values: list[float]) -> int:
    if not values:
        raise ValueError("argmax requires a nonempty sequence")
    return max(range(len(values)), key=values.__getitem__)


class AgentRuntime:
    """Mutable agent matrices with shared categorical inference and learning."""

    def __init__(self, matrices: Any) -> None:
        self.A: list[list[float]] = matrices.A
        self.B: list[list[list[float]]] = matrices.B
        self.C: list[float] = matrices.C
        self.D: list[float] = matrices.D
        self._model = CategoricalModel(self.A, self.B, self.C, self.D)
        self._likelihood = self._model.observe
        self._transition = self._model.predict
        self._n_states = len(self.D)
        self._n_obs = len(self.A)
        self._n_actions = self._model.n_actions
        self._episode_count = 0
        self._last_free_energy = float("nan")

    @classmethod
    def from_matrices_dict(cls, d: dict[str, Any]) -> AgentRuntime:
        return cls(types.SimpleNamespace(A=d["A"], B=d["B"], C=d["C"], D=d["D"]))

    def step(self, state_dist: list[float], obs_idx: int, t: int = 0) -> AgentStep:
        """Filter then choose minimum one-step EFE, with lowest-index ties."""
        result = self._model.step(state_dist, obs_idx)
        self._last_free_energy = result.free_energy
        return AgentStep(
            t,
            result.prediction,
            obs_idx,
            result.action,
            result.free_energy,
            result.posterior,
            result.policy_scores,
        )

    def run_n_steps(self, n: int, initial_state: list[float] | None = None) -> list[AgentStep]:
        """Run a deterministic model rollout using modal predicted observations."""
        if n < 0:
            raise ValueError("step count must be non-negative")
        state = list(self.D if initial_state is None else initial_state)
        distribution(state)
        steps = []
        for t in range(n):
            result = self.step(state, _argmax(self._likelihood(state)), t)
            steps.append(result)
            state = result.state_dist
        return steps

    def run_until_convergence(
        self, initial_state: list[float] | None = None, cfg: AgentConfig | None = None
    ) -> list[AgentStep]:
        cfg = cfg if cfg is not None else AgentConfig()
        state = list(self.D if initial_state is None else initial_state)
        distribution(state)
        steps = []
        for t in range(cfg.max_steps):
            result = self.step(state, _argmax(self._likelihood(state)), t)
            steps.append(result)
            if t > 0 and kl_divergence(result.state_dist, state) < cfg.convergence_threshold:
                break
            state = result.state_dist
        return steps

    def run_episode(self, n_steps: int, initial_state: list[float] | None = None) -> EpisodeResult:
        initial = list(self.D if initial_state is None else initial_state)
        return summarize_episode(self.run_n_steps(n_steps, initial), initial, self._n_obs)

    def update_D_from_posterior(self, posterior: list[float]) -> list[float]:
        if len(posterior) != self._n_states:
            raise ValueError("posterior has incompatible state dimensions")
        normalized = _normalize(posterior)
        k = self._episode_count
        self.D[:] = [(d * k + q) / (k + 1) for d, q in zip(self.D, normalized, strict=True)]
        self._episode_count += 1
        return self.D

    def update_A_from_counts(
        self, obs_state_counts: list[list[float]], learning_rate: float = 0.1
    ) -> list[list[float]]:
        """Blend conditional P(observation | state) counts, leaving unseen states unchanged."""
        if not math.isfinite(learning_rate) or not 0 <= learning_rate <= 1:
            raise ValueError("learning_rate must be finite and in [0, 1]")
        if len(obs_state_counts) != self._n_obs or any(
            len(row) != self._n_states for row in obs_state_counts
        ):
            raise ValueError("observation-state counts have incompatible dimensions")
        if any(not math.isfinite(v) or v < 0 for row in obs_state_counts for v in row):
            raise ValueError("observation-state counts must be finite and non-negative")
        for s in range(self._n_states):
            total = math.fsum(row[s] for row in obs_state_counts)
            if total > 0:
                for o in range(self._n_obs):
                    self.A[o][s] = (1 - learning_rate) * self.A[o][
                        s
                    ] + learning_rate * obs_state_counts[o][s] / total
        return self.A

    def run_multi_episode(
        self,
        n_episodes: int,
        steps_per_episode: int,
        learning_rate: float = 0.1,
        initial_state: list[float] | None = None,
    ) -> MultiEpisodeResult:
        if n_episodes < 0:
            raise ValueError("episode count must be non-negative")
        episodes = []
        priors = []
        for _ in range(n_episodes):
            result = self.run_episode(steps_per_episode, initial_state)
            episodes.append(result)
            self.update_D_from_posterior(result.final_posterior)
            self.update_A_from_counts(result.obs_state_counts, learning_rate)
            priors.append(list(self.D))
        return MultiEpisodeResult(
            episodes,
            [e.mean_free_energy for e in episodes],
            [e.final_free_energy for e in episodes],
            priors,
            learning_rate,
        )

    def run_episode_with_logging(
        self, obs_sequence: list[int]
    ) -> tuple[EpisodeResult, list[dict[str, Any]]]:
        state = list(self.D)
        steps = []
        logs = []
        for t, obs in enumerate(obs_sequence):
            result = self.step(state, obs, t)
            steps.append(result)
            logs.append(
                {
                    "step": t,
                    "observation": obs,
                    "action": result.action,
                    "free_energy": result.free_energy,
                }
            )
            state = result.state_dist
        return summarize_episode(steps, self.D, self._n_obs), logs

    def benchmark(self, n_episodes: int = 10) -> dict[str, float]:
        if n_episodes <= 0:
            raise ValueError("benchmark episode count must be positive")
        elapsed = []
        for _ in range(n_episodes):
            start = time.perf_counter()
            self.run_episode(5)
            elapsed.append((time.perf_counter() - start) * 1000)
        mean = sum(elapsed) / len(elapsed)
        return {
            "mean_ms": mean,
            "std_ms": (sum((x - mean) ** 2 for x in elapsed) / len(elapsed)) ** 0.5,
            "min_ms": min(elapsed),
            "max_ms": max(elapsed),
        }

    def reset(self) -> None:
        self._episode_count = 0
        self._last_free_energy = float("nan")

    def get_free_energy(self) -> float:
        return self._last_free_energy

    def to_dict(self) -> dict[str, Any]:
        return {
            "A": self.A,
            "B": self.B,
            "C": self.C,
            "D": self.D,
            "n_states": self._n_states,
            "n_obs": self._n_obs,
            "n_actions": self._n_actions,
            "episode_count": self._episode_count,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentRuntime:
        runtime = cls.from_matrices_dict(d)
        runtime._episode_count = d.get("episode_count", 0)
        return runtime


def run_n_steps(
    runtime: AgentRuntime, n: int, initial_state: list[float] | None = None
) -> list[AgentStep]:
    return runtime.run_n_steps(n, initial_state)


def run_until_convergence(
    runtime: AgentRuntime, initial_state: list[float] | None = None, cfg: AgentConfig | None = None
) -> list[AgentStep]:
    return runtime.run_until_convergence(initial_state, cfg)


__all__ = [
    "AgentStep",
    "AgentRuntime",
    "EpisodeResult",
    "MultiEpisodeResult",
    "run_n_steps",
    "run_until_convergence",
]
