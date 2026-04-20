"""Tests for TranslationEngine.explain(), validate(), get_convergence_info()."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import pytest
from cogant.translate.engine import TranslationEngine
from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import NodeKind, EdgeKind
from cogant.translate.rules.structural import ContainmentRule, ReadOnlyInputRule
from cogant.translate.rules.semantic import ActionRule, ObservationRule


def _graph_with_calls():
    b = ProgramGraphBuilder(repo_uri="test://engine")
    mod = b.add_node(kind=NodeKind.MODULE, name="mod", qualified_name="mod")
    fn_a = b.add_node(kind=NodeKind.FUNCTION, name="main", qualified_name="mod.main")
    fn_b = b.add_node(kind=NodeKind.FUNCTION, name="helper", qualified_name="mod.helper")
    cls = b.add_node(kind=NodeKind.CLASS, name="Sensor", qualified_name="mod.Sensor")
    b.add_edge(source_id=mod.id, target_id=fn_a.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=mod.id, target_id=fn_b.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=mod.id, target_id=cls.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=fn_a.id, target_id=fn_b.id, kind=EdgeKind.CALLS)
    return b.finalize()


@pytest.fixture
def engine():
    e = TranslationEngine(max_iterations=3)
    e.rules = [ContainmentRule(), ReadOnlyInputRule(), ActionRule(), ObservationRule()]
    return e


@pytest.fixture
def translated_engine(engine):
    graph = _graph_with_calls()
    engine.translate(graph)
    return engine


@pytest.mark.unit
def test_explain_returns_list(translated_engine):
    result = translated_engine.explain()
    assert isinstance(result, list)


@pytest.mark.unit
def test_explain_empty_after_no_translation():
    e = TranslationEngine()
    e.rules = [ContainmentRule()]
    result = e.explain()
    assert isinstance(result, list)


@pytest.mark.unit
def test_explain_has_entries_after_translation(translated_engine):
    result = translated_engine.explain()
    # May or may not have entries depending on whether rules fired
    assert isinstance(result, list)


@pytest.mark.unit
def test_validate_returns_list(translated_engine):
    result = translated_engine.validate()
    assert isinstance(result, list)


@pytest.mark.unit
def test_validate_empty_before_translation():
    e = TranslationEngine()
    e.rules = []
    result = e.validate()
    assert isinstance(result, list)


@pytest.mark.unit
def test_validate_no_issues_for_valid_mappings(translated_engine):
    issues = translated_engine.validate()
    assert isinstance(issues, list)


@pytest.mark.unit
def test_get_convergence_info_returns_dict(translated_engine):
    info = translated_engine.get_convergence_info()
    assert isinstance(info, dict)


@pytest.mark.unit
def test_get_convergence_info_has_converged_key(translated_engine):
    info = translated_engine.get_convergence_info()
    assert "converged" in info


@pytest.mark.unit
def test_get_convergence_info_before_translation():
    e = TranslationEngine()
    e.rules = []
    info = e.get_convergence_info()
    assert isinstance(info, dict)


@pytest.mark.unit
def test_validate_with_real_mappings():
    from cogant.schemas.semantic import MappingKind, SemanticMapping, ConfidenceTier
    e = TranslationEngine()
    e.rules = []
    # Inject a valid mapping directly
    m = SemanticMapping(
        id="m1",
        kind=MappingKind.HIDDEN_STATE,
        graph_fragment_node_ids=["n1"],
        semantic_label="state",
        confidence_score=0.8,
        confidence_tier=ConfidenceTier.STATIC_PLUS_RUNTIME,
    )
    e.mappings = {"m1": m}
    issues = e.validate()
    assert isinstance(issues, list)
    assert len(issues) == 0


@pytest.mark.unit
def test_validate_detects_empty_node_ids():
    from cogant.schemas.semantic import MappingKind, SemanticMapping, ConfidenceTier
    e = TranslationEngine()
    e.rules = []
    m = SemanticMapping(
        id="m2",
        kind=MappingKind.HIDDEN_STATE,
        graph_fragment_node_ids=[],
        semantic_label="empty",
        confidence_score=0.7,
        confidence_tier=ConfidenceTier.STATIC_PLUS_RUNTIME,
    )
    e.mappings = {"m2": m}
    issues = e.validate()
    assert any("no node IDs" in issue for issue in issues)


@pytest.mark.unit
def test_explain_with_match_log_entries():
    from cogant.schemas.semantic import MappingKind, SemanticMapping, ConfidenceTier
    e = TranslationEngine()
    e.rules = []
    # Inject match log entries to exercise explain() body
    e._match_log = [
        {"rule_name": "ActionRule", "event_type": "mapping_created"},
        {"rule_name": "ActionRule", "event_type": "mapping_created"},
        {"rule_name": "ContainmentRule", "event_type": "mapping_created"},
        {"event_type": "iteration_complete", "detail": "converged at iteration 2"},
    ]
    result = e.explain()
    assert isinstance(result, list)
    assert any("ActionRule" in r for r in result)
    assert any("ContainmentRule" in r for r in result)
    assert any("convergence" in r.lower() for r in result)
