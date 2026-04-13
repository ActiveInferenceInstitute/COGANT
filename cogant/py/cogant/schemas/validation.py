"""
ValidationReport: Quality and completeness assessment of analysis artifacts.

Provides metrics, checks, and recommendations for validating bundle contents
and identifying gaps or issues in analysis results.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import ConfigDict, Field

from .base import CogantBaseModel, StableID


class CheckLevel(StrEnum):
    """Severity levels for validation checks."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class CheckStatus(StrEnum):
    """Outcome of a validation check."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    INCONCLUSIVE = "inconclusive"


class ValidationCheck(CogantBaseModel):
    """
    A single validation check performed on bundle contents.
    """

    check_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    description: str | None = Field(
        default=None, description="Detailed description of check"
    )

    # Check properties
    check_type: str = Field(
        ...,
        description="Type of check (e.g., 'schema_validity', 'referential_integrity', 'completeness')",
    )
    level: CheckLevel = Field(
        default=CheckLevel.WARNING,
        description="Severity level if check fails",
    )
    status: CheckStatus = Field(
        ..., description="Outcome of check"
    )

    # Details
    details: str | None = Field(
        default=None, description="Detailed results/explanation"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Specific issues found",
    )
    affected_elements: list[str] = Field(
        default_factory=list,
        description="IDs of elements affected by issue",
    )

    # Recommendation
    recommendation: str | None = Field(
        default=None,
        description="Suggested action to resolve issue",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When check was performed",
    )


class ValidationMetrics(CogantBaseModel):
    """
    Quantitative metrics about bundle contents.
    """

    # Counts
    node_count: int = Field(default=0, description="Total nodes in graph")
    edge_count: int = Field(default=0, description="Total edges in graph")
    mapping_count: int = Field(
        default=0, description="Total semantic mappings"
    )
    state_variable_count: int = Field(
        default=0, description="Total state variables"
    )
    process_stage_count: int = Field(
        default=0, description="Total process stages"
    )
    provenance_record_count: int = Field(
        default=0, description="Total provenance records"
    )

    # Coverage metrics
    node_provenance_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of nodes with provenance [0, 1]",
    )
    edge_provenance_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of edges with provenance",
    )
    mapping_review_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of mappings reviewed",
    )
    observable_state_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of state variables observable",
    )

    # Quality metrics
    unresolved_reference_count: int = Field(
        default=0,
        description="Number of dangling references",
    )
    unresolved_reference_fraction: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of references unresolved",
    )
    confidence_mean: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Mean confidence across all confidence metrics",
    )
    confidence_min: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score",
    )
    confidence_stddev: float = Field(
        default=0.0,
        ge=0.0,
        description="Standard deviation of confidence scores",
    )

    # Graph structure
    graph_density: float = Field(
        default=0.0,
        description="Graph density (edges / max_possible_edges)",
    )
    average_node_degree: float = Field(
        default=0.0,
        description="Average node degree",
    )
    largest_strongly_connected_component_size: int | None = Field(
        default=None,
        description="Size of largest SCC",
    )

    # Custom metrics
    custom_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom/domain-specific metrics",
    )


class ValidationRecommendation(CogantBaseModel):
    """
    A recommendation for improving bundle quality.
    """

    recommendation_id: str = Field(..., description="Unique identifier")
    category: str = Field(
        ...,
        description="Category (e.g., 'completeness', 'coverage', 'review')",
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium",
        description="Priority for addressing",
    )
    title: str = Field(..., description="Short title")
    description: str = Field(
        ..., description="Detailed recommendation"
    )
    affected_elements: list[str] = Field(
        default_factory=list,
        description="IDs of affected elements",
    )
    estimated_effort: str | None = Field(
        default=None,
        description="Estimated effort to address (e.g., 'quick', 'medium', 'large')",
    )


class ValidationReport(CogantBaseModel):
    """
    Comprehensive validation assessment of a bundle.

    Provides detailed results of all validation checks, metrics, and
    recommendations for improving bundle quality.
    """

    report_id: StableID = Field(
        ..., description="Unique identifier for report"
    )
    bundle_id: str = Field(
        ..., description="ID of bundle being validated"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When report was generated",
    )
    created_by: str | None = Field(
        default=None, description="Tool/user that created report"
    )

    # Checks
    checks: list[ValidationCheck] = Field(
        default_factory=list,
        description="Results of validation checks",
    )

    # Metrics
    metrics: ValidationMetrics = Field(
        default_factory=ValidationMetrics,
        description="Quantitative metrics",
    )

    # Recommendations
    recommendations: list[ValidationRecommendation] = Field(
        default_factory=list,
        description="Recommendations for improvement",
    )

    # Overall status
    is_valid: bool = Field(
        default=True,
        description="Whether bundle passes all critical checks",
    )
    overall_quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall quality score [0, 1]",
    )
    summary: str | None = Field(
        default=None,
        description="Human-readable summary of validation",
    )

    # Configuration
    validation_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration used for validation",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": "val_report_abc123",
                "bundle_id": "bundle_550e8400",
                "is_valid": True,
                "overall_quality_score": 0.85,
                "metrics": {
                    "node_count": 250,
                    "edge_count": 1200,
                    "mapping_count": 150,
                    "node_provenance_coverage": 0.95,
                    "edge_provenance_coverage": 0.88,
                    "confidence_mean": 0.87,
                    "unresolved_reference_count": 3,
                    "graph_density": 0.023,
                },
                "checks": [
                    {
                        "check_id": "check_001",
                        "name": "Schema Validity",
                        "status": "passed",
                        "level": "error",
                    },
                    {
                        "check_id": "check_002",
                        "name": "Referential Integrity",
                        "status": "passed",
                        "level": "error",
                    },
                ],
                "recommendations": [
                    {
                        "recommendation_id": "rec_001",
                        "category": "coverage",
                        "priority": "medium",
                        "title": "Add provenance for remaining edges",
                        "description": "12% of edges lack provenance evidence",
                    }
                ],
            }
        }
    )
