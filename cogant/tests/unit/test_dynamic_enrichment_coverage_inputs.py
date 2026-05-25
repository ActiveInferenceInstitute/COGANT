"""Behavioral tests for cogant.dynamic.enrichment.

Exercises all helper functions and the public enrich_graph API using
real ProgramGraph instances, real JSON trace files, and real Cobertura
XML coverage files — no mocks.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from cogant.dynamic.enrichment import (
    _build_function_index,
    _node_spans_line,
    _normalize_path,
    _stable_edge_id,
    enrich_graph,
)
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

# ------------------------------------------------------------------ #
# Graph-building helpers
# ------------------------------------------------------------------ #


def _func_node(
    nid: str,
    name: str,
    path: str = "pkg/mod.py",
    start: int = 1,
    end: int = 10,
    *,
    kind: NodeKind = NodeKind.FUNCTION,
) -> Node:
    n = Node(
        id=nid,
        kind=kind,
        name=name,
        qualified_name=f"pkg.{name}",
        path=path,
    )
    n.source_range = {"start_line": start, "end_line": end}
    return n


def _empty_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))


def _graph_with_funcs(*nodes: Node) -> ProgramGraph:
    g = _empty_graph()
    for n in nodes:
        g.add_node(n)
    return g


# ------------------------------------------------------------------ #
# _normalize_path
# ------------------------------------------------------------------ #


def test_normalize_path_strips_dotslash() -> None:
    assert _normalize_path("./pkg/foo.py") == "pkg/foo.py"


def test_normalize_path_strips_multiple_dotslash() -> None:
    assert _normalize_path("././src/bar.py") == "src/bar.py"


def test_normalize_path_converts_backslash() -> None:
    assert _normalize_path("pkg\\mod.py") == "pkg/mod.py"


def test_normalize_path_already_clean() -> None:
    assert _normalize_path("pkg/foo.py") == "pkg/foo.py"


def test_normalize_path_empty_string() -> None:
    assert _normalize_path("") == ""


# ------------------------------------------------------------------ #
# _node_spans_line
# ------------------------------------------------------------------ #


def test_node_spans_line_within_range() -> None:
    node = _func_node("n1", "fn", start=10, end=20)
    assert _node_spans_line(node, 15) is True


def test_node_spans_line_at_start() -> None:
    node = _func_node("n1", "fn", start=10, end=20)
    assert _node_spans_line(node, 10) is True


def test_node_spans_line_at_end() -> None:
    node = _func_node("n1", "fn", start=10, end=20)
    assert _node_spans_line(node, 20) is True


def test_node_spans_line_outside_range() -> None:
    node = _func_node("n1", "fn", start=10, end=20)
    assert _node_spans_line(node, 5) is False


def test_node_spans_line_no_source_range() -> None:
    node = Node(id="n1", kind=NodeKind.FUNCTION, name="fn", qualified_name="fn", path="f.py")
    # source_range defaults to empty dict / None
    node.source_range = {}
    assert _node_spans_line(node, 5) is False


def test_node_spans_line_alt_key_format() -> None:
    """Handles {'start': {'line': N}, 'end': {'line': M}} format."""
    node = Node(id="n1", kind=NodeKind.FUNCTION, name="fn", qualified_name="fn", path="f.py")
    node.source_range = {"start": {"line": 5}, "end": {"line": 15}}
    assert _node_spans_line(node, 10) is True
    assert _node_spans_line(node, 4) is False


# ------------------------------------------------------------------ #
# _stable_edge_id
# ------------------------------------------------------------------ #


def test_stable_edge_id_deterministic() -> None:
    eid1 = _stable_edge_id("src_node", "tgt_node", "CALLS")
    eid2 = _stable_edge_id("src_node", "tgt_node", "CALLS")
    assert eid1 == eid2


def test_stable_edge_id_different_for_different_inputs() -> None:
    eid_a = _stable_edge_id("a", "b", "CALLS")
    eid_b = _stable_edge_id("b", "a", "CALLS")
    assert eid_a != eid_b


def test_stable_edge_id_length_16() -> None:
    eid = _stable_edge_id("x", "y", "IMPORTS")
    assert len(eid) == 16


# ------------------------------------------------------------------ #
# _build_function_index
# ------------------------------------------------------------------ #


def test_build_function_index_only_callables() -> None:
    func = _func_node("f1", "run")
    module = Node(
        id="m1", kind=NodeKind.MODULE, name="mymod", qualified_name="pkg.mymod", path="pkg/mymod.py"
    )
    g = _graph_with_funcs(func, module)

    index = _build_function_index(g)
    assert "run" in index
    assert "mymod" not in index  # modules are not callable kinds


def test_build_function_index_includes_method() -> None:
    method = _func_node("m1", "do_work", kind=NodeKind.METHOD)
    g = _graph_with_funcs(method)

    index = _build_function_index(g)
    assert "do_work" in index


def test_build_function_index_maps_qualified_name() -> None:
    func = _func_node("f1", "compute")
    g = _graph_with_funcs(func)

    index = _build_function_index(g)
    # qualified_name is "pkg.compute"
    assert "pkg.compute" in index


def test_build_function_index_multiple_nodes_same_name() -> None:
    f1 = _func_node("f1", "helper", path="a.py")
    f2 = _func_node("f2", "helper", path="b.py")
    g = _graph_with_funcs(f1, f2)

    index = _build_function_index(g)
    assert "helper" in index
    assert len(index["helper"]) == 2


# ------------------------------------------------------------------ #
# enrich_graph — no enrichment
# ------------------------------------------------------------------ #


def test_enrich_graph_no_paths_returns_zero_counts() -> None:
    g = _empty_graph()
    result = enrich_graph(g, coverage_path=None, trace_path=None)
    assert result["coverage_nodes_enriched"] == 0
    assert result["trace_nodes_enriched"] == 0
    assert result["evidence_sources"] == []


def test_enrich_graph_returns_same_graph_instance() -> None:
    g = _empty_graph()
    result = enrich_graph(g)
    assert result["graph"] is g


# ------------------------------------------------------------------ #
# enrich_graph — coverage XML enrichment
# ------------------------------------------------------------------ #


def _write_cobertura(tmp_path: Path, file_rel: str, lines: list[int]) -> Path:
    """Write a minimal Cobertura-compatible coverage.xml."""
    line_items = "".join(f'<line number="{ln}" hits="1" branch="false"/>' for ln in lines)
    xml = textwrap.dedent(f"""\
        <?xml version="1.0" ?>
        <coverage>
          <packages>
            <package name="pkg">
              <classes>
                <class filename="{file_rel}">
                  <lines>
                    {line_items}
                  </lines>
                </class>
              </classes>
            </package>
          </packages>
        </coverage>
    """)
    cov_path = tmp_path / "coverage.xml"
    cov_path.write_text(xml)
    return cov_path


def test_enrich_graph_coverage_xml_annotates_matching_node(tmp_path: Path) -> None:
    """Coverage hits are added to a node whose path and line range match."""
    cov_path = _write_cobertura(tmp_path, "pkg/mod.py", [5, 6, 7])
    node = _func_node("n1", "compute", path="pkg/mod.py", start=1, end=10)
    g = _graph_with_funcs(node)

    result = enrich_graph(g, coverage_path=str(cov_path))
    assert result["coverage_nodes_enriched"] >= 1
    assert g.nodes["n1"].metadata.get("coverage_hits", 0) > 0


def test_enrich_graph_coverage_xml_evidence_source_added(tmp_path: Path) -> None:
    """'dynamic_coverage' is appended to graph metadata evidence_sources."""
    cov_path = _write_cobertura(tmp_path, "pkg/mod.py", [3])
    g = _empty_graph()

    enrich_graph(g, coverage_path=str(cov_path))
    assert "dynamic_coverage" in g.metadata.evidence_sources


def test_enrich_graph_coverage_xml_no_match(tmp_path: Path) -> None:
    """Nodes with a different path are not enriched."""
    cov_path = _write_cobertura(tmp_path, "other/file.py", [5])
    node = _func_node("n1", "compute", path="pkg/mod.py", start=1, end=10)
    g = _graph_with_funcs(node)

    result = enrich_graph(g, coverage_path=str(cov_path))
    assert result["coverage_nodes_enriched"] == 0
    assert "coverage_hits" not in g.nodes["n1"].metadata


def test_enrich_graph_coverage_idempotent_evidence_source(tmp_path: Path) -> None:
    """Calling enrich_graph twice does not duplicate evidence_sources."""
    cov_path = _write_cobertura(tmp_path, "pkg/mod.py", [3])
    g = _empty_graph()

    enrich_graph(g, coverage_path=str(cov_path))
    enrich_graph(g, coverage_path=str(cov_path))

    count = g.metadata.evidence_sources.count("dynamic_coverage")
    assert count == 1


# ------------------------------------------------------------------ #
# enrich_graph — Chrome trace enrichment
# ------------------------------------------------------------------ #


def _write_chrome_trace(tmp_path: Path, events: list[dict]) -> Path:
    """Write a minimal Chrome DevTools trace JSON."""
    trace = {"traceEvents": events}
    p = tmp_path / "trace.json"
    p.write_text(json.dumps(trace))
    return p


def test_enrich_graph_trace_annotates_matching_function(tmp_path: Path) -> None:
    """Trace timing is added to a function node whose name matches a trace event."""
    events = [
        {"name": "compute", "ph": "X", "dur": 1000, "ts": 0, "pid": 1, "tid": 1},
    ]
    trace_path = _write_chrome_trace(tmp_path, events)

    node = _func_node("n1", "compute", path="pkg/mod.py", start=1, end=10)
    g = _graph_with_funcs(node)

    result = enrich_graph(g, trace_path=str(trace_path))
    assert result["trace_nodes_enriched"] >= 1
    assert "call_count" in g.nodes["n1"].metadata


def test_enrich_graph_trace_evidence_source_added(tmp_path: Path) -> None:
    """'dynamic_trace' appears in graph metadata evidence_sources after trace enrichment."""
    events = [{"name": "fn", "ph": "X", "dur": 500, "ts": 0, "pid": 1, "tid": 1}]
    trace_path = _write_chrome_trace(tmp_path, events)
    g = _empty_graph()

    enrich_graph(g, trace_path=str(trace_path))
    assert "dynamic_trace" in g.metadata.evidence_sources


def test_enrich_graph_trace_no_match_still_adds_evidence(tmp_path: Path) -> None:
    """Even if no node names match, the evidence_source label is added."""
    events = [{"name": "unknown_fn", "ph": "X", "dur": 100, "ts": 0, "pid": 1, "tid": 1}]
    trace_path = _write_chrome_trace(tmp_path, events)
    g = _empty_graph()

    result = enrich_graph(g, trace_path=str(trace_path))
    assert "dynamic_trace" in g.metadata.evidence_sources
    assert result["trace_nodes_enriched"] == 0


def test_enrich_graph_both_paths_populate_both_sources(tmp_path: Path) -> None:
    """Passing both coverage and trace paths adds both evidence sources."""
    cov_path = _write_cobertura(tmp_path, "pkg/mod.py", [3])
    events = [{"name": "fn", "ph": "X", "dur": 100, "ts": 0, "pid": 1, "tid": 1}]
    trace_path = _write_chrome_trace(tmp_path, events)
    g = _empty_graph()

    enrich_graph(g, coverage_path=str(cov_path), trace_path=str(trace_path))
    sources = g.metadata.evidence_sources
    assert "dynamic_coverage" in sources
    assert "dynamic_trace" in sources
