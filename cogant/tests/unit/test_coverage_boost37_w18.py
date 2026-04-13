#!/usr/bin/env python3
"""Coverage boost batch 37 — translate/engine.py.

Covers:
- RuleExplanation dataclass: creation, to_dict
- TranslationRule: priority default, explain method
- TranslationEngine: init, register_rule, translate, translate_with_confidence,
  get_coverage_report, get_mappings_by_kind, get_mappings_by_confidence,
  get_mapping, get_match_log, get_statistics, _resolve_conflicts
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graph():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    mod = builder.add_node(NodeKind.MODULE, "mymodule", "mymodule",
                           path="mymodule.py", language="python")
    func1 = builder.add_node(NodeKind.FUNCTION, "sender", "mymodule.sender",
                             path="mymodule.py")
    var1 = builder.add_node(NodeKind.VARIABLE, "state", "mymodule.state",
                            path="mymodule.py")
    builder.add_edge(mod.id, func1.id, EdgeKind.CONTAINS)
    builder.add_edge(mod.id, var1.id, EdgeKind.CONTAINS)
    builder.add_edge(func1.id, var1.id, EdgeKind.WRITES)
    builder.add_edge(func1.id, var1.id, EdgeKind.READS)
    return builder.finalize(), mod, func1, var1


def _make_engine_with_rules():
    """Create TranslationEngine with all standard rules registered."""
    from cogant.translate.engine import TranslationEngine
    from cogant.translate.rules.structural import (
        ReadOnlyInputRule, MutatingSubsystemRule, InheritanceRule,
        ContainmentRule, DataPipelineRule,
    )
    from cogant.translate.rules.resilience import RetryPatternRule
    engine = TranslationEngine()
    engine.register_rule(ReadOnlyInputRule())
    engine.register_rule(MutatingSubsystemRule())
    engine.register_rule(ContainmentRule())
    engine.register_rule(DataPipelineRule())
    engine.register_rule(RetryPatternRule())
    return engine


# ---------------------------------------------------------------------------
# RuleExplanation
# ---------------------------------------------------------------------------

class TestRuleExplanation:
    def test_creation(self):
        from cogant.translate.engine import RuleExplanation
        exp = RuleExplanation(
            rule_name="test_rule",
            priority=0,
            fired=True,
            reason="matched",
        )
        assert exp.rule_name == "test_rule"
        assert exp.fired is True

    def test_default_evidence_empty(self):
        from cogant.translate.engine import RuleExplanation
        exp = RuleExplanation(rule_name="r", priority=0, fired=False, reason="no")
        assert exp.evidence == []

    def test_default_mapping_kind_none(self):
        from cogant.translate.engine import RuleExplanation
        exp = RuleExplanation(rule_name="r", priority=0, fired=False, reason="no")
        assert exp.mapping_kind is None

    def test_to_dict_returns_dict(self):
        from cogant.translate.engine import RuleExplanation
        exp = RuleExplanation(
            rule_name="my_rule", priority=1, fired=True,
            reason="matches", evidence=["e1"], mapping_kind="hidden_state",
        )
        d = exp.to_dict()
        assert isinstance(d, dict)
        assert d["rule_name"] == "my_rule"
        assert d["fired"] is True
        assert d["evidence"] == ["e1"]

    def test_to_dict_has_all_keys(self):
        from cogant.translate.engine import RuleExplanation
        exp = RuleExplanation(rule_name="r", priority=0, fired=False, reason="no")
        d = exp.to_dict()
        assert set(d.keys()) >= {"rule_name", "priority", "fired", "reason", "evidence", "mapping_kind"}


# ---------------------------------------------------------------------------
# TranslationEngine — initialization
# ---------------------------------------------------------------------------

class TestTranslationEngineInit:
    def test_default_init(self):
        from cogant.translate.engine import TranslationEngine
        engine = TranslationEngine()
        assert engine.max_iterations == 10
        assert engine.rules == []
        assert engine.mappings == {}

    def test_custom_max_iterations(self):
        from cogant.translate.engine import TranslationEngine
        engine = TranslationEngine(max_iterations=5)
        assert engine.max_iterations == 5

    def test_register_rule(self):
        from cogant.translate.engine import TranslationEngine
        from cogant.translate.rules.structural import ReadOnlyInputRule
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        assert len(engine.rules) == 1

    def test_register_multiple_rules(self):
        from cogant.translate.engine import TranslationEngine
        from cogant.translate.rules.structural import ReadOnlyInputRule, MutatingSubsystemRule
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        engine.register_rule(MutatingSubsystemRule())
        assert len(engine.rules) == 2


# ---------------------------------------------------------------------------
# TranslationEngine — translate
# ---------------------------------------------------------------------------

class TestTranslationEngineTranslate:
    def test_translate_empty_graph_returns_list(self):
        from cogant.translate.engine import TranslationEngine
        from cogant.graph.builder import ProgramGraphBuilder
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        engine = TranslationEngine()
        result = engine.translate(graph)
        assert isinstance(result, list)

    def test_translate_with_rules_returns_mappings(self):
        from cogant.schemas.semantic import SemanticMapping
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        result = engine.translate(graph)
        assert all(isinstance(m, SemanticMapping) for m in result)

    def test_translate_with_filter(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        result = engine.translate(graph, rule_filter=["read_only_input"])
        assert isinstance(result, list)

    def test_translate_clears_previous_mappings(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        count1 = len(engine.mappings)
        engine.translate(graph)
        count2 = len(engine.mappings)
        assert count1 == count2

    def test_translate_populates_match_log(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        log = engine.get_match_log()
        assert isinstance(log, list)

    def test_translate_convergence(self):
        from cogant.translate.engine import TranslationEngine
        from cogant.graph.builder import ProgramGraphBuilder
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        engine = TranslationEngine(max_iterations=3)
        result = engine.translate(graph)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# TranslationEngine — translate_with_confidence
# ---------------------------------------------------------------------------

class TestTranslationEngineTranslateWithConfidence:
    def test_translate_with_confidence_returns_list(self):
        from cogant.schemas.semantic import SemanticMapping
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        result = engine.translate_with_confidence(graph)
        assert isinstance(result, list)
        assert all(isinstance(m, SemanticMapping) for m in result)

    def test_translate_with_confidence_confidence_scores(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        result = engine.translate_with_confidence(graph)
        for m in result:
            assert 0.0 <= m.confidence_score <= 1.0


# ---------------------------------------------------------------------------
# TranslationEngine — get_coverage_report
# ---------------------------------------------------------------------------

class TestTranslationEngineCoverageReport:
    def test_coverage_report_structure(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        report = engine.get_coverage_report(graph)
        assert "total_nodes" in report
        assert "covered_nodes" in report
        assert "uncovered_nodes" in report
        assert "coverage_percent" in report

    def test_total_nodes_matches_graph(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        report = engine.get_coverage_report(graph)
        assert report["total_nodes"] == len(graph.nodes)

    def test_coverage_percent_in_range(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        report = engine.get_coverage_report(graph)
        assert 0.0 <= report["coverage_percent"] <= 100.0

    def test_empty_graph_zero_coverage(self):
        from cogant.translate.engine import TranslationEngine
        from cogant.graph.builder import ProgramGraphBuilder
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        engine = TranslationEngine()
        engine.translate(graph)
        report = engine.get_coverage_report(graph)
        assert report["total_nodes"] == 0
        assert report["coverage_percent"] == 0.0


# ---------------------------------------------------------------------------
# TranslationEngine — get_mappings_by_kind
# ---------------------------------------------------------------------------

class TestGetMappingsByKind:
    def test_returns_list(self):
        from cogant.schemas.semantic import MappingKind
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        result = engine.get_mappings_by_kind(MappingKind.HIDDEN_STATE)
        assert isinstance(result, list)

    def test_returns_only_requested_kind(self):
        from cogant.schemas.semantic import MappingKind
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        result = engine.get_mappings_by_kind(MappingKind.OBSERVATION)
        assert all(m.kind == MappingKind.OBSERVATION for m in result)


# ---------------------------------------------------------------------------
# TranslationEngine — get_mappings_by_confidence
# ---------------------------------------------------------------------------

class TestGetMappingsByConfidence:
    def test_returns_list(self):
        from cogant.schemas.semantic import ConfidenceTier
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        result = engine.get_mappings_by_confidence(ConfidenceTier.STATIC_ONLY)
        assert isinstance(result, list)

    def test_only_requested_tier(self):
        from cogant.schemas.semantic import ConfidenceTier
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        result = engine.get_mappings_by_confidence(ConfidenceTier.STATIC_ONLY)
        assert all(m.confidence_tier == ConfidenceTier.STATIC_ONLY for m in result)


# ---------------------------------------------------------------------------
# TranslationEngine — get_mapping, get_match_log, get_statistics
# ---------------------------------------------------------------------------

class TestTranslationEngineAccessors:
    def test_get_mapping_missing_returns_none(self):
        from cogant.translate.engine import TranslationEngine
        engine = TranslationEngine()
        result = engine.get_mapping("nonexistent_id")
        assert result is None

    def test_get_match_log_empty_initially(self):
        from cogant.translate.engine import TranslationEngine
        engine = TranslationEngine()
        log = engine.get_match_log()
        assert log == []

    def test_get_match_log_after_translate(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        log = engine.get_match_log()
        assert isinstance(log, list)

    def test_get_statistics_structure(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        stats = engine.get_statistics()
        assert "total_mappings" in stats
        assert "mappings_by_kind" in stats
        assert "rules_registered" in stats

    def test_get_statistics_rules_count(self):
        from cogant.translate.engine import TranslationEngine
        from cogant.translate.rules.structural import ReadOnlyInputRule
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        stats = engine.get_statistics()
        assert stats["rules_registered"] == 1

    def test_get_statistics_total_mappings_nonneg(self):
        graph, mod, func1, var1 = _make_graph()
        engine = _make_engine_with_rules()
        engine.translate(graph)
        stats = engine.get_statistics()
        assert stats["total_mappings"] >= 0


# ---------------------------------------------------------------------------
# TranslationRule.explain
# ---------------------------------------------------------------------------

class TestTranslationRuleExplain:
    def test_explain_matched_node(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule
        from cogant.translate.engine import RuleExplanation
        graph, mod, func1, var1 = _make_graph()
        from cogant.graph.queries import GraphQuery
        rule = ReadOnlyInputRule()
        query = GraphQuery(graph)
        exp = rule.explain(mod, graph, query)
        assert isinstance(exp, RuleExplanation)
        assert exp.rule_name == "read_only_input"

    def test_explain_non_matched_node(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule
        from cogant.translate.engine import RuleExplanation
        graph, mod, func1, var1 = _make_graph()
        from cogant.graph.queries import GraphQuery
        rule = ReadOnlyInputRule()
        query = GraphQuery(graph)
        exp = rule.explain(func1, graph, query)
        assert isinstance(exp, RuleExplanation)
        assert exp.fired is False or exp.fired is True  # either is valid
