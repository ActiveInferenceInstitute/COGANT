from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from cogant.reverse.callable import MatrixFunctions
from cogant.reverse.parser import parse_gnn
from cogant.runtime.inference_records import (
    AxisLabels,
    InferenceOptions,
    InferenceRecord,
    InferenceTrace,
    MatrixSnapshot,
)
from cogant.runtime.loop import AgentRuntime


def _axis_labels(names: Sequence[str], size: int, axis: str) -> tuple[str, ...]:
    if len(names) == size:
        return tuple(names)
    prefix = names[0] if len(names) == 1 else axis
    return tuple(f"{prefix}[{index}]" for index in range(size))


def run_gnn_inference(text: str, options: InferenceOptions | None = None) -> InferenceTrace:
    """Execute parsed GNN matrices without code generation; never invent missing matrices."""
    options = options or InferenceOptions()
    model = parse_gnn(text)
    if model.degraded:
        raise ValueError(
            "inference requires a complete GNN representation without degraded parsing"
        )
    functions = MatrixFunctions(model)
    matrices = MatrixSnapshot(
        A=tuple(tuple(row) for row in functions.A),
        B=tuple(tuple(tuple(cell) for cell in row) for row in functions.B),
        C=tuple(functions.C),
        D=tuple(functions.D),
    )
    ns, no, na = len(matrices.D), len(matrices.A), len(matrices.B[0][0])
    work = options.steps * na * (ns * ns + ns * no)
    if work > options.max_work_units:
        raise ValueError(f"inference work {work} exceeds budget {options.max_work_units}")
    if options.observations is not None and any(o >= no for o in options.observations):
        raise ValueError("observation index is outside the GNN observation axis")
    runtime = AgentRuntime(functions)
    state = list(functions.D)
    records: list[InferenceRecord] = []
    for t in range(options.steps):
        predicted_observation = functions.likelihood(state)
        observation = (
            options.observations[t]
            if options.observations is not None
            else max(range(no), key=predicted_observation.__getitem__)
        )
        step = runtime.step(state, observation, t=t)
        records.append(
            InferenceRecord(
                t=t,
                prior=tuple(state),
                posterior=tuple(step.posterior),
                predicted_belief=tuple(step.state_dist),
                predicted_observation=tuple(predicted_observation),
                observation=observation,
                action=step.action,
                policy_scores=tuple(step.policy_scores),
                free_energy=step.free_energy,
            )
        )
        state = list(step.state_dist)
    return InferenceTrace(
        source_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        matrices_sha256=matrices.digest(),
        model_name=model.raw_model_name,
        mode="observations" if options.observations is not None else "model_rollout",
        labels=AxisLabels(
            states=_axis_labels(model.hidden_states, ns, "state"),
            observations=_axis_labels(model.observations, no, "observation"),
            actions=_axis_labels(model.actions, na, "action"),
        ),
        matrices=matrices,
        trace=tuple(records),
    )


def write_inference_trace_artifact(run_dir: str | Path, *, steps: int = 8) -> Path:
    """Regenerate a run's model rollout from its exported GNN; bind its relative source path."""
    root = Path(run_dir)
    source = root / "gnn_package" / "model.gnn.md"
    text = source.read_bytes().decode("utf-8")
    trace = run_gnn_inference(text, InferenceOptions(steps=steps))
    trace = trace.model_copy(update={"source_artifact": "gnn_package/model.gnn.md"})
    data = root / "data" if (root / "data").is_dir() else root
    data.mkdir(parents=True, exist_ok=True)
    path = data / "inference_trace.json"
    path.write_text(trace.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def load_inference_trace(run_dir: str | Path) -> InferenceTrace:
    """Admit a stored trace only when its source digest and parsed matrices still agree."""
    root = Path(run_dir)
    data = root / "data" if (root / "data").is_dir() else root
    trace = InferenceTrace.model_validate_json((data / "inference_trace.json").read_bytes())
    source = (root / "gnn_package" / "model.gnn.md").read_bytes()
    if hashlib.sha256(source).hexdigest() != trace.source_sha256:
        raise ValueError("inference trace is stale: exported GNN source digest changed")
    model = parse_gnn(source.decode("utf-8"))
    matrices = MatrixSnapshot(
        A=tuple(tuple(row) for row in model.A),
        B=tuple(tuple(tuple(cell) for cell in row) for row in model.B),
        C=tuple(model.C),
        D=tuple(model.D),
    )
    if matrices.digest() != trace.matrices_sha256:
        raise ValueError("inference trace matrices disagree with the exported GNN")
    replay = run_gnn_inference(
        source.decode("utf-8"),
        InferenceOptions(
            steps=len(trace.trace),
            observations=(
                tuple(record.observation for record in trace.trace)
                if trace.mode == "observations"
                else None
            ),
        ),
    )
    if trace.model_dump(exclude={"source_artifact"}) != replay.model_dump(
        exclude={"source_artifact"}
    ):
        raise ValueError("inference trace records disagree with canonical execution")
    return trace
