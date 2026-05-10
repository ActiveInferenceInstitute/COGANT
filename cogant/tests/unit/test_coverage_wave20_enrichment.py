"""Wave-20 coverage tests for ``cogant.dynamic.enrichment``.

Targets the previously uncovered branches of ``_enrich_with_coverage``
(branch coverage, no spans, missing path) and the dynamic CALLS-edge
generation in ``_enrich_with_traces`` (lines 245-275). Every test uses a
real ``ProgramGraph`` plus a real on-disk Cobertura XML or Chrome trace
JSON — no mocks.
"""

from __future__ import annotations

import json
import sqlite3
import textwrap
from pathlib import Path

from cogant.dynamic.enrichment import (
    _enrich_with_coverage,
    _enrich_with_traces,
    _node_spans_line,
    enrich_graph,
)
from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

# ------------------------------------------------------------------ #
# Helpers (mirror existing tests)
# ------------------------------------------------------------------ #


def _func_node(
    nid: str,
    name: str,
    path: str = "pkg/mod.py",
    start: int = 1,
    end: int = 10,
    *,
    qualified: str | None = None,
    kind: NodeKind = NodeKind.FUNCTION,
) -> Node:
    n = Node(
        id=nid,
        kind=kind,
        name=name,
        qualified_name=qualified or f"pkg.{name}",
        path=path,
    )
    n.source_range = {"start_line": start, "end_line": end}
    return n


def _empty_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/wave20"))


def _graph_with_nodes(*nodes: Node) -> ProgramGraph:
    g = _empty_graph()
    for n in nodes:
        g.add_node(n)
    return g


def _write_cobertura_with_branches(
    tmp_path: Path,
    file_rel: str,
    lines: list[tuple[int, int, bool]],
) -> Path:
    """Write a Cobertura XML where each line is ``(number, hits, branch)``."""
    items: list[str] = []
    for ln, hits, branch in lines:
        attrs = f'number="{ln}" hits="{hits}"'
        if branch:
            attrs += ' branch="true" condition-coverage="50% (1/2)"'
        else:
            attrs += ' branch="false"'
        items.append(f"<line {attrs}/>")
    xml = textwrap.dedent(
        f"""\
        <?xml version="1.0" ?>
        <coverage>
          <packages>
            <package name="pkg">
              <classes>
                <class filename="{file_rel}">
                  <lines>
                    {"".join(items)}
                  </lines>
                </class>
              </classes>
            </package>
          </packages>
        </coverage>
        """
    )
    p = tmp_path / "cov_branch.xml"
    p.write_text(xml)
    return p


def _write_chrome_trace(tmp_path: Path, events: list[dict]) -> Path:
    p = tmp_path / "trace.json"
    p.write_text(json.dumps({"traceEvents": events}))
    return p


# ------------------------------------------------------------------ #
# _enrich_with_coverage — uncovered branches
# ------------------------------------------------------------------ #


def test_enrich_with_coverage_branch_coverage_partial(tmp_path: Path) -> None:
    """When some branch lines are hit and others not, branch_coverage is a
    fraction in (0, 1)."""
    cov_path = _write_cobertura_with_branches(
        tmp_path,
        "pkg/mod.py",
        [(5, 1, True), (6, 0, True), (7, 1, False)],
    )
    node = _func_node("n1", "fn", path="pkg/mod.py", start=1, end=20)
    g = _graph_with_nodes(node)

    enriched = _enrich_with_coverage(g, str(cov_path))
    assert enriched == 1
    md = g.nodes["n1"].metadata
    assert md.get("branch_coverage") is not None
    # one of two branches was hit -> 0.5
    assert md["branch_coverage"] == 0.5
    # covered lines (hits>0) include line 5 and 7 -> 2 hits
    assert md["coverage_hits"] >= 1


def test_enrich_with_coverage_branch_coverage_all_zero(tmp_path: Path) -> None:
    """All branch lines uncovered → branch_coverage = 0.0."""
    cov_path = _write_cobertura_with_branches(
        tmp_path,
        "pkg/mod.py",
        [(5, 0, True), (6, 0, True)],
    )
    node = _func_node("n1", "fn", path="pkg/mod.py", start=1, end=20)
    g = _graph_with_nodes(node)

    enriched = _enrich_with_coverage(g, str(cov_path))
    assert enriched == 1
    assert g.nodes["n1"].metadata["branch_coverage"] == 0.0


