# `cogant.pipeline`

DAG types used by `cogant.api.pipeline.PipelineRunner` to schedule and
record stage execution. The runtime stages themselves live under
[`cogant.api.pipeline`](../api/AGENTS.md); this package only carries the
typed primitives so other modules (CLI, server, observability) can build
or inspect a stage graph without importing the full runner.

## Public API

Re-exported from `cogant/pipeline/__init__.py`:

| Symbol | Role |
| --- | --- |
| `Stage` | One pipeline node (name + handler + dependency list). |
| `PipelineDAG` | Topologically ordered set of `Stage` objects with cycle detection. |
| `StageStatus` | Enum: `PENDING` / `RUNNING` / `COMPLETED` / `FAILED` / `SKIPPED`. |
| `StageResult` | Per-stage outcome (status, output, error, duration, timestamps). |
| `DAGResult` | Aggregate of all `StageResult`s with overall status helpers. |

## Conventions

* `Stage.name` is the stable string used in logs, the bundle's
  `stage_results` dict, and `cogant doctor`'s status table.
* `PipelineDAG.topological_sort()` is the canonical run order.
* `StageResult.duration_ms` feeds `PipelineResult.timing` for profiling.
* Failures short-circuit downstream stages (`SKIPPED`) so the bundle
  always carries enough state to diagnose what stopped.

See [`AGENTS.md`](AGENTS.md) for invariants and the parent index in
[`../AGENTS.md`](../AGENTS.md) for how the DAG plugs into the full
forward-path runner.
