from _typeshed import Incomplete
from cogant.simulate.free_energy import FreeEnergyCalculator as FreeEnergyCalculator
from pathlib import Path
from typing import Any

logger: Incomplete
ACTIVE_INFERENCE_AVAILABLE: bool

class ExecutionTrace:
    step: Incomplete
    state: Incomplete
    action: Incomplete
    observation: Incomplete
    reward: Incomplete
    timestamp: Incomplete
    beliefs: Incomplete
    beliefs_prior: Incomplete
    free_energy_before: Incomplete
    free_energy_after: Incomplete
    policy_scores: Incomplete
    action_rationale: Incomplete
    predicted_state: Incomplete
    def __init__(self, step: int, state: dict[str, Any], action: str | None = None, observation: str | None = None, reward: float = 0.0, beliefs: dict[str, float] | None = None, beliefs_prior: dict[str, float] | None = None, free_energy_before: float = 0.0, free_energy_after: float = 0.0, policy_scores: list[tuple[str, float]] | None = None, action_rationale: str | None = None, predicted_state: dict[str, Any] | None = None) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...

class GNNModelRunner:
    package_dir: Path
    manifest: dict[str, Any]
    model: dict[str, Any]
    state_space: dict[str, Any]
    traces: list[ExecutionTrace]
    fe_calculator: FreeEnergyCalculator | None
    beliefs_history: list[dict[str, float]]
    free_energy_trajectory: list[float]
    action_counts: dict[str, int]
    def __init__(self) -> None: ...
    def load_package(self, package_dir: str) -> dict[str, Any]: ...
    def run(self, steps: int = 10) -> dict[str, Any]: ...
    def generate_execution_report(self, trace: dict[str, Any] | None = None) -> str: ...
