"""End-to-end integration tests for COGANT dynamic pipeline features.

These tests exercise the recently added dynamic analysis and translation
engine features together:

* ``PipelineRunner`` wired through the dynamic enrichment stage with a
  real coverage.xml file.
* ``TranslationEngine`` fixpoint iteration with priority-based conflict
  resolution and confidence tiebreakers.
* ``TranslationEngine.get_coverage_report`` on a partially-mapped graph.
* ``enrich_graph`` summary API returning the graph instance for
  functional-style composition.

Follows the project no-mocks policy: all inputs are real files built
under ``tmp_path`` and all computations run against real objects.
"""

from typing import Any, Dict, List, Optional

import pytest

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.dynamic.enrichment import enrich_graph
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.translate.engine import TranslationEngine, TranslationRule


# -- Sample data constants ---------------------------------------------------

MINIMAL_COBERTURA_XML = """\
<?xml version="1.0" ?>
<coverage version="5.5" timestamp="1234567890"
         lines-valid="4" lines-covered="3" line-rate="0.75"
         branches-valid="0" branches-covered="0" branch-rate="0"
         complexity="0">
  <packages>
    <package name="." line-rate="0.75">
      <classes>
        <class name="main.py" filename="main.py" line-rate="0.75">
          <lines>
            <line number="1" hits="1"/>
            <line number="2" hits="1"/>
            <line number="3" hits="0"/>
            <line number="4" hits="1"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


# -- Helpers ------------------------------------------------------------------

def _make_empty_graph() -> ProgramGraph:
    """Return a ProgramGraph with minimal but valid metadata."""
    metadata = GraphMetadata(
        repo_uri="test://repo",
        languages={"python"},
    )
    return ProgramGraph(metadata=metadata)


def _make_function_node(node_id: str, name: str, path: str = "test.py") -> Node:
    """Build a FUNCTION node with the given id and name."""
    return Node(
        id=node_id,
        kind=NodeKind.FUNCTION,
        name=name,
        qualified_name=name,
        path=path,
        language="python",
    )


class _StubRule(TranslationRule):
    """Minimal ``TranslationRule`` for conflict-resolution tests.

    Parameterises every aspect of the rule contract so the test body can
    instantiate several rules that all match the same node but differ in
    priority, confidence, or mapping kind.
    """

    def __init__(
        self,
        name: str,
        priority: int,
        mapping_id: str,
        mapping_kind: MappingKind,
        confidence: float,
        node_id: str,
    ) -> None:
        self._name = name
        self._priority = priority
        self._mapping_id = mapping_id
        self._mapping_kind = mapping_kind
        self._confidence = confidence
        self._node_id = node_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def mapping_kind(self) -> MappingKind:
        return self._mapping_kind

    @property
    def priority(self) -> int:
        return self._priority

    def matches(self, graph: ProgramGraph, query: Any) -> List[Dict[str, Any]]:
        if self._node_id in graph.nodes:
            return [{"node_id": self._node_id}]
        return []

    def apply(
        self,
        graph: ProgramGraph,
        match: Dict[str, Any],
    ) -> Optional[SemanticMapping]:
        return SemanticMapping(
            id=self._mapping_id,
            kind=self._mapping_kind,
            graph_fragment_node_ids=[match["node_id"]],
            confidence_score=self._confidence,
            provenance=[],
            evidence_diversity=0.0,
            parser_certainty=1.0,
            conflict_penalties=[],
        )


# =============================================================================
# 1. Pipeline with dynamic data flow
# =============================================================================

@pytest.mark.integration
class TestPipelineDynamicStage:
    """PipelineRunner end-to-end with the dynamic enrichment stage enabled."""

    def test_pipeline_with_coverage_enrichment(self, tmp_path):
        """Running the full pipeline with a coverage.xml path invokes the
        dynamic stage, enriches the program graph, and completes without
        errors.
        """
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text(
            "def hello():\n    return 'hi'\n",
            encoding="utf-8",
        )

        coverage_file = tmp_path / "coverage.xml"
        coverage_file.write_text(MINIMAL_COBERTURA_XML, encoding="utf-8")

        config = PipelineConfig(
            output_dir=str(tmp_path / "out"),
            plugins={"dynamic": {"coverage_path": str(coverage_file)}},
        )
        runner = PipelineRunner()
        bundle = runner.run(str(repo), config)

        # The dynamic stage must have executed and produced a result entry.
        assert "dynamic" in bundle.stage_results
        dynamic_result = bundle.stage_results["dynamic"]
        assert dynamic_result.get("type") == "dynamic_enrichment"
        # enrich_graph summary is merged into the stage result, so the
        # coverage counter key must be present.
        assert "coverage_nodes_enriched" in dynamic_result

        # The pipeline should complete cleanly.
        assert bundle.errors == [], f"Pipeline errors: {bundle.errors}"

        # The program graph must still be accessible downstream.
        pg = bundle.artifacts.get("_program_graph")
        assert pg is not None
        assert pg.node_count() >= 1

        # Evidence source should be stamped on the graph metadata because
        # a coverage_path was supplied, even if no nodes ended up matching.
        assert "dynamic_coverage" in pg.metadata.evidence_sources

    def test_pipeline_without_coverage_path_skips_enrichment(self, tmp_path):
        """Without a coverage_path the dynamic stage still runs but reports
        zero enriched nodes and does not add any evidence source.
        """
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text(
            "def hello():\n    return 'hi'\n",
            encoding="utf-8",
        )

        config = PipelineConfig(output_dir=str(tmp_path / "out"))
        runner = PipelineRunner()
        bundle = runner.run(str(repo), config)

        assert "dynamic" in bundle.stage_results
        dynamic_result = bundle.stage_results["dynamic"]
        assert dynamic_result.get("coverage_nodes_enriched", 0) == 0
        assert dynamic_result.get("trace_nodes_enriched", 0) == 0
        assert bundle.errors == []


# =============================================================================
# 2. Fixpoint iteration with priority-based rules
# =============================================================================

@pytest.mark.integration
class TestTranslationEngineConflictResolution:
    """TranslationEngine conflict-resolution semantics: priority wins, then
    confidence as tiebreaker.
    """

    def test_fixpoint_priority_beats_confidence(self):
        """When two rules overlap on a node, the higher-priority rule wins
        even if the lower-priority rule has a higher confidence score.
        """
        graph = _make_empty_graph()
        graph.add_node(_make_function_node("n1", "foo"))

        high_pri = _StubRule(
            name="high_pri",
            priority=10,
            mapping_id="m_high",
            mapping_kind=MappingKind.ACTION,
            confidence=0.5,  # LOWER confidence
            node_id="n1",
        )
        low_pri = _StubRule(
            name="low_pri",
            priority=1,
            mapping_id="m_low",
            mapping_kind=MappingKind.OBSERVATION,
            confidence=0.9,  # HIGHER confidence
            node_id="n1",
        )

        engine = TranslationEngine()
        engine.register_rule(high_pri)
        engine.register_rule(low_pri)
        mappings = engine.translate(graph)

        mapping_ids = {m.id for m in mappings}
        assert "m_high" in mapping_ids, (
            f"Expected high-priority mapping to win, got {mapping_ids}"
        )
        assert "m_low" not in mapping_ids, (
            f"Low-priority mapping should have been removed, got {mapping_ids}"
        )

    def test_conflict_resolution_confidence_tiebreaker(self):
        """When rule priorities are equal, the mapping with the higher
        confidence score should win the conflict resolution.
        """
        graph = _make_empty_graph()
        graph.add_node(_make_function_node("n1", "foo"))

        tie_low_conf = _StubRule(
            name="tie_low_conf",
            priority=5,
            mapping_id="m_tie_low",
            mapping_kind=MappingKind.OBSERVATION,
            confidence=0.3,
            node_id="n1",
        )
        tie_high_conf = _StubRule(
            name="tie_high_conf",
            priority=5,
            mapping_id="m_tie_high",
            mapping_kind=MappingKind.ACTION,
            confidence=0.85,
            node_id="n1",
        )

        engine = TranslationEngine()
        engine.register_rule(tie_low_conf)
        engine.register_rule(tie_high_conf)
        mappings = engine.translate(graph)

        mapping_ids = {m.id for m in mappings}
        assert "m_tie_high" in mapping_ids, (
            f"Expected higher-confidence mapping to win tiebreaker, got "
            f"{mapping_ids}"
        )
        assert "m_tie_low" not in mapping_ids, (
            f"Lower-confidence mapping should have been removed, got "
            f"{mapping_ids}"
        )


# =============================================================================
# 3. Coverage report with partial mappings
# =============================================================================

@pytest.mark.integration
class TestTranslationEngineCoverageReport:
    """TranslationEngine.get_coverage_report on a partially-mapped graph."""

    def test_coverage_report_identifies_unmapped(self):
        """A graph with 3 nodes where a rule matches exactly 1 should
        report ~33.33% coverage and list the other two as uncovered.
        """
        graph = _make_empty_graph()
        graph.add_node(_make_function_node("n1", "foo"))
        graph.add_node(_make_function_node("n2", "bar"))
        graph.add_node(_make_function_node("n3", "baz"))

        # A single rule that maps only n1.
        single_match_rule = _StubRule(
            name="single",
            priority=1,
            mapping_id="m_single",
            mapping_kind=MappingKind.OBSERVATION,
            confidence=0.9,
            node_id="n1",
        )

        engine = TranslationEngine()
        engine.register_rule(single_match_rule)
        mappings = engine.translate(graph)
        assert len(mappings) == 1

        report = engine.get_coverage_report(graph)

        assert report["total_nodes"] == 3
        assert report["covered_nodes"] == 1
        assert report["uncovered_nodes"] == 2
        # 1/3 ≈ 33.33% (rounded to 2 decimals in the implementation)
        assert report["coverage_percent"] == pytest.approx(33.33, abs=0.01)
        # n2 and n3 should both appear in the uncovered list.
        uncovered_ids = set(report["uncovered_node_ids"])
        assert uncovered_ids == {"n2", "n3"}

    def test_coverage_report_empty_graph(self):
        """An empty graph should return zero coverage without dividing by zero."""
        graph = _make_empty_graph()
        engine = TranslationEngine()
        engine.translate(graph)

        report = engine.get_coverage_report(graph)
        assert report["total_nodes"] == 0
        assert report["covered_nodes"] == 0
        assert report["uncovered_nodes"] == 0
        assert report["coverage_percent"] == 0.0


# =============================================================================
# 4. enrich_graph returns graph in summary (new API contract)
# =============================================================================

@pytest.mark.integration
class TestEnrichGraphSummaryContract:
    """enrich_graph summary shape: ``graph`` and ``evidence_sources`` keys."""

    def test_enrich_graph_returns_graph_in_summary(self, tmp_path):
        """Calling enrich_graph with no coverage or trace paths should still
        return a summary dict containing the original graph instance under
        the ``graph`` key and an empty ``evidence_sources`` list.
        """
        graph = _make_empty_graph()
        node = _make_function_node("n1", "foo")
        graph.add_node(node)

        summary = enrich_graph(graph, coverage_path=None, trace_path=None)

        # Functional-composition contract: the returned graph must be the
        # same instance (mutation is in-place).
        assert "graph" in summary
        assert summary["graph"] is graph

        # Both counters are zero when no paths are provided.
        assert summary["coverage_nodes_enriched"] == 0
        assert summary["trace_nodes_enriched"] == 0

        # Evidence-sources key is always present, empty when no sources used.
        assert "evidence_sources" in summary
        assert summary["evidence_sources"] == []

        # Underlying graph metadata evidence_sources should not have been
        # polluted with dynamic markers.
        assert "dynamic_coverage" not in graph.metadata.evidence_sources
        assert "dynamic_trace" not in graph.metadata.evidence_sources

    def test_enrich_graph_summary_with_coverage(self, tmp_path):
        """When coverage_path is supplied the summary still contains the
        graph instance and records dynamic_coverage as an evidence source.
        """
        coverage_file = tmp_path / "coverage.xml"
        coverage_file.write_text(MINIMAL_COBERTURA_XML, encoding="utf-8")

        graph = _make_empty_graph()
        node = Node(
            id="func:main",
            kind=NodeKind.FUNCTION,
            name="main",
            qualified_name="main.main",
            path="main.py",
            source_range={"start_line": 1, "end_line": 4},
            language="python",
        )
        graph.add_node(node)

        summary = enrich_graph(
            graph,
            coverage_path=str(coverage_file),
            trace_path=None,
        )

        assert summary["graph"] is graph
        assert "dynamic_coverage" in summary["evidence_sources"]
        assert "dynamic_coverage" in graph.metadata.evidence_sources
