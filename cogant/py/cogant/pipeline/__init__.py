"""Pipeline execution engine with DAG-based stage scheduling."""

from cogant.pipeline.dag import DAGResult, PipelineDAG, Stage, StageResult, StageStatus

# Canonical runner stage sequence — the single source of truth for both code and
# documentation. ``tools/audit_stage_list.py`` enforces that every prose stage
# list in docs/CLI docstrings/init templates matches this tuple verbatim. Do not
# duplicate or paraphrase this list elsewhere in the package; import from here.
RUNNER_STAGES: tuple[str, ...] = (
    "ingest",
    "static",
    "normalize",
    "graph",
    "dynamic",
    "translate",
    "statespace",
    "process",
    "export",
    "validate",
)

__all__ = [
    "DAGResult",
    "PipelineDAG",
    "RUNNER_STAGES",
    "Stage",
    "StageResult",
    "StageStatus",
]
