from .base import CogantBaseModel as CogantBaseModel, StableID as StableID
from _typeshed import Incomplete
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar, Literal

class CheckLevel(StrEnum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'

class CheckStatus(StrEnum):
    PASSED = 'passed'
    FAILED = 'failed'
    SKIPPED = 'skipped'
    INCONCLUSIVE = 'inconclusive'

class ValidationCheck(CogantBaseModel):
    check_id: str
    name: str
    description: str | None
    check_type: str
    level: CheckLevel
    status: CheckStatus
    details: str | None
    issues: list[str]
    affected_elements: list[str]
    recommendation: str | None
    timestamp: datetime

class ValidationMetrics(CogantBaseModel):
    node_count: int
    edge_count: int
    mapping_count: int
    state_variable_count: int
    process_stage_count: int
    provenance_record_count: int
    node_provenance_coverage: float
    edge_provenance_coverage: float
    mapping_review_coverage: float
    observable_state_coverage: float
    unresolved_reference_count: int
    unresolved_reference_fraction: float
    confidence_mean: float
    confidence_min: float
    confidence_stddev: float
    graph_density: float
    average_node_degree: float
    largest_strongly_connected_component_size: int | None
    custom_metrics: dict[str, Any]

class ValidationRecommendation(CogantBaseModel):
    recommendation_id: str
    category: str
    priority: Literal['low', 'medium', 'high', 'critical']
    title: str
    description: str
    affected_elements: list[str]
    estimated_effort: str | None

class ValidationReport(CogantBaseModel):
    report_id: StableID
    bundle_id: str
    created_at: datetime
    created_by: str | None
    checks: list[ValidationCheck]
    metrics: ValidationMetrics
    recommendations: list[ValidationRecommendation]
    is_valid: bool
    overall_quality_score: float
    summary: str | None
    validation_config: dict[str, Any]
    model_config: ClassVar[Incomplete]
