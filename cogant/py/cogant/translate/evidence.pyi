from pathlib import Path
from typing import Any

def load_reviewer_annotations(path: str | Path) -> dict[str, dict[str, Any]]: ...
def apply_reviewer_annotations(
    trace: dict[str, Any],
    annotations: dict[str, dict[str, Any]] | list[dict[str, Any]] | str | Path | None,
) -> dict[str, Any]: ...
def calibrate_rule_evidence_trace(trace: dict[str, Any]) -> dict[str, Any]: ...
def build_rule_evidence_trace(
    mappings: Any,
    *,
    graph: Any = ...,
    match_log: list[dict[str, Any]] | None = ...,
    annotations: dict[str, dict[str, Any]] | list[dict[str, Any]] | str | Path | None = ...,
) -> dict[str, Any]: ...
