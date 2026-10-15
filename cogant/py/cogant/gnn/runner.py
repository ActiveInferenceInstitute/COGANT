"""Execute a package's declared matrices through the shared categorical kernel."""

from __future__ import annotations

import time
from pathlib import Path

from pydantic import JsonValue, TypeAdapter

from cogant.gnn.execution import ExecutionTrace, RunnerResult, execution_result, render_report
from cogant.reverse.callable import MatrixFunctions
from cogant.reverse.parser import parse_gnn
from cogant.runtime.categorical import CategoricalModel
from cogant.runtime.inference import run_gnn_inference
from cogant.runtime.inference_records import InferenceOptions

__all__ = ["ExecutionTrace", "GNNModelRunner", "load_gnn_package"]


class GNNModelRunner:
    """Own a validated GNN snapshot and its most recent model rollout.

    Observations are modes of A times the incoming belief, not measurements
    of source program execution. Actions minimize one-step risk-plus-ambiguity
    expected free energy.
    """

    def __init__(self) -> None:
        self.package_dir = Path(".")
        self.manifest: dict[str, JsonValue] = {}
        self.traces: list[ExecutionTrace] = []
        self.beliefs_history: list[dict[str, float]] = []
        self.free_energy_trajectory: list[float] = []
        self.action_counts: dict[str, int] = {}
        self.last_error: str | None = None
        self._source: str | None = None
        self._result: RunnerResult | None = None
        self._work_per_step = 0

    def _clear_run(self) -> None:
        self.traces = []
        self.beliefs_history = []
        self.free_energy_trajectory = []
        self.action_counts = {}
        self.last_error = None
        self._result = None

    def load_package(self, package_dir: str) -> dict[str, JsonValue]:
        """Load complete model.gnn.md matrices; invalidate stale state on failure."""
        self._source = None
        self.manifest = {}
        self._clear_run()
        self.package_dir = Path(package_dir)
        manifest = TypeAdapter(dict[str, JsonValue]).validate_json(
            (self.package_dir / "manifest.json").read_bytes()
        )
        source = (self.package_dir / "model.gnn.md").read_bytes().decode("utf-8")
        model = parse_gnn(source)
        if model.degraded:
            raise ValueError("execution requires complete, non-degraded GNN matrices")
        functions = MatrixFunctions(model)
        categorical = CategoricalModel(functions.A, functions.B, functions.C, functions.D)
        states, observations = len(functions.D), len(functions.A)
        self._work_per_step = categorical.n_actions * (states * states + states * observations)
        self.manifest = manifest
        self._source = source
        return manifest

    def run(self, steps: int = 10) -> RunnerResult:
        """Execute 1 to 10,000 steps; invalid input fails without a success report."""
        self._clear_run()
        if self._source is None:
            raise RuntimeError("Package not loaded. Call load_package first.")
        try:
            inference = run_gnn_inference(self._source, InferenceOptions(steps=steps))
        except ValueError as error:
            self.last_error = str(error)
            raise
        self.traces = [
            ExecutionTrace.from_record(record, inference.labels) for record in inference.trace
        ]
        self.beliefs_history = [
            dict(zip(inference.labels.states, inference.matrices.D, strict=True))
        ]
        self.beliefs_history.extend(trace.beliefs.copy() for trace in self.traces)
        self.free_energy_trajectory = [trace.free_energy_after for trace in self.traces]
        for trace in self.traces:
            self.action_counts[trace.action] = self.action_counts.get(trace.action, 0) + 1
        self._result = execution_result(inference, self.traces, self.action_counts)
        return self._result

    def generate_execution_report(self, trace: RunnerResult | None = None) -> str:
        """Describe matrix inference without claiming program or control success."""
        result = trace if trace is not None else self._result
        if result is None:
            detail = (
                f"Execution rejected: {self.last_error}"
                if self.last_error
                else "No traces to report."
            )
            return f"# GNN Execution Report\n\n{detail}\n"
        return render_report(result)

    def run_with_profiling(
        self, num_steps: int = 10, num_trials: int = 1
    ) -> tuple[list[dict[str, JsonValue]], dict[str, float]]:
        """Measure complete inference runs; each trial restarts from exported D."""
        self._clear_run()
        InferenceOptions(steps=num_trials)
        InferenceOptions(steps=num_steps)
        if num_steps * num_trials > 10_000:
            raise ValueError("profiling exceeds the 10,000 total-step budget")
        if num_steps * num_trials * self._work_per_step > InferenceOptions().max_work_units:
            raise ValueError("profiling exceeds the combined matrix-work budget")
        traces: list[dict[str, JsonValue]] = []
        start = time.perf_counter()
        for trial in range(num_trials):
            result = self.run(num_steps)
            for item in result["traces"]:
                record = item.copy()
                record["trial"] = trial
                traces.append(record)
        return traces, {"total_ms": (time.perf_counter() - start) * 1000.0}


load_gnn_package = GNNModelRunner().load_package
