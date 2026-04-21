"""Tests for cogant.validate.report — ValidationReport and ReportGenerator helpers."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from cogant.validate._mixin import ValidationIssue
from cogant.validate.report import ReportGenerator, ValidationReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_report(
    issues: list[ValidationIssue] | None = None,
    is_valid: bool = True,
    coverage_score: float = 0.9,
    confidence_score: float = 0.95,
) -> ValidationReport:
    return ValidationReport(
        id="rep_test",
        schema_name="test_schema",
        validated_at=datetime(2026, 1, 1, 12, 0, 0),
        model_id="model_001",
        issues=issues or [],
        is_valid=is_valid,
        coverage_score=coverage_score,
        confidence_score=confidence_score,
        summary="Test summary",
        details={"graph_nodes": 3, "graph_edges": 2},
    )


def _make_issue(
    severity: str = "error", category: str = "schema", msg: str = "bad"
) -> ValidationIssue:
    return ValidationIssue(
        id="i0", severity=severity, category=category, message=msg, affected_ids=["node_1"]
    )


# ---------------------------------------------------------------------------
# ValidationReport dataclass
# ---------------------------------------------------------------------------


def test_validation_report_fields() -> None:
    report = _make_report()
    assert report.id == "rep_test"
    assert report.schema_name == "test_schema"
    assert report.model_id == "model_001"
    assert report.is_valid is True
    assert report.coverage_score == pytest.approx(0.9)
    assert report.confidence_score == pytest.approx(0.95)
    assert report.details["graph_nodes"] == 3


def test_validation_report_default_details() -> None:
    report = ValidationReport(
        id="r",
        schema_name="s",
        validated_at=datetime.now(),
        model_id="m",
        issues=[],
        is_valid=True,
        coverage_score=1.0,
        confidence_score=1.0,
        summary="ok",
    )
    assert report.details == {}


def test_validation_report_issues_list() -> None:
    issues = [_make_issue("error"), _make_issue("warning", msg="mild")]
    report = _make_report(issues=issues)
    assert len(report.issues) == 2
    assert report.issues[0].severity == "error"


# ---------------------------------------------------------------------------
# ReportGenerator._compute_confidence_score
# ---------------------------------------------------------------------------


def _make_generator() -> ReportGenerator:
    """Return a ReportGenerator built from minimal real empty objects."""
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.process.extractor import ProcessExtractor
    from cogant.statespace.compiler import StateSpaceCompiler

    graph = ProgramGraphBuilder("test://repo").finalize()
    state_space = StateSpaceCompiler(graph, "test").compile({})
    process = ProcessExtractor(graph, "test").extract()
    return ReportGenerator(graph, state_space, process, "test_schema")


def test_confidence_score_no_issues() -> None:
    gen = _make_generator()
    score = gen._compute_confidence_score([])
    assert score == pytest.approx(1.0)


def test_confidence_score_decreases_with_errors() -> None:
    gen = _make_generator()
    issues = [_make_issue("error")] * 5
    score = gen._compute_confidence_score(issues)
    assert 0.0 <= score < 1.0


def test_confidence_score_errors_penalize_more_than_warnings() -> None:
    gen = _make_generator()
    score_error = gen._compute_confidence_score([_make_issue("error")])
    score_warning = gen._compute_confidence_score([_make_issue("warning")])
    assert score_error < score_warning


def test_confidence_score_bounded() -> None:
    gen = _make_generator()
    many_errors = [_make_issue("error")] * 100
    score = gen._compute_confidence_score(many_errors)
    assert score >= 0.0


# ---------------------------------------------------------------------------
# ReportGenerator._generate_summary
# ---------------------------------------------------------------------------


def test_generate_summary_valid() -> None:
    gen = _make_generator()
    summary = gen._generate_summary([], is_valid=True)
    assert "VALID" in summary
    assert "INVALID" not in summary


def test_generate_summary_invalid() -> None:
    gen = _make_generator()
    issues = [_make_issue("error")]
    summary = gen._generate_summary(issues, is_valid=False)
    assert "INVALID" in summary
    assert "Errors: 1" in summary


def test_generate_summary_counts_warnings() -> None:
    gen = _make_generator()
    issues = [_make_issue("warning"), _make_issue("warning")]
    summary = gen._generate_summary(issues, is_valid=True)
    assert "Warnings: 2" in summary


def test_generate_summary_critical_message_on_errors() -> None:
    gen = _make_generator()
    issues = [_make_issue("error")]
    summary = gen._generate_summary(issues, is_valid=False)
    assert "Critical" in summary or "error" in summary.lower()


# ---------------------------------------------------------------------------
# ReportGenerator.export_to_dict
# ---------------------------------------------------------------------------


def test_export_to_dict_required_keys() -> None:
    gen = _make_generator()
    report = _make_report()
    d = gen.export_to_dict(report)
    required = {
        "id",
        "schema_name",
        "model_id",
        "is_valid",
        "coverage_score",
        "confidence_score",
        "summary",
        "issues",
        "details",
        "validated_at",
    }
    assert required <= d.keys()


def test_export_to_dict_issues_serialized() -> None:
    gen = _make_generator()
    issues = [_make_issue("error", "schema", "broken field")]
    report = _make_report(issues=issues, is_valid=False)
    d = gen.export_to_dict(report)
    assert len(d["issues"]) == 1
    assert d["issues"][0]["severity"] == "error"
    assert d["issues"][0]["message"] == "broken field"
    assert d["is_valid"] is False


def test_export_to_dict_details_preserved() -> None:
    gen = _make_generator()
    report = _make_report()
    d = gen.export_to_dict(report)
    assert d["details"]["graph_nodes"] == 3
    assert d["details"]["graph_edges"] == 2


# ---------------------------------------------------------------------------
# ReportGenerator.export_to_json_string
# ---------------------------------------------------------------------------


def test_export_to_json_string_valid_json() -> None:
    gen = _make_generator()
    report = _make_report()
    json_str = gen.export_to_json_string(report)
    parsed = json.loads(json_str)
    assert parsed["id"] == "rep_test"
    assert parsed["is_valid"] is True


def test_export_to_json_string_round_trips_issues() -> None:
    gen = _make_generator()
    report = _make_report(issues=[_make_issue("warning", msg="check this")])
    parsed = json.loads(gen.export_to_json_string(report))
    assert parsed["issues"][0]["severity"] == "warning"
    assert parsed["issues"][0]["message"] == "check this"
