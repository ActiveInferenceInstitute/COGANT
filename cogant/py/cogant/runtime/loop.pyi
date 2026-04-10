from dataclasses import dataclass
from typing import Any

from cogant.runtime.config import AgentConfig

__all__ = ['AgentStep', 'AgentRuntime', 'EpisodeResult', 'MultiEpisodeResult', 'run_n_steps', 'run_until_convergence']

@dataclass
class AgentStep:
    t: int
    state_dist: list[float]
    obs: int
    action: int
    free_energy: float

@dataclass
class EpisodeResult:
    steps: list[AgentStep]
    final_posterior: list[float]
    obs_counts: list[float]
    obs_state_counts: list[list[float]]
    mean_free_energy: float
    final_free_energy: float

@dataclass
class MultiEpisodeResult:
    episodes: list[EpisodeResult]
    vfe_trajectory: list[float]
    final_vfe_trajectory: list[float]
    D_trajectory: list[list[float]]
    learning_rate: float

class AgentRuntime:
    A: list[list[float]]
    B: list[list[list[float]]]
    C: list[float]
    D: list[float]
    def __init__(self, matrices: Any) -> None: ...
    @classmethod
    def from_matrices_dict(cls, d: dict[str, Any]) -> AgentRuntime: ...
    def step(self, state_dist: list[float], obs_idx: int, t: int = 0) -> AgentStep: ...
    def run_n_steps(self, n: int, initial_state: list[float] | None = None) -> list[AgentStep]: ...
    def run_until_convergence(self, initial_state: list[float] | None = None, cfg: AgentConfig | None = None) -> list[AgentStep]: ...
    def run_episode(self, n_steps: int, initial_state: list[float] | None = None) -> EpisodeResult: ...
    def update_D_from_posterior(self, posterior: list[float]) -> list[float]: ...
    def update_A_from_counts(self, obs_state_counts: list[list[float]], learning_rate: float = 0.1) -> list[list[float]]: ...
    def run_multi_episode(self, n_episodes: int, steps_per_episode: int, learning_rate: float = 0.1, initial_state: list[float] | None = None) -> MultiEpisodeResult: ...

def run_n_steps(runtime: AgentRuntime, n: int, initial_state: list[float] | None = None) -> list[AgentStep]: ...
def run_until_convergence(runtime: AgentRuntime, initial_state: list[float] | None = None, cfg: AgentConfig | None = None) -> list[AgentStep]: ...
