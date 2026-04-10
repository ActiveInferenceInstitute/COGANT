# Agents — py/cogant/pipeline

## Owner

Runtime Lead

## Responsibilities

DAG-based pipeline scheduling: stages, dependencies, and aggregated `DAGResult` / `StageResult` for orchestrated runs (distinct from `api/orchestration.py` stage functions, which execute work; this module models the graph).

## Coordination

Composable with `api/pipeline.py` runners that map named stages onto orchestration calls.

## Files

- `dag.py` — `PipelineDAG`, `Stage`, `StageStatus`, `StageResult`, `DAGResult`.
- `__init__.py` — public exports.
