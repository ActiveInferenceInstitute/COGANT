from __future__ import annotations

from pathlib import Path
from typing import Any

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import SemanticMapping as SemanticMapping
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel
from cogant.validate.report import ValidationReport as ValidationReport

class DashboardGenerator:
    graph: Any
    state_space: Any
    process_model: Any
    semantic_mappings: Any
    mermaid_diagrams: Any
    validation_report: Any
    repo_name: Any
    output_dir: Any
    trace_data: Any
    gnn_validation: Any
    def __init__(
        self,
        graph: ProgramGraph,
        state_space: StateSpaceModel,
        process_model: ProcessModel,
        semantic_mappings: dict[str, SemanticMapping],
        mermaid_diagrams: dict[str, str],
        validation_report: ValidationReport,
        repo_name: str,
        output_dir: Path | None = None,
        trace_data: dict[str, Any] | None = None,
        gnn_validation: dict[str, Any] | None = None,
    ) -> None: ...
    def generate(self) -> str: ...
