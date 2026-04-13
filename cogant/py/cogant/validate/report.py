"""
Validation report generation.

Compiles all validation results into comprehensive ValidationReport.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel
from cogant.validate.integrity import IntegrityChecker
from cogant.validate.provenance_check import ProvenanceChecker
from cogant.validate.schema_check import SchemaValidator, ValidationIssue

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Complete validation report."""
    id: str
    schema_name: str
    validated_at: datetime
    model_id: str
    issues: list[ValidationIssue]
    is_valid: bool
    coverage_score: float  # 0-1
    confidence_score: float  # 0-1
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """
    Generates comprehensive validation reports by running all validators
    and compiling results.
    """

    def __init__(
        self,
        program_graph: ProgramGraph,
        state_space_model: StateSpaceModel,
        process_model: ProcessModel,
        schema_name: str,
    ):
        """
        Initialize the generator.

        Args:
            program_graph: The program graph.
            state_space_model: The state space model.
            process_model: The process model.
            schema_name: Name of the schema.
        """
        self.graph = program_graph
        self.state_space = state_space_model
        self.process = process_model
        self.schema_name = schema_name

    def generate(
        self,
        provenance_records: dict[str, list[object]] | None = None,
    ) -> ValidationReport:
        """
        Generate a complete validation report.

        Args:
            provenance_records: Optional provenance records dictionary.

        Returns:
            Compiled ValidationReport.
        """
        logger.info(f"Generating validation report for '{self.schema_name}'...")

        # Run all validators
        schema_validator = SchemaValidator()
        schema_issues = []
        schema_issues.extend(schema_validator.validate_program_graph(self.graph))
        schema_issues.extend(schema_validator.validate_state_space(self.state_space))
        schema_issues.extend(schema_validator.validate_process_model(self.process))

        integrity_checker = IntegrityChecker()
        integrity_issues = []
        integrity_issues.extend(integrity_checker.check_program_graph(self.graph))
        integrity_issues.extend(integrity_checker.check_state_space(self.state_space))
        integrity_issues.extend(integrity_checker.check_process_model(self.process))

        provenance_checker = ProvenanceChecker(provenance_records)
        provenance_gaps = []
        provenance_gaps.extend(provenance_checker.check_graph_provenance(self.graph))
        provenance_gaps.extend(provenance_checker.check_state_space_provenance(self.state_space))

        # Compile all issues
        all_issues = schema_issues + integrity_issues
        for gap in provenance_gaps:
            # Convert gap to issue
            issue = ValidationIssue(
                id=gap.element_id,
                severity=gap.severity,
                category="provenance",
                message=gap.message,
                affected_ids=[gap.element_id],
            )
            all_issues.append(issue)

        # Calculate scores
        is_valid = all(i.severity != "error" for i in all_issues)
        coverage_score = provenance_checker.get_coverage_percentage(
            len(self.graph.nodes) + len(self.state_space.variables)
        ) / 100.0

        confidence_score = self._compute_confidence_score(all_issues)

        # Generate summary
        summary = self._generate_summary(all_issues, is_valid)

        report = ValidationReport(
            id=f"report_{self.schema_name}",
            schema_name=self.schema_name,
            validated_at=datetime.now(),
            model_id=self.state_space.id,
            issues=all_issues,
            is_valid=is_valid,
            coverage_score=coverage_score,
            confidence_score=confidence_score,
            summary=summary,
            details={
                "schema_issues": len(schema_issues),
                "integrity_issues": len(integrity_issues),
                "provenance_gaps": len(provenance_gaps),
                "graph_nodes": len(self.graph.nodes),
                "graph_edges": len(self.graph.edges),
                "state_variables": len(self.state_space.variables),
                "process_stages": len(self.process.stages),
                "process_connections": len(self.process.connections),
            },
        )

        logger.info(f"Report generated: valid={is_valid}, coverage={coverage_score:.1%}")
        return report

    def _compute_confidence_score(self, issues: list[ValidationIssue]) -> float:
        """
        Compute overall confidence score from issues.

        Args:
            issues: List of validation issues.

        Returns:
            Confidence score (0-1).
        """
        if not issues:
            return 1.0

        # Penalize based on issue severity
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")

        # Scale: errors heavily penalize, warnings moderately, info slightly
        total_elements = max(1, error_count + warning_count + info_count)
        penalty = (error_count * 0.1 + warning_count * 0.02 + info_count * 0.001) / total_elements
        return max(0.0, 1.0 - penalty)

    def _generate_summary(self, issues: list[ValidationIssue], is_valid: bool) -> str:
        """
        Generate a text summary of validation results.

        Args:
            issues: List of validation issues.
            is_valid: Whether the model is valid.

        Returns:
            Summary text.
        """
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        status = "VALID" if is_valid else "INVALID"

        summary = f"Model validation result: {status}\n"
        summary += f"- Errors: {error_count}\n"
        summary += f"- Warnings: {warning_count}\n"

        if error_count > 0:
            summary += "\nCritical errors must be fixed before use."

        return summary

    def export_to_dict(self, report: ValidationReport) -> dict[str, Any]:
        """
        Export report to dictionary.

        Args:
            report: The validation report.

        Returns:
            Dictionary representation.
        """
        return {
            "id": report.id,
            "schema_name": report.schema_name,
            "validated_at": str(report.validated_at),
            "model_id": report.model_id,
            "is_valid": report.is_valid,
            "coverage_score": report.coverage_score,
            "confidence_score": report.confidence_score,
            "summary": report.summary,
            "issues": [
                {
                    "id": i.id,
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "affected_ids": i.affected_ids,
                    "recommendation": i.recommendation,
                }
                for i in report.issues
            ],
            "details": report.details,
        }

    def export_to_json_string(self, report: ValidationReport) -> str:
        """
        Export report to JSON string.

        Args:
            report: The validation report.

        Returns:
            JSON string.
        """
        import json
        data = self.export_to_dict(report)
        return json.dumps(data, indent=2, default=str)
