from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel
from cogant.validate.schema_check import ValidationIssue as ValidationIssue

@dataclass
class ValidationReport:
    id: str
    schema_name: str
    validated_at: datetime
    model_id: str
    issues: list[ValidationIssue]
    is_valid: bool
    coverage_score: float
    confidence_score: float
    summary: str
    details: dict[str, Any] = field(default_factory=dict)

class ReportGenerator:
    graph: Any
    state_space: Any
    process: Any
    schema_name: Any
    def __init__(self, program_graph: ProgramGraph, state_space_model: StateSpaceModel, process_model: ProcessModel, schema_name: str) -> None: ...
    def generate(self, provenance_records: dict[str, list[object]] | None = None) -> ValidationReport: ...
    def export_to_dict(self, report: ValidationReport) -> dict[str, Any]: ...
    def export_to_json_string(self, report: ValidationReport) -> str: ...