def test_enrich_with_coverage_skips_node_with_no_path(tmp_path: Path) -> None:
    """Nodes whose ``path`` is None are skipped (continue at line 114)."""
    cov_path = _write_cobertura_with_branches(
        tmp_path,
        "pkg/mod.py",
        [(5, 1, False)],
    )
    node = Node(
        id="n_no_path",
        kind=NodeKind.FUNCTION,
        name="orphan",
        qualified_name="orphan",
        path=None,
    )
    node.source_range = {"start_line": 1, "end_line": 10}
    matched = _func_node("matched", "fn", path="pkg/mod.py", start=1, end=10)
    g = _graph_with_nodes(node, matched)

    enriched = _enrich_with_coverage(g, str(cov_path))
    # Only the matched node is enriched; the path-less node is skipped.
    assert enriched == 1
    assert "coverage_hits" not in g.nodes["n_no_path"].metadata
    assert g.nodes["matched"].metadata.get("coverage_hits", 0) >= 1


def test_enrich_with_coverage_line_outside_node_range(tmp_path: Path) -> None:
    """Spans for the node's file but outside its line range are ignored."""
    cov_path = _write_cobertura_with_branches(
        tmp_path,
        "pkg/mod.py",
        [(100, 1, False)],  # well outside node lines 1-10
    )
    node = _func_node("n1", "fn", path="pkg/mod.py", start=1, end=10)
    g = _graph_with_nodes(node)

    enriched = _enrich_with_coverage(g, str(cov_path))
    # The single span doesn't overlap the node, so 0 enriched and no metadata.
    assert enriched == 0
    assert "coverage_hits" not in g.nodes["n1"].metadata


def test_enrich_with_coverage_empty_xml_returns_zero(tmp_path: Path) -> None:
    """An XML with no covered lines yields 0 spans → early-return path."""
    xml = textwrap.dedent(
        """\
        <?xml version="1.0" ?>
        <coverage>
          <packages>
            <package name="pkg">
              <classes>
              </classes>
            </package>
          </packages>
        </coverage>
        """
    )
    p = tmp_path / "empty.xml"
    p.write_text(xml)
    g = _graph_with_nodes(_func_node("n1", "fn"))

    assert _enrich_with_coverage(g, str(p)) == 0


def test_enrich_with_coverage_sqlite_default_branch(tmp_path: Path) -> None:
    """Non-XML suffix dispatches to ``ingest_coverage_py`` (line 96).

    We create a minimal coverage.py-compatible SQLite DB with the
    ``file`` and ``line_bits`` tables but no rows: the ingester loads it
    cleanly, returns no spans, and enrichment short-circuits.
    """
    db_path = tmp_path / "fake.coverage"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE file (id INTEGER PRIMARY KEY, path TEXT)")
    cur.execute("CREATE TABLE line_bits (file_id INTEGER, numbits BLOB)")
    conn.commit()
    conn.close()

    g = _graph_with_nodes(_func_node("n1", "fn", path="pkg/mod.py"))
    # Should not raise; should return 0 enriched.
    assert _enrich_with_coverage(g, str(db_path)) == 0


# ------------------------------------------------------------------ #
# _enrich_with_traces — dynamic CALLS edges (lines 245-275)
# ------------------------------------------------------------------ #


def test_enrich_with_traces_creates_dynamic_calls_edge(tmp_path: Path) -> None:
    """B/E events with nested calls create CALLS edges with weight + evidence."""
    events = [
        # Outer call ``alpha`` opens, inner call ``beta`` opens then closes
        # before alpha closes. This produces an alpha -> beta call-graph edge.
        {"name": "alpha", "ph": "B", "ts": 0, "pid": 1, "tid": 1},
        {"name": "beta", "ph": "B", "ts": 1, "pid": 1, "tid": 1},
        {"name": "beta", "ph": "E", "ts": 2, "pid": 1, "tid": 1},
        {"name": "alpha", "ph": "E", "ts": 3, "pid": 1, "tid": 1},
        # An additional X event so beta has timing and gets a real weight.
        {"name": "beta", "ph": "X", "dur": 500, "ts": 5, "pid": 1, "tid": 1},
    ]
    trace_path = _write_chrome_trace(tmp_path, events)

    n_alpha = _func_node("a1", "alpha", path="pkg/mod.py", start=1, end=50)
    n_beta = _func_node("b1", "beta", path="pkg/mod.py", start=51, end=80)
    g = _graph_with_nodes(n_alpha, n_beta)

    enriched = _enrich_with_traces(g, str(trace_path))
    assert enriched >= 1

    # A CALLS edge from alpha -> beta should now exist with the
    # ``dynamic_trace`` evidence marker.
    calls = [
        e
        for e in g.edges.values()
        if e.kind == EdgeKind.CALLS and e.source_id == "a1" and e.target_id == "b1"
    ]
    assert len(calls) == 1
    edge = calls[0]
    assert "dynamic_trace" in edge.evidence_sources
    assert edge.metadata.get("source") == "dynamic_trace"
    assert edge.weight >= 1.0


