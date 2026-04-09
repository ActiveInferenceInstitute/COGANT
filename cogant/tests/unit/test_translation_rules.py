"""Unit tests for :mod:`cogant.translate.engine` and concrete rules.

These tests exercise the real ``TranslationEngine`` and a real
``TranslationRule`` subclass (``ReadOnlyInputRule``) against a
hand-built ``ProgramGraph``. No dict literals or pseudo-rules — every
assertion touches concrete cogant classes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.graph.queries import GraphQuery
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.translate.engine import TranslationEngine, TranslationRule
from cogant.translate.rules.structural import ReadOnlyInputRule

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def read_only_graph() -> ProgramGraph:
    """Build a graph with a module that has READS edges but no WRITES,
    which the ``ReadOnlyInputRule`` should classify as an observation.
    """
    builder = ProgramGraphBuilder(repo_uri="test://read-only")
    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="sensor_reader",
        qualified_name="sensor_reader",
        path="sensor_reader.py",
        language="python",
    )
    data1 = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="raw_data",
        qualified_name="sensor_reader.raw_data",
        path="sensor_reader.py",
        language="python",
    )
    data2 = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="config",
        qualified_name="sensor_reader.config",
        path="sensor_reader.py",
        language="python",
    )
    builder.add_edge(module.id, data1.id, EdgeKind.READS)
    builder.add_edge(module.id, data2.id, EdgeKind.READS)
    return builder.finalize()


@pytest.fixture
def empty_graph() -> ProgramGraph:
    """Empty graph with no nodes or edges."""
    return ProgramGraphBuilder(repo_uri="test://empty").finalize()


# --------------------------------------------------------------- stub rule


class _StubRule(TranslationRule):
    """Stub rule that emits a mapping per MODULE node in the graph.

    Uses a unique id incorporating the rule's priority so collisions can
    be exercised in isolation.
    """

    def __init__(
        self,
        name: str = "stub",
        priority: int = 0,
        kind: MappingKind = MappingKind.HIDDEN_STATE,
    ) -> None:
        self._name = name
        self._priority = priority
        self._kind = kind

    def matches(
        self, graph: ProgramGraph, query: GraphQuery
    ) -> List[Dict[str, Any]]:
        return [{"node_id": n.id} for n in graph.get_nodes_by_kind(NodeKind.MODULE)]

    def apply(
        self, graph: ProgramGraph, match: Dict[str, Any]
    ) -> Optional[SemanticMapping]:
        node_id = match["node_id"]
        return SemanticMapping(
            id=f"mapping:{self._name}:{node_id}",
            kind=self._kind,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{self._name}_{node_id}",
            description="stub mapping",
            confidence_score=0.5,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[ProvenanceRecord(source="stub", confidence=0.5)],
            evidence_count=1,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def mapping_kind(self) -> MappingKind:
        return self._kind

    @property
    def priority(self) -> int:
        return self._priority


# --------------------------------------------------------------- engine tests


class TestTranslationEngineConstruction:
    """Tests for :class:`TranslationEngine` construction and registration."""

    def test_engine_starts_empty(self) -> None:
        engine = TranslationEngine()
        assert engine.rules == []
        assert engine.mappings == {}
        assert engine.max_iterations == 10

    def test_engine_accepts_max_iterations(self) -> None:
        engine = TranslationEngine(max_iterations=3)
        assert engine.max_iterations == 3

    def test_register_rule_adds_to_rules(self) -> None:
        engine = TranslationEngine()
        rule = _StubRule()
        engine.register_rule(rule)
        assert engine.rules == [rule]


class TestTranslationEngineTranslate:
    """Tests for :meth:`TranslationEngine.translate`."""

    def test_translate_empty_graph_returns_empty(
        self, empty_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine()
        engine.register_rule(_StubRule())
        mappings = engine.translate(empty_graph)
        assert mappings == []

    def test_translate_with_stub_rule_produces_mapping(
        self, read_only_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine()
        engine.register_rule(_StubRule(name="s1"))
        mappings = engine.translate(read_only_graph)
        # 1 module node -> 1 mapping
        assert len(mappings) == 1
        assert mappings[0].kind is MappingKind.HIDDEN_STATE
        assert mappings[0].id == f"mapping:s1:{mappings[0].graph_fragment_node_ids[0]}"

    def test_translate_with_real_read_only_input_rule(
        self, read_only_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        mappings = engine.translate(read_only_graph)
        assert len(mappings) == 1
        mapping = mappings[0]
        assert mapping.kind is MappingKind.OBSERVATION
        assert mapping.confidence_tier is ConfidenceTier.STATIC_ONLY
        assert mapping.semantic_label.endswith("Read-Only Input")

    def test_translate_rule_filter_applies_only_named(
        self, read_only_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine()
        engine.register_rule(_StubRule(name="keep"))
        engine.register_rule(_StubRule(name="skip"))
        mappings = engine.translate(read_only_graph, rule_filter=["keep"])
        # Conflict resolution: keep & skip targeted same module; filter excludes skip
        assert len(mappings) == 1
        assert "keep" in mappings[0].id

    def test_translate_fixpoint_terminates_without_progress(
        self, empty_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine(max_iterations=3)
        engine.register_rule(_StubRule())
        mappings = engine.translate(empty_graph)
        assert mappings == []
        log = engine.get_match_log()
        # Should have at least one iteration_complete event
        events = {entry["event_type"] for entry in log}
        assert "iteration_complete" in events


class TestTranslationEngineConflictResolution:
    """Tests for conflict resolution between overlapping mappings."""

    def test_priority_wins_over_lower_priority(
        self, read_only_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine()
        engine.register_rule(_StubRule(name="low", priority=1))
        engine.register_rule(_StubRule(name="high", priority=10))
        mappings = engine.translate(read_only_graph)
        # Both rules emit mappings touching the same module -> conflict
        # High priority wins.
        assert len(mappings) == 1
        assert "high" in mappings[0].id


class TestCoverageReport:
    """Tests for :meth:`TranslationEngine.get_coverage_report`."""

    def test_coverage_report_empty_graph(
        self, empty_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine()
        report = engine.get_coverage_report(empty_graph)
        assert report["total_nodes"] == 0
        assert report["covered_nodes"] == 0
        assert report["coverage_percent"] == 0.0

    def test_coverage_report_after_translation(
        self, read_only_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        engine.translate(read_only_graph)
        report = engine.get_coverage_report(read_only_graph)
        assert report["total_nodes"] == 3  # module + 2 vars
        assert report["covered_nodes"] == 1  # only the module is mapped
        assert report["uncovered_nodes"] == 2
        assert 0.0 < report["coverage_percent"] <= 100.0


class TestEngineQueries:
    """Tests for mapping-query helpers on the engine."""

    def test_get_mappings_by_kind(self, read_only_graph: ProgramGraph) -> None:
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        engine.translate(read_only_graph)
        obs = engine.get_mappings_by_kind(MappingKind.OBSERVATION)
        hidden = engine.get_mappings_by_kind(MappingKind.HIDDEN_STATE)
        assert len(obs) == 1
        assert hidden == []

    def test_get_statistics_reports_rule_count(
        self, read_only_graph: ProgramGraph
    ) -> None:
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        engine.register_rule(_StubRule(name="extra"))
        engine.translate(read_only_graph)
        stats = engine.get_statistics()
        assert stats["rules_registered"] == 2
        assert stats["total_mappings"] >= 1
