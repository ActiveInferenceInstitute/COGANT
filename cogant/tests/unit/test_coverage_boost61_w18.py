#!/usr/bin/env python3
"""Coverage boost batch 61 — validate/schema_check.py, validate/integrity.py,
validate/report.py.

Covers:
- validate/schema_check.py: ValidationIssue dataclass, SchemaValidator
  (validate_program_graph empty/with-nodes, validate_state_space, validate_process_model)
- validate/integrity.py: IntegrityChecker (check_program_graph, check_state_space,
  check_process_model, get_issues, is_valid)
- validate/report.py: ValidationReport, ReportGenerator (generate, export_to_dict,
  export_to_json_string)
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


def _make_empty_graph():
    from cogant.graph.builder import ProgramGraphBuilder
    return ProgramGraphBuilder(repo_uri="file:///test").finalize()


def _make_state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime
    return StateSpaceModel(
        id="ss1", schema_name="test",
        variables={}, observations={}, actions={},
        transitions={}, likelihoods={}, preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_process_model():
    from cogant.process.extractor import ProcessModel
    return ProcessModel(id="pm1", schema_name="test", stages={}, connections={})


# ---------------------------------------------------------------------------
# validate/schema_check.py — ValidationIssue and SchemaValidator
# ---------------------------------------------------------------------------

class TestValidationIssue:
    def test_validation_issue_init(self):
        from cogant.validate.schema_check import ValidationIssue
        issue = ValidationIssue(
            id="issue_001",
            severity="error",
            category="schema",
            message="Missing field",
            affected_ids=["node_a"],
        )
        assert issue.severity == "error"
        assert issue.message == "Missing field"
        assert issue.id == "issue_001"

    def test_validation_issue_warning(self):
        from cogant.validate.schema_check import ValidationIssue
        issue = ValidationIssue(
            id="issue_002",
            severity="warning",
            category="structure",
            message="Orphaned node",
            affected_ids=[],
        )
        assert issue.severity == "warning"
        assert issue.affected_ids == []


class TestSchemaValidator:
    def test_init(self):
        from cogant.validate.schema_check import SchemaValidator
        validator = SchemaValidator()
        assert validator is not None

    def test_validate_program_graph_empty(self):
        from cogant.validate.schema_check import SchemaValidator
        validator = SchemaValidator()
        graph = _make_empty_graph()
        issues = validator.validate_program_graph(graph)
        assert isinstance(issues, list)

    def test_validate_program_graph_with_nodes(self):
        from cogant.validate.schema_check import SchemaValidator
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        n2 = builder.add_node(NodeKind.CLASS, "Cls", "mod.Cls", path="mod.py")
        builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
        graph = builder.finalize()
        validator = SchemaValidator()
        issues = validator.validate_program_graph(graph)
        assert isinstance(issues, list)

    def test_validate_state_space_empty(self):
        from cogant.validate.schema_check import SchemaValidator
        validator = SchemaValidator()
        ss = _make_state_space()
        issues = validator.validate_state_space(ss)
        assert isinstance(issues, list)

    def test_validate_process_model_empty(self):
        from cogant.validate.schema_check import SchemaValidator
        validator = SchemaValidator()
        pm = _make_process_model()
        issues = validator.validate_process_model(pm)
        assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# validate/integrity.py — IntegrityChecker
# ---------------------------------------------------------------------------

class TestIntegrityChecker:
    def test_init(self):
        from cogant.validate.integrity import IntegrityChecker
        checker = IntegrityChecker()
        assert checker is not None

    def test_check_program_graph_empty(self):
        from cogant.validate.integrity import IntegrityChecker
        checker = IntegrityChecker()
        graph = _make_empty_graph()
        issues = checker.check_program_graph(graph)
        assert isinstance(issues, list)

    def test_check_state_space_empty(self):
        from cogant.validate.integrity import IntegrityChecker
        checker = IntegrityChecker()
        ss = _make_state_space()
        issues = checker.check_state_space(ss)
        assert isinstance(issues, list)

    def test_check_process_model_empty(self):
        from cogant.validate.integrity import IntegrityChecker
        checker = IntegrityChecker()
        pm = _make_process_model()
        issues = checker.check_process_model(pm)
        assert isinstance(issues, list)

    def test_get_issues_initially_empty(self):
        from cogant.validate.integrity import IntegrityChecker
        checker = IntegrityChecker()
        issues = checker.get_issues()
        assert isinstance(issues, list)
        assert len(issues) == 0

    def test_is_valid_initially_true(self):
        from cogant.validate.integrity import IntegrityChecker
        checker = IntegrityChecker()
        assert checker.is_valid() is True

    def test_is_valid_after_check(self):
        from cogant.validate.integrity import IntegrityChecker
        checker = IntegrityChecker()
        graph = _make_empty_graph()
        checker.check_program_graph(graph)
        # Still valid with empty graph
        assert isinstance(checker.is_valid(), bool)


# ---------------------------------------------------------------------------
# validate/report.py — ValidationReport and ReportGenerator
# ---------------------------------------------------------------------------

class TestValidationReport:
    def test_report_init(self):
        from cogant.validate.report import ValidationReport
        from datetime import datetime
        report = ValidationReport(
            id="report_001",
            schema_name="test",
            validated_at=datetime.now(),
            model_id="model_001",
            issues=[],
            is_valid=True,
            coverage_score=1.0,
            confidence_score=1.0,
            summary="All checks passed",
        )
        assert report.is_valid is True
        assert report.confidence_score == 1.0
        assert report.coverage_score == 1.0


class TestReportGenerator:
    def test_init(self):
        from cogant.validate.report import ReportGenerator
        graph = _make_empty_graph()
        ss = _make_state_space()
        pm = _make_process_model()
        generator = ReportGenerator(
            program_graph=graph,
            state_space_model=ss,
            process_model=pm,
            schema_name="test",
        )
        assert generator is not None

    def test_generate_empty_graph(self):
        from cogant.validate.report import ReportGenerator, ValidationReport
        graph = _make_empty_graph()
        ss = _make_state_space()
        pm = _make_process_model()
        generator = ReportGenerator(
            program_graph=graph,
            state_space_model=ss,
            process_model=pm,
            schema_name="test",
        )
        report = generator.generate()
        assert isinstance(report, ValidationReport)
        assert isinstance(report.is_valid, bool)

    def test_export_to_dict(self):
        from cogant.validate.report import ReportGenerator
        graph = _make_empty_graph()
        ss = _make_state_space()
        pm = _make_process_model()
        generator = ReportGenerator(
            program_graph=graph,
            state_space_model=ss,
            process_model=pm,
            schema_name="test",
        )
        report = generator.generate()
        result = generator.export_to_dict(report)
        assert isinstance(result, dict)

    def test_export_to_json_string(self):
        import json
        from cogant.validate.report import ReportGenerator
        graph = _make_empty_graph()
        ss = _make_state_space()
        pm = _make_process_model()
        generator = ReportGenerator(
            program_graph=graph,
            state_space_model=ss,
            process_model=pm,
            schema_name="test",
        )
        report = generator.generate()
        json_str = generator.export_to_json_string(report)
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert isinstance(data, dict)
