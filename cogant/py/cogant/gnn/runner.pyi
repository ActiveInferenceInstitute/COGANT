from pathlib import Path

from pydantic import JsonValue

from cogant.gnn.execution import ExecutionTrace as ExecutionTrace
from cogant.gnn.execution import RunnerResult

class GNNModelRunner:
    package_dir: Path
    manifest: dict[str, JsonValue]
    traces: list[ExecutionTrace]
    beliefs_history: list[dict[str, float]]
    free_energy_trajectory: list[float]
    action_counts: dict[str, int]
    last_error: str | None
    def __init__(self) -> None: ...
    def load_package(self, package_dir: str) -> dict[str, JsonValue]: ...
    def run(self, steps: int = 10) -> RunnerResult: ...
    def run_with_profiling(
        self, num_steps: int = 10, num_trials: int = 1
    ) -> tuple[list[dict[str, JsonValue]], dict[str, float]]: ...
    def generate_execution_report(self, trace: RunnerResult | None = None) -> str: ...

def load_gnn_package(package_dir: str) -> dict[str, JsonValue]: ...
