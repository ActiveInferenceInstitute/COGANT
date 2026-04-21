"""Comprehensive tests for COGANT dynamic analysis modules.

Tests cover:
- CoverageIngester: Cobertura XML parsing, missing/malformed files, span mapping
- TraceIngester: Chrome DevTools trace parsing, timing extraction, call graph
- enrich_graph: Graph enrichment with coverage and trace data
"""

import json

import pytest

from cogant.dynamic.coverage import CoverageIngester
from cogant.dynamic.enrichment import enrich_graph
from cogant.dynamic.traces import TraceIngester
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

# -- Sample data constants ---------------------------------------------------

MINIMAL_COBERTURA_XML = """\
<?xml version="1.0" ?>
<coverage version="5.5" timestamp="1234567890"
         lines-valid="10" lines-covered="5" line-rate="0.5"
         branches-valid="0" branches-covered="0" branch-rate="0"
         complexity="0">
  <packages>
    <package name="src" line-rate="0.5">
      <classes>
        <class name="main.py" filename="src/main.py" line-rate="0.5">
          <lines>
            <line number="1" hits="1"/>
            <line number="2" hits="1"/>
            <line number="3" hits="0"/>
            <line number="5" hits="1"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""

MINIMAL_CHROME_TRACE = {
    "traceEvents": [
        {"name": "foo", "cat": "function", "ph": "X", "ts": 1000, "dur": 500, "pid": 1, "tid": 1},
        {"name": "bar", "cat": "function", "ph": "X", "ts": 2000, "dur": 300, "pid": 1, "tid": 1},
        {"name": "foo", "cat": "function", "ph": "X", "ts": 3000, "dur": 400, "pid": 1, "tid": 1},
    ]
}


# -- Helper -------------------------------------------------------------------


def _make_graph(nodes, edges=None):
    """Build a ProgramGraph from lists of Node and Edge objects.

    Args:
        nodes: List of Node dataclass instances.
        edges: Optional list of Edge dataclass instances.

    Returns:
        A ProgramGraph with GraphMetadata populated.
    """
    metadata = GraphMetadata(
        repo_uri="test://repo",
        languages={"python"},
    )
    graph = ProgramGraph(metadata=metadata)
    for node in nodes:
        graph.add_node(node)
    for edge in edges or []:
        graph.add_edge(edge)
    return graph


# -- Fixtures -----------------------------------------------------------------


@pytest.fixture()
def cobertura_xml_path(tmp_path):
    """Write minimal Cobertura XML to a temporary file and return its path."""
    xml_file = tmp_path / "coverage.xml"
    xml_file.write_text(MINIMAL_COBERTURA_XML, encoding="utf-8")
    return str(xml_file)


@pytest.fixture()
def chrome_trace_path(tmp_path):
    """Write minimal Chrome trace JSON to a temporary file and return its path."""
    trace_file = tmp_path / "trace.json"
    trace_file.write_text(json.dumps(MINIMAL_CHROME_TRACE), encoding="utf-8")
    return str(trace_file)


# =============================================================================
# CoverageIngester tests
# =============================================================================


class TestCoverageIngester:
    """Tests for CoverageIngester."""

    def test_ingest_coverage_xml_valid(self, cobertura_xml_path):
        """Parse a valid Cobertura XML and verify structure and values."""
        ingester = CoverageIngester()
        result = ingester.ingest_coverage_xml(cobertura_xml_path)

        assert result["type"] == "coverage"
        assert result["format"] == "cobertura"

        # Summary should reflect top-level attributes
        summary = result["summary"]
        assert summary["line_rate"] == pytest.approx(0.5)
        assert summary["lines_valid"] == 10
        assert summary["lines_covered"] == 5

        # One file entry expected
        assert len(result["files"]) == 1
        file_entry = result["files"][0]
        assert file_entry["filename"] == "src/main.py"
        assert file_entry["package"] == "src"
        assert sorted(file_entry["covered_lines"]) == [1, 2, 5]
        assert file_entry["uncovered_lines"] == [3]

    def test_ingest_coverage_xml_missing_file(self, tmp_path):
        """Non-existent path returns graceful empty result."""
        ingester = CoverageIngester()
        result = ingester.ingest_coverage_xml(str(tmp_path / "does_not_exist.xml"))

        assert result["type"] == "coverage"
        assert result["files"] == []
        assert result["summary"]["line_rate"] == 0.0

    def test_ingest_coverage_xml_malformed(self, tmp_path):
        """Malformed XML returns graceful empty result without raising."""
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("<coverage><not-closed", encoding="utf-8")

        ingester = CoverageIngester()
        result = ingester.ingest_coverage_xml(str(bad_xml))

        assert result["type"] == "coverage"
        assert result["files"] == []
        assert result["summary"]["lines_valid"] == 0

    def test_map_coverage_to_spans(self, cobertura_xml_path):
        """After ingesting valid XML, spans have expected keys and values."""
        ingester = CoverageIngester()
        ingester.ingest_coverage_xml(cobertura_xml_path)
        spans = ingester.map_coverage_to_spans()

        assert len(spans) > 0

        required_keys = {"file", "start_line", "end_line", "covered"}
        for span in spans:
            assert required_keys.issubset(span.keys()), (
                f"Span missing keys: {required_keys - span.keys()}"
            )

        # Covered spans
        covered = [s for s in spans if s["covered"]]
        uncovered = [s for s in spans if not s["covered"]]
        assert len(covered) == 3  # lines 1, 2, 5
        assert len(uncovered) == 1  # line 3

        # All spans reference the correct file
        for span in spans:
            assert span["file"] == "src/main.py"


# =============================================================================
# TraceIngester tests
# =============================================================================


class TestTraceIngester:
    """Tests for TraceIngester."""

    def test_ingest_chrome_trace_valid(self, chrome_trace_path):
        """Parse a valid Chrome trace and verify non-empty events."""
        ingester = TraceIngester()
        result = ingester.ingest_chrome_trace(chrome_trace_path)

        assert len(result) == 1
        trace = result[0]
        assert trace["type"] == "trace"
        assert trace["format"] == "chrome"
        assert len(trace["events"]) == 3
        assert trace["duration_ms"] > 0

        # Verify event normalisation kept expected fields
        event_names = [e["name"] for e in trace["events"]]
        assert "foo" in event_names
        assert "bar" in event_names

    def test_ingest_chrome_trace_missing_file(self, tmp_path):
        """Non-existent path returns graceful empty result."""
        ingester = TraceIngester()
        result = ingester.ingest_chrome_trace(str(tmp_path / "missing.json"))

        assert len(result) == 1
        assert result[0]["events"] == []
        assert result[0]["duration_ms"] == 0

    def test_extract_timing(self, chrome_trace_path):
        """Timing dict has min/max/mean/count for each function."""
        ingester = TraceIngester()
        ingester.ingest_chrome_trace(chrome_trace_path)
        timing = ingester.extract_timing()

        assert "foo" in timing
        assert "bar" in timing

        foo_stats = timing["foo"]
        assert set(foo_stats.keys()) == {"min", "max", "mean", "count"}
        assert foo_stats["count"] == 2.0
        assert foo_stats["min"] > 0
        assert foo_stats["max"] >= foo_stats["min"]
        assert foo_stats["mean"] == pytest.approx((foo_stats["min"] + foo_stats["max"]) / 2.0)

        bar_stats = timing["bar"]
        assert bar_stats["count"] == 1.0
        assert bar_stats["min"] == bar_stats["max"] == bar_stats["mean"]

    def test_extract_call_graph(self, chrome_trace_path):
        """Call graph returns a caller-to-callees adjacency dict."""
        ingester = TraceIngester()
        ingester.ingest_chrome_trace(chrome_trace_path)
        call_graph = ingester.extract_call_graph()

        # With only top-level X events (no nesting), the call graph is
        # built from the stack: only when there is a parent on the stack
        # does an adjacency get recorded. Since all three events are
        # sequential (non-overlapping), no caller-callee pairs are found.
        assert isinstance(call_graph, dict)

    def test_extract_call_graph_nested(self, tmp_path):
        """Nested B/E events produce caller-to-callee adjacency entries."""
        nested_trace = {
            "traceEvents": [
                {"name": "outer", "cat": "function", "ph": "B", "ts": 100, "pid": 1, "tid": 1},
                {"name": "inner", "cat": "function", "ph": "B", "ts": 200, "pid": 1, "tid": 1},
                {"name": "inner", "cat": "function", "ph": "E", "ts": 300, "pid": 1, "tid": 1},
                {"name": "outer", "cat": "function", "ph": "E", "ts": 400, "pid": 1, "tid": 1},
            ]
        }
        trace_file = tmp_path / "nested_trace.json"
        trace_file.write_text(json.dumps(nested_trace), encoding="utf-8")

        ingester = TraceIngester()
        ingester.ingest_chrome_trace(str(trace_file))
        call_graph = ingester.extract_call_graph()

        assert "outer" in call_graph
        assert "inner" in call_graph["outer"]


# =============================================================================
# enrich_graph tests
# =============================================================================


class TestEnrichGraph:
    """Tests for enrich_graph integration."""

    def test_enrich_graph_no_data(self):
        """With both paths None, graph is unchanged and summary shows zero."""
        node_a = Node(
            id="func:a",
            kind=NodeKind.FUNCTION,
            name="func_a",
            qualified_name="mod.func_a",
            path="src/mod.py",
        )
        node_b = Node(
            id="func:b",
            kind=NodeKind.FUNCTION,
            name="func_b",
            qualified_name="mod.func_b",
            path="src/mod.py",
        )
        edge = Edge(
            id="edge:ab",
            source_id="func:a",
            target_id="func:b",
            kind=EdgeKind.CALLS,
        )
        graph = _make_graph([node_a, node_b], [edge])

        summary = enrich_graph(graph, coverage_path=None, trace_path=None)

        assert summary["coverage_nodes_enriched"] == 0
        assert summary["trace_nodes_enriched"] == 0
        # Graph structure unchanged
        assert graph.node_count() == 2
        assert graph.edge_count() == 1

    def test_enrich_graph_with_coverage(self, cobertura_xml_path):
        """Coverage enrichment adds coverage_hits to matching node."""
        node = Node(
            id="func:main",
            kind=NodeKind.FUNCTION,
            name="main",
            qualified_name="src.main.main",
            path="src/main.py",
            source_range={"start_line": 1, "end_line": 10},
        )
        graph = _make_graph([node])

        summary = enrich_graph(graph, coverage_path=cobertura_xml_path, trace_path=None)

        assert summary["coverage_nodes_enriched"] >= 1
        enriched_node = graph.get_node("func:main")
        assert "coverage_hits" in enriched_node.metadata
        assert enriched_node.metadata["coverage_hits"] > 0
        # Evidence source recorded on graph metadata
        assert "dynamic_coverage" in graph.metadata.evidence_sources

    def test_enrich_graph_with_traces(self, chrome_trace_path):
        """Trace enrichment adds call_count metadata to matching nodes."""
        node_foo = Node(
            id="func:foo",
            kind=NodeKind.FUNCTION,
            name="foo",
            qualified_name="mod.foo",
            path="src/mod.py",
        )
        node_bar = Node(
            id="func:bar",
            kind=NodeKind.FUNCTION,
            name="bar",
            qualified_name="mod.bar",
            path="src/mod.py",
        )
        graph = _make_graph([node_foo, node_bar])

        summary = enrich_graph(graph, coverage_path=None, trace_path=chrome_trace_path)

        assert summary["trace_nodes_enriched"] >= 1

        foo_node = graph.get_node("func:foo")
        assert "call_count" in foo_node.metadata
        assert foo_node.metadata["call_count"] == 2  # foo appears twice in trace

        bar_node = graph.get_node("func:bar")
        assert "call_count" in bar_node.metadata
        assert bar_node.metadata["call_count"] == 1

        # Evidence source recorded
        assert "dynamic_trace" in graph.metadata.evidence_sources

    def test_enrich_graph_coverage_no_match(self, cobertura_xml_path):
        """Node whose path does not match coverage file is not enriched."""
        node = Node(
            id="func:other",
            kind=NodeKind.FUNCTION,
            name="other",
            qualified_name="other.func",
            path="other/file.py",
            source_range={"start_line": 1, "end_line": 10},
        )
        graph = _make_graph([node])

        summary = enrich_graph(graph, coverage_path=cobertura_xml_path, trace_path=None)

        assert summary["coverage_nodes_enriched"] == 0
        assert "coverage_hits" not in graph.get_node("func:other").metadata

    def test_enrich_graph_with_both(self, cobertura_xml_path, chrome_trace_path):
        """Both coverage and trace enrichment can run together."""
        node = Node(
            id="func:foo",
            kind=NodeKind.FUNCTION,
            name="foo",
            qualified_name="src.main.foo",
            path="src/main.py",
            source_range={"start_line": 1, "end_line": 10},
        )
        graph = _make_graph([node])

        summary = enrich_graph(
            graph,
            coverage_path=cobertura_xml_path,
            trace_path=chrome_trace_path,
        )

        enriched = graph.get_node("func:foo")
        # Coverage enrichment
        assert summary["coverage_nodes_enriched"] >= 1
        assert "coverage_hits" in enriched.metadata
        # Trace enrichment
        assert summary["trace_nodes_enriched"] >= 1
        assert "call_count" in enriched.metadata
        # Both evidence sources
        assert "dynamic_coverage" in graph.metadata.evidence_sources
        assert "dynamic_trace" in graph.metadata.evidence_sources
