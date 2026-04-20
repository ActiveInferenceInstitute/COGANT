"""Shared issue type and mixin for cogant.validate validator classes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationIssue:
    """A validation issue found in the model."""

    id: str
    severity: str  # "error", "warning", "info"
    category: str  # "schema", "integrity", "provenance", "coverage"
    message: str
    affected_ids: list[str]
    recommendation: str | None = None


class _ValidatorMixin:
    """Shared issue-collection and filtering logic for validator classes."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def _add_issue(
        self,
        severity: str,
        category: str,
        message: str,
        affected_ids: list[str],
    ) -> None:
        self.issues.append(ValidationIssue(
            id=f"issue_{len(self.issues)}",
            severity=severity,
            category=category,
            message=message,
            affected_ids=affected_ids,
        ))

    def get_issues(self) -> list[ValidationIssue]:
        return self.issues

    def get_errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    def get_warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def is_valid(self) -> bool:
        return all(i.severity != "error" for i in self.issues)
