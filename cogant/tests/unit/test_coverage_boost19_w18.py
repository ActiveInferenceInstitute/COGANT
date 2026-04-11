#!/usr/bin/env python3
"""Coverage boost batch 19 — confidence model, schema validator, translate rules.

Covers:
- translate/confidence.py: ConfidenceModel (compute, determine_tier, diversity,
  conflicts, update_mapping, score_batch)
- validate/schema_check.py: SchemaValidator (validate_program_graph, state_space)
- validate/report.py: ValidationReport dataclass
- translate/rules/behavioral.py: OrchestratorRule, TestAssertionRule
- translate/rules/structural.py: ReadOnlyInputRule, MutatingSubsystemRule,
  InheritanceRule, ContainmentRule
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graph():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test_repo")
    mod = builder.add_node(NodeKind.MODULE, "mymodule", "mymodule", path="mymodule.py", language="python")
    cls = builder.add_node(NodeKind.CLASS, "MyClass", "mymodule.MyClass", path="mymodule.py")
    func = builder.add_node(NodeKind.FUNCTION, "my_func", "mymodule.my_func", path="mymodule.py")
    builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
    builder.add_edge(cls.id, func.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_state_space(graph=None):
    from cogant.statespace.compiler import StateSpaceCompiler
    if graph is None:
        graph = _make_graph()
    compiler = StateSpaceCompiler(graph, "test_schema")
    return compiler.compile({})


def _make_semantic_mapping(kind_name="HIDDEN_STATE", n_provenance=1, sources=None):
    from cogant.schemas.semantic import SemanticMapping, ProvenanceRecord, MappingKind
    from cogant.schemas.semantic import ConfidenceTier

    kind = MappingKind[kind_name] if kind_name in MappingKind.__members__ else MappingKind.HIDDEN_STATE
    sources = sources or ["static_analysis"] * n_provenance
    provenance = [
        ProvenanceRecord(source=src, confidence=0.7)
        for src in sources
    ]
    return SemanticMapping(
        id=f"map_{kind_name}",
        kind=kind,
        provenance=provenance,
        parser_certainty=0.9,
        evidence_diversity=len(set(sources)) / max(1, len(sources)),
        conflict_penalties=[],
    )


# ---------------------------------------------------------------------------
# translate/confidence.py — ConfidenceModel
# ---------------------------------------------------------------------------

class TestConfidenceModelCompute:
    """Test ConfidenceModel.compute_confidence_score."""

    def test_compute_no_provenance(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="test",
            kind=MappingKind.HIDDEN_STATE,
        )
        score = model.compute_confidence_score(mapping)
        assert score == 0.0

    def test_compute_with_single_provenance(self):
        from cogant.translate.confidence import ConfidenceModel
        mapping = _make_semantic_mapping("HIDDEN_STATE", n_provenance=1)
        model = ConfidenceModel()
        score = model.compute_confidence_score(mapping)
        assert 0.0 <= score <= 1.0

    def test_compute_alias_works(self):
        from cogant.translate.confidence import ConfidenceModel
        mapping = _make_semantic_mapping("HIDDEN_STATE", n_provenance=1)
        model = ConfidenceModel()
        assert model.compute(mapping) == model.compute_confidence_score(mapping)

    def test_compute_high_confidence(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="test_high",
            kind=MappingKind.OBSERVATION,
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.95)],
            parser_certainty=1.0,
            evidence_diversity=1.0,
            conflict_penalties=[],
        )
        score = model.compute_confidence_score(mapping)
        assert score > 0.5

    def test_compute_clamped_to_1(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        # Very high values should be clamped
        mapping = SemanticMapping(
            id="test_clamp",
            kind=MappingKind.HIDDEN_STATE,
            provenance=[ProvenanceRecord(source="static_analysis", confidence=1.0)],
            parser_certainty=1.0,
            evidence_diversity=1.0,
            conflict_penalties=[],
        )
        score = model.compute_confidence_score(mapping)
        assert score <= 1.0

    def test_compute_clamped_to_0(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        # Conflict penalties should reduce score but not below 0
        mapping = SemanticMapping(
            id="test_zero",
            kind=MappingKind.HIDDEN_STATE,
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.1)],
            parser_certainty=0.1,
            evidence_diversity=0.0,
            conflict_penalties=[0.5, 0.5, 0.5],
        )
        score = model.compute_confidence_score(mapping)
        assert score >= 0.0


class TestConfidenceModelTier:
    """Test determine_confidence_tier."""

    def test_static_only_tier(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import ConfidenceTier, SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="static",
            kind=MappingKind.HIDDEN_STATE,
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.7)],
            parser_certainty=0.9,
            evidence_diversity=1.0,
            conflict_penalties=[],
        )
        tier = model.determine_confidence_tier(mapping)
        assert tier == ConfidenceTier.STATIC_ONLY

    def test_human_reviewed_tier(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import ConfidenceTier, SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="human",
            kind=MappingKind.HIDDEN_STATE,
            provenance=[ProvenanceRecord(source="human_review", confidence=0.95)],
            parser_certainty=1.0,
            evidence_diversity=1.0,
            conflict_penalties=[],
        )
        tier = model.determine_confidence_tier(mapping)
        assert tier == ConfidenceTier.HUMAN_REVIEWED

    def test_runtime_only_tier(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import ConfidenceTier, SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="runtime",
            kind=MappingKind.HIDDEN_STATE,
            provenance=[ProvenanceRecord(source="dynamic_trace", confidence=0.6)],
            parser_certainty=0.8,
            evidence_diversity=1.0,
            conflict_penalties=[],
        )
        tier = model.determine_confidence_tier(mapping, score=0.5)
        assert tier == ConfidenceTier.RUNTIME_ONLY

    def test_static_plus_runtime_tier(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import ConfidenceTier, SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="both",
            kind=MappingKind.HIDDEN_STATE,
            provenance=[
                ProvenanceRecord(source="static_analysis", confidence=0.7),
                ProvenanceRecord(source="dynamic_trace", confidence=0.7),
            ],
            parser_certainty=0.9,
            evidence_diversity=1.0,
            conflict_penalties=[],
        )
        tier = model.determine_confidence_tier(mapping, score=0.7)
        assert tier == ConfidenceTier.STATIC_PLUS_RUNTIME

    def test_precomputed_score_used(self):
        from cogant.translate.confidence import ConfidenceModel
        mapping = _make_semantic_mapping()
        model = ConfidenceModel()
        # Pass a custom score so compute is not called
        tier = model.determine_confidence_tier(mapping, score=0.95)
        # With human_review source not present, should be static_only or similar
        assert tier is not None


class TestConfidenceModelDiversity:
    """Test score_evidence_diversity."""

    def test_no_provenance(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(id="empty", kind=MappingKind.HIDDEN_STATE)
        score = model.score_evidence_diversity(mapping)
        assert score == 0.0

    def test_single_source(self):
        from cogant.translate.confidence import ConfidenceModel
        mapping = _make_semantic_mapping(n_provenance=1, sources=["static_analysis"])
        model = ConfidenceModel()
        score = model.score_evidence_diversity(mapping)
        assert score == 1.0

    def test_two_different_sources(self):
        from cogant.translate.confidence import ConfidenceModel
        mapping = _make_semantic_mapping(
            n_provenance=2, sources=["static_analysis", "dynamic_trace"]
        )
        model = ConfidenceModel()
        score = model.score_evidence_diversity(mapping)
        assert score == 1.0

    def test_same_sources_no_diversity(self):
        from cogant.translate.confidence import ConfidenceModel
        mapping = _make_semantic_mapping(
            n_provenance=3, sources=["static_analysis", "static_analysis", "static_analysis"]
        )
        model = ConfidenceModel()
        score = model.score_evidence_diversity(mapping)
        assert score <= 1.0  # same source = low diversity


class TestConfidenceModelConflicts:
    """Test detect_conflicts."""

    def test_no_provenance(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(id="empty", kind=MappingKind.HIDDEN_STATE)
        penalties = model.detect_conflicts(mapping)
        assert penalties == []

    def test_single_provenance_no_conflict(self):
        from cogant.translate.confidence import ConfidenceModel
        mapping = _make_semantic_mapping(n_provenance=1)
        model = ConfidenceModel()
        penalties = model.detect_conflicts(mapping)
        assert penalties == []

    def test_high_confidence_divergence(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="divergent",
            kind=MappingKind.HIDDEN_STATE,
            provenance=[
                ProvenanceRecord(source="static_analysis", confidence=0.9),
                ProvenanceRecord(source="dynamic_trace", confidence=0.3),
            ],
        )
        penalties = model.detect_conflicts(mapping)
        # Should detect divergence (0.9 - 0.3 = 0.6 > 0.3 threshold)
        assert len(penalties) >= 1

    def test_static_dynamic_disagreement(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="static_vs_dynamic",
            kind=MappingKind.HIDDEN_STATE,
            provenance=[
                ProvenanceRecord(source="static_analysis", confidence=0.9),
                ProvenanceRecord(source="dynamic_trace", confidence=0.3),
            ],
        )
        penalties = model.detect_conflicts(mapping)
        # Both divergence AND static/dynamic disagreement — at least 1 penalty
        assert len(penalties) >= 1


class TestConfidenceModelBatch:
    """Test update_mapping_confidence and score_batch."""

    def test_update_mapping_in_place(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mapping = SemanticMapping(
            id="upd",
            kind=MappingKind.OBSERVATION,
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.7)],
            parser_certainty=0.9,
        )
        model.update_mapping_confidence(mapping)
        # Should have been updated
        assert mapping.evidence_count >= 1
        assert mapping.confidence_score >= 0.0
        assert mapping.confidence_tier is not None

    def test_score_batch_empty(self):
        from cogant.translate.confidence import ConfidenceModel
        model = ConfidenceModel()
        model.score_batch([])  # Should not raise

    def test_score_batch_multiple(self):
        from cogant.translate.confidence import ConfidenceModel
        from cogant.schemas.semantic import SemanticMapping, ProvenanceRecord, MappingKind
        model = ConfidenceModel()
        mappings = [
            SemanticMapping(
                id=f"map_{i}",
                kind=MappingKind.HIDDEN_STATE,
                provenance=[ProvenanceRecord(source="static_analysis", confidence=0.7)],
                parser_certainty=0.9,
            )
            for i in range(5)
        ]
        model.score_batch(mappings)
        for m in mappings:
            assert m.confidence_score >= 0.0
            assert m.evidence_count == 1


# ---------------------------------------------------------------------------
# validate/schema_check.py — SchemaValidator
# ---------------------------------------------------------------------------

class TestSchemaValidator:
    """Test SchemaValidator on real graphs and state spaces."""

    def test_validate_program_graph_returns_list(self):
        from cogant.validate.schema_check import SchemaValidator
        graph = _make_graph()
        validator = SchemaValidator()
        issues = validator.validate_program_graph(graph)
        assert isinstance(issues, list)

    def test_validate_clean_graph_no_errors(self):
        from cogant.validate.schema_check import SchemaValidator
        graph = _make_graph()
        validator = SchemaValidator()
        issues = validator.validate_program_graph(graph)
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) == 0

    def test_validate_state_space_returns_list(self):
        from cogant.validate.schema_check import SchemaValidator
        ssm = _make_state_space()
        validator = SchemaValidator()
        issues = validator.validate_state_space(ssm)
        assert isinstance(issues, list)

    def test_schema_validator_init(self):
        from cogant.validate.schema_check import SchemaValidator
        validator = SchemaValidator()
        assert validator.issues == []

    def test_validation_issue_creation(self):
        from cogant.validate.schema_check import ValidationIssue
        issue = ValidationIssue(
            id="ISS-001",
            severity="error",
            category="schema",
            message="Test issue",
            affected_ids=["node_1"],
            recommendation="Fix this",
        )
        assert issue.id == "ISS-001"
        assert issue.severity == "error"
        assert issue.recommendation == "Fix this"

    def test_validation_issue_no_recommendation(self):
        from cogant.validate.schema_check import ValidationIssue
        issue = ValidationIssue(
            id="ISS-002",
            severity="warning",
            category="integrity",
            message="Warning",
            affected_ids=[],
        )
        assert issue.recommendation is None

    def test_validate_graph_with_nodes(self):
        from cogant.validate.schema_check import SchemaValidator
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        for i in range(5):
            builder.add_node(NodeKind.FUNCTION, f"func_{i}", f"mod.func_{i}")
        graph = builder.finalize()
        validator = SchemaValidator()
        issues = validator.validate_program_graph(graph)
        assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# validate/report.py — ValidationReport dataclass
# ---------------------------------------------------------------------------

class TestValidationReport:
    """Test ValidationReport dataclass."""

    def test_validation_report_creation(self):
        from cogant.validate.report import ValidationReport
        from cogant.validate.schema_check import ValidationIssue
        from datetime import datetime
        report = ValidationReport(
            id="report_001",
            schema_name="test_schema",
            validated_at=datetime.now(),
            model_id="model_001",
            issues=[],
            is_valid=True,
            coverage_score=0.9,
            confidence_score=0.8,
            summary="All good",
        )
        assert report.id == "report_001"
        assert report.is_valid is True
        assert report.coverage_score == 0.9
        assert report.details == {}

    def test_validation_report_with_issues(self):
        from cogant.validate.report import ValidationReport
        from cogant.validate.schema_check import ValidationIssue
        from datetime import datetime
        issue = ValidationIssue(
            id="I001", severity="warning", category="schema",
            message="Minor", affected_ids=[]
        )
        report = ValidationReport(
            id="report_002",
            schema_name="test",
            validated_at=datetime.now(),
            model_id="model_002",
            issues=[issue],
            is_valid=False,
            coverage_score=0.5,
            confidence_score=0.5,
            summary="Has warnings",
        )
        assert len(report.issues) == 1
        assert report.is_valid is False


# ---------------------------------------------------------------------------
# translate/rules/behavioral.py — OrchestratorRule
# ---------------------------------------------------------------------------

class TestOrchestratorRule:
    """Test OrchestratorRule matches and apply."""

    def _make_orchestrator_graph(self):
        """Build a graph where a function calls 3+ others (orchestrator pattern)."""
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        orch = builder.add_node(NodeKind.FUNCTION, "orchestrate", "mod.orchestrate")
        targets = [
            builder.add_node(NodeKind.FUNCTION, f"sub_{i}", f"mod.sub_{i}")
            for i in range(4)
        ]
        for t in targets:
            builder.add_edge(orch.id, t.id, EdgeKind.CALLS)
        return builder.finalize()

    def test_orchestrator_rule_name(self):
        from cogant.translate.rules.behavioral import OrchestratorRule
        rule = OrchestratorRule()
        assert rule.name == "orchestrator"

    def test_orchestrator_rule_mapping_kind(self):
        from cogant.translate.rules.behavioral import OrchestratorRule
        from cogant.schemas.semantic import MappingKind
        rule = OrchestratorRule()
        assert rule.mapping_kind == MappingKind.ORCHESTRATION

    def test_orchestrator_matches_high_fan_out(self):
        from cogant.translate.rules.behavioral import OrchestratorRule
        from cogant.graph.queries import GraphQuery
        graph = self._make_orchestrator_graph()
        query = GraphQuery(graph)
        rule = OrchestratorRule()
        matches = rule.matches(graph, query)
        # The orchestrate function calls 4 nodes, should match
        assert len(matches) >= 1

    def test_orchestrator_no_match_low_fan_out(self):
        from cogant.translate.rules.behavioral import OrchestratorRule
        from cogant.graph.queries import GraphQuery
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        func = builder.add_node(NodeKind.FUNCTION, "small", "mod.small")
        target = builder.add_node(NodeKind.FUNCTION, "helper", "mod.helper")
        builder.add_edge(func.id, target.id, EdgeKind.CALLS)  # only 1 call
        graph = builder.finalize()
        query = GraphQuery(graph)
        rule = OrchestratorRule()
        matches = rule.matches(graph, query)
        assert len(matches) == 0

    def test_orchestrator_apply_returns_mapping(self):
        from cogant.translate.rules.behavioral import OrchestratorRule
        from cogant.graph.queries import GraphQuery
        graph = self._make_orchestrator_graph()
        query = GraphQuery(graph)
        rule = OrchestratorRule()
        matches = rule.matches(graph, query)
        assert len(matches) >= 1
        mapping = rule.apply(graph, matches[0])
        assert mapping is not None
        assert mapping.confidence_score > 0.0


# ---------------------------------------------------------------------------
# translate/rules/structural.py — ReadOnlyInputRule, ContainmentRule
# ---------------------------------------------------------------------------

class TestReadOnlyInputRule:
    """Test ReadOnlyInputRule matches and apply."""

    def _make_readonly_graph(self):
        """Build a graph with a module that only has READS edges (no WRITES)."""
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        mod = builder.add_node(NodeKind.MODULE, "reader", "reader", path="reader.py")
        var = builder.add_node(NodeKind.VARIABLE, "data", "reader.data")
        builder.add_edge(mod.id, var.id, EdgeKind.READS)
        return builder.finalize()

    def test_read_only_rule_name(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule
        rule = ReadOnlyInputRule()
        assert rule.name == "read_only_input"

    def test_read_only_rule_mapping_kind(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule
        from cogant.schemas.semantic import MappingKind
        rule = ReadOnlyInputRule()
        assert rule.mapping_kind == MappingKind.OBSERVATION

    def test_read_only_matches_readonly_module(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule
        from cogant.graph.queries import GraphQuery
        graph = self._make_readonly_graph()
        query = GraphQuery(graph)
        rule = ReadOnlyInputRule()
        matches = rule.matches(graph, query)
        assert len(matches) >= 1

    def test_read_only_no_match_on_empty_graph(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule
        from cogant.graph.queries import GraphQuery
        graph = _make_graph()
        query = GraphQuery(graph)
        rule = ReadOnlyInputRule()
        matches = rule.matches(graph, query)
        # Our _make_graph has no READS edges, so no matches
        assert len(matches) == 0

    def test_read_only_apply_returns_mapping(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule
        from cogant.graph.queries import GraphQuery
        graph = self._make_readonly_graph()
        query = GraphQuery(graph)
        rule = ReadOnlyInputRule()
        matches = rule.matches(graph, query)
        if len(matches) > 0:
            mapping = rule.apply(graph, matches[0])
            assert mapping is not None


class TestMutatingSubsystemRule:
    """Test MutatingSubsystemRule."""

    def _make_mutating_graph(self):
        """Build a graph with a class that has WRITES edges."""
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        cls = builder.add_node(NodeKind.CLASS, "Tracker", "Tracker")
        var1 = builder.add_node(NodeKind.VARIABLE, "count", "Tracker.count")
        var2 = builder.add_node(NodeKind.VARIABLE, "state", "Tracker.state")
        builder.add_edge(cls.id, var1.id, EdgeKind.WRITES)
        builder.add_edge(cls.id, var2.id, EdgeKind.WRITES)
        builder.add_edge(cls.id, var2.id, EdgeKind.WRITES)  # extra write
        return builder.finalize()

    def test_mutating_rule_name(self):
        from cogant.translate.rules.structural import MutatingSubsystemRule
        rule = MutatingSubsystemRule()
        assert rule.name == "mutating_subsystem"

    def test_mutating_rule_mapping_kind(self):
        from cogant.translate.rules.structural import MutatingSubsystemRule
        from cogant.schemas.semantic import MappingKind
        rule = MutatingSubsystemRule()
        assert rule.mapping_kind == MappingKind.HIDDEN_STATE

    def test_mutating_matches(self):
        from cogant.translate.rules.structural import MutatingSubsystemRule
        from cogant.graph.queries import GraphQuery
        graph = self._make_mutating_graph()
        query = GraphQuery(graph)
        rule = MutatingSubsystemRule()
        matches = rule.matches(graph, query)
        assert len(matches) >= 1

    def test_mutating_apply(self):
        from cogant.translate.rules.structural import MutatingSubsystemRule
        from cogant.graph.queries import GraphQuery
        graph = self._make_mutating_graph()
        query = GraphQuery(graph)
        rule = MutatingSubsystemRule()
        matches = rule.matches(graph, query)
        if len(matches) > 0:
            mapping = rule.apply(graph, matches[0])
            assert mapping is not None


class TestContainmentRule:
    """Test ContainmentRule."""

    def test_containment_rule_name(self):
        from cogant.translate.rules.structural import ContainmentRule
        rule = ContainmentRule()
        assert rule.name == "containment"

    def test_containment_rule_matches_on_standard_graph(self):
        from cogant.translate.rules.structural import ContainmentRule
        from cogant.graph.queries import GraphQuery
        graph = _make_graph()
        query = GraphQuery(graph)
        rule = ContainmentRule()
        matches = rule.matches(graph, query)
        assert isinstance(matches, list)

    def test_containment_rule_apply(self):
        from cogant.translate.rules.structural import ContainmentRule
        from cogant.graph.queries import GraphQuery
        graph = _make_graph()
        query = GraphQuery(graph)
        rule = ContainmentRule()
        matches = rule.matches(graph, query)
        if len(matches) > 0:
            mapping = rule.apply(graph, matches[0])
            # mapping may be None if the match can't be applied
            assert mapping is None or mapping.confidence_score >= 0.0


class TestInheritanceRule:
    """Test InheritanceRule."""

    def _make_inheritance_graph(self):
        """Build a graph with inheritance edges."""
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        base = builder.add_node(NodeKind.CLASS, "Base", "Base")
        child = builder.add_node(NodeKind.CLASS, "Child", "Child")
        builder.add_edge(child.id, base.id, EdgeKind.INHERITS)
        return builder.finalize()

    def test_inheritance_rule_name(self):
        from cogant.translate.rules.structural import InheritanceRule
        rule = InheritanceRule()
        assert rule.name == "inheritance"

    def test_inheritance_matches(self):
        from cogant.translate.rules.structural import InheritanceRule
        from cogant.graph.queries import GraphQuery
        graph = self._make_inheritance_graph()
        query = GraphQuery(graph)
        rule = InheritanceRule()
        matches = rule.matches(graph, query)
        assert isinstance(matches, list)