def test_enrich_with_traces_updates_existing_edge_weight(tmp_path: Path) -> None:
    """When a CALLS edge already exists, its weight is raised and
    evidence list gains ``dynamic_trace``."""
    from cogant.dynamic.enrichment import _stable_edge_id
    from cogant.schemas.core import Edge

    events = [
        {"name": "alpha", "ph": "B", "ts": 0, "pid": 1, "tid": 1},
        {"name": "beta", "ph": "X", "dur": 10000, "ts": 1, "pid": 1, "tid": 1},
        {"name": "alpha", "ph": "E", "ts": 11, "pid": 1, "tid": 1},
    ]
    trace_path = _write_chrome_trace(tmp_path, events)

    n_alpha = _func_node("a1", "alpha")
    n_beta = _func_node("b1", "beta")
    g = _graph_with_nodes(n_alpha, n_beta)

    edge_id = _stable_edge_id("a1", "b1", EdgeKind.CALLS.value)
    g.add_edge(
        Edge(
            id=edge_id,
            source_id="a1",
            target_id="b1",
            kind=EdgeKind.CALLS,
            weight=0.5,
            metadata={"source": "static"},
            evidence_sources=["static"],
        )
    )

    _enrich_with_traces(g, str(trace_path))

    edge = g.edges[edge_id]
    # existing weight (0.5) was raised to the trace-derived weight (1.0)
    assert edge.weight >= 1.0
    # evidence list was extended (idempotent: only one entry).
    assert edge.evidence_sources.count("dynamic_trace") == 1
    assert "static" in edge.evidence_sources


def test_enrich_with_traces_caller_unknown_skipped(tmp_path: Path) -> None:
    """Caller present in trace but not in graph index → no edge added."""
    events = [
        {"name": "ghost_caller", "ph": "B", "ts": 0, "pid": 1, "tid": 1},
        {"name": "real_callee", "ph": "X", "dur": 100, "ts": 1, "pid": 1, "tid": 1},
        {"name": "ghost_caller", "ph": "E", "ts": 2, "pid": 1, "tid": 1},
    ]
    trace_path = _write_chrome_trace(tmp_path, events)

    g = _graph_with_nodes(_func_node("c1", "real_callee"))

    _enrich_with_traces(g, str(trace_path))
    # No alpha node → no edges
    calls = [e for e in g.edges.values() if e.kind == EdgeKind.CALLS]
    assert calls == []


def test_enrich_with_traces_callee_unknown_skipped(tmp_path: Path) -> None:
    """Callee present in trace but not in graph index → no edge added."""
    events = [
        {"name": "real_caller", "ph": "B", "ts": 0, "pid": 1, "tid": 1},
        {"name": "ghost_callee", "ph": "X", "dur": 100, "ts": 1, "pid": 1, "tid": 1},
        {"name": "real_caller", "ph": "E", "ts": 2, "pid": 1, "tid": 1},
    ]
    trace_path = _write_chrome_trace(tmp_path, events)

    g = _graph_with_nodes(_func_node("c1", "real_caller"))
    _enrich_with_traces(g, str(trace_path))
    calls = [e for e in g.edges.values() if e.kind == EdgeKind.CALLS]
    assert calls == []


# ------------------------------------------------------------------ #
# Misc edge cases
# ------------------------------------------------------------------ #


def test_node_spans_line_missing_keys_returns_false() -> None:
    """source_range with neither start_line nor start.line → False."""
    node = Node(
        id="n1",
        kind=NodeKind.FUNCTION,
        name="fn",
        qualified_name="fn",
        path="x.py",
    )
    node.source_range = {"unrelated_key": 1}
    assert _node_spans_line(node, 5) is False


def test_enrich_graph_returns_self_graph_with_both_paths_idempotent(
    tmp_path: Path,
) -> None:
    """Second call adds no duplicate evidence_sources (idempotency for both)."""
    cov_path = _write_cobertura_with_branches(
        tmp_path,
        "pkg/mod.py",
        [(3, 1, False)],
    )
    events = [{"name": "fn", "ph": "X", "dur": 100, "ts": 0, "pid": 1, "tid": 1}]
    trace_path = _write_chrome_trace(tmp_path, events)

    g = _graph_with_nodes(_func_node("n1", "fn", path="pkg/mod.py"))
    enrich_graph(g, coverage_path=str(cov_path), trace_path=str(trace_path))
    enrich_graph(g, coverage_path=str(cov_path), trace_path=str(trace_path))

    assert g.metadata.evidence_sources.count("dynamic_coverage") == 1
    assert g.metadata.evidence_sources.count("dynamic_trace") == 1
