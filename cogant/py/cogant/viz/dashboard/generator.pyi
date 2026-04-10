from pathlib import Path
from typing import Any

from _typeshed import Incomplete as Incomplete

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import SemanticMapping as SemanticMapping
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel
from cogant.validate.report import ValidationReport as ValidationReport

logger: Incomplete

class DashboardGenerator:
    graph: Incomplete
    state_space: Incomplete
    process_model: Incomplete
    semantic_mappings: Incomplete
    mermaid_diagrams: Incomplete
    validation_report: Incomplete
    repo_name: Incomplete
    output_dir: Incomplete
    trace_data: Incomplete
    gnn_validation: Incomplete
    def __init__(self, graph: ProgramGraph, state_space: StateSpaceModel, process_model: ProcessModel, semantic_mappings: dict[str, SemanticMapping], mermaid_diagrams: dict[str, str], validation_report: ValidationReport, repo_name: str, output_dir: Path | None = None, trace_data: dict[str, Any] | None = None, gnn_validation: dict[str, Any] | None = None) -> None: ...
    def generate(self) -> str: ...
