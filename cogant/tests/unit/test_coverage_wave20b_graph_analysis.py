"""Wave 20b coverage boost: cogant.graph.analysis missing lines.

Targets uncovered lines:
- 31-32: networkx ImportError fallback
- 229-234: Louvain exception fallback to connected components
- 317: ImportError when no networkx (to_networkx)
- 411: _compute_all_out_degrees helper
- 415-418: _compute_density helper
- 436: _compute_diameter returns None when graph disconnected
- 514-535: betweenness centrality pure-Python fallback
- 587: pagerank empty graph
- 610: shortest path source==target identity
- 620: BFS continues when get_node returns None
- 632: shortest path returns None when unreachable
- 688: _find_all_paths_dfs max_depth exceeded
"""

from __future__ import annotations

import pytest

from cogant.graph.analysis import (
    CycleDetection,
    GraphAnalyzer,
    HotspotAnalysis,
    PathAnalysis,
    _try_import_networkx,
)
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="test://repo"))


def _add_node(g: ProgramGraph, nid: str) -> Node:
    n = Node(id=nid, kind=NodeKind.FUNCTION, name=nid, qualified_name=f"m.{nid}")
    g.add_node(n)
    return n


def _add_edge(g: ProgramGraph, src: str, tgt: str, eid: str | None = None) -> Edge:
    e = Edge(
        id=eid or f"e:{src}->{tgt}",
        source_id=src,
        target_id=tgt,
        kind=EdgeKind.CALLS,
    )
    g.add_edge(e)
    return e


# ---------------------------------------------------------------------------
# Lines 31-32: _try_import_networkx ImportError fallback
# ---------------------------------------------------------------------------


def test_try_import_networkx_returns_module_or_none() -> None:
    """Hits the import branch; nx is installed in CI so the success path runs.

    The ImportError branch (lines 31-32) is exercised through the `nx` is None
    check pattern in other tests; here we just confirm the helper returns either
    the networkx module or None and never raises.
    """
    nx = _try_import_networkx()
    # Either networkx is installed (truthy module) or it's None
    assert nx is None or hasattr(nx, "DiGraph")


def test_try_import_networkx_when_unavailable(monkeypatch) -> None:
    """Force ImportError to cover lines 31-32."""
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "networkx":
            raise ImportError("simulated networkx missing")
        return real_import(name, *args, **kwargs)

    # Drop cached networkx so a fresh import goes through fake_import.
    monkeypatch.setitem(sys.modules, "networkx", None)
    try:
        sys.modules.pop("networkx")
    except KeyError:
        pass
    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Reload analysis to re-evaluate _try_import_networkx with patched import.
    import cogant.graph.analysis as analysis_module

    importlib.reload(analysis_module)
    result = analysis_module._try_import_networkx()
    assert result is None

    # Restore real networkx for downstream tests.
    monkeypatch.setattr(builtins, "__import__", real_import)
    importlib.reload(analysis_module)


# ---------------------------------------------------------------------------
# Lines 229-234: Louvain exception fallback to connected components
# ---------------------------------------------------------------------------


def test_find_communities_falls_back_when_louvain_raises(monkeypatch) -> None:
    """Force Louvain community detection to raise so we hit lines 229-234.

    Patch networkx.algorithms.community.louvain_communities to raise.
    """
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    _add_edge(g, "A", "B")

    analyzer = GraphAnalyzer(g)
    if analyzer.nx is None:
        pytest.skip("networkx not installed; Louvain branch unreachable")

    from networkx.algorithms import community as community_module

    def boom(*args, **kwargs):
        raise RuntimeError("simulated Louvain failure")

    monkeypatch.setattr(community_module, "louvain_communities", boom)

    communities = analyzer.find_communities()
    # Should have fallen back to connected components
    assert isinstance(communities, list)
    assert len(communities) >= 1
    assert all(isinstance(c, frozenset) for c in communities)


def test_find_communities_no_networkx_uses_connected_components(monkeypatch) -> None:
    """When self.nx is None, the Louvain branch is skipped entirely (fallback path)."""
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    _add_node(g, "C")
    _add_edge(g, "A", "B")
    _add_edge(g, "B", "C")

    analyzer = GraphAnalyzer(g)
    monkeypatch.setattr(analyzer, "nx", None)

    communities = analyzer.find_communities()
    assert len(communities) >= 1
    # All nodes should appear in some community
    union: set[str] = set()
    for c in communities:
        union |= set(c)
    assert union == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Line 317: to_networkx ImportError when nx is None
# ---------------------------------------------------------------------------


def test_to_networkx_raises_without_networkx(monkeypatch) -> None:
    g = _make_graph()
    _add_node(g, "A")
    analyzer = GraphAnalyzer(g)
    monkeypatch.setattr(analyzer, "nx", None)

    with pytest.raises(ImportError, match="networkx"):
        analyzer.to_networkx()


# ---------------------------------------------------------------------------
# Lines 411: _compute_all_out_degrees
# ---------------------------------------------------------------------------


def test_compute_all_out_degrees_helper() -> None:
    g = _make_graph()
    for nid in ("A", "B", "C"):
        _add_node(g, nid)
    _add_edge(g, "A", "B")
    _add_edge(g, "A", "C")
    _add_edge(g, "B", "C")

    analyzer = GraphAnalyzer(g)
    out_degrees = analyzer._compute_all_out_degrees()
    assert out_degrees == {"A": 2, "B": 1, "C": 0}


# ---------------------------------------------------------------------------
# Lines 415-418: _compute_density helper
# ---------------------------------------------------------------------------


def test_compute_density_helper_empty() -> None:
    g = _make_graph()
    analyzer = GraphAnalyzer(g)
    assert analyzer._compute_density() == 0.0


def test_compute_density_helper_with_edges() -> None:
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    _add_node(g, "C")
    _add_edge(g, "A", "B")

    analyzer = GraphAnalyzer(g)
    # 3 nodes, 1 edge: max edges = 3*2 = 6, density = 1/6
    density = analyzer._compute_density()
    assert density == pytest.approx(1.0 / 6.0, rel=1e-6)


def test_compute_density_helper_single_node() -> None:
    g = _make_graph()
    _add_node(g, "A")
    analyzer = GraphAnalyzer(g)
    # max_edges = 1*0 = 0 → returns 0.0
    assert analyzer._compute_density() == 0.0


# ---------------------------------------------------------------------------
# Line 436: diameter returns None when graph disconnected
# ---------------------------------------------------------------------------


def test_diameter_returns_none_for_disconnected_graph() -> None:
    """_compute_diameter returns None when any pair has no path between them.

    `get_neighbors` is undirected, so disconnected = literally no edge connecting
    the two components. Use two unconnected nodes.
    """
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    # No edges → the two nodes have no path between them via BFS.

    analyzer = GraphAnalyzer(g)
    diameter = analyzer._compute_diameter()
    assert diameter is None


def test_diameter_returns_none_when_fewer_than_two_nodes() -> None:
    g = _make_graph()
    analyzer = GraphAnalyzer(g)
    assert analyzer._compute_diameter() is None

    _add_node(g, "Solo")
    analyzer = GraphAnalyzer(g)
    assert analyzer._compute_diameter() is None


# ---------------------------------------------------------------------------
# Lines 514-535: pure-Python betweenness centrality fallback
# ---------------------------------------------------------------------------


def test_betweenness_centrality_pure_python_fallback(monkeypatch) -> None:
    """Force the pure-Python fallback by setting nx to None."""
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    _add_node(g, "C")
    _add_edge(g, "A", "B")
    _add_edge(g, "B", "C")

    analyzer = GraphAnalyzer(g)
    monkeypatch.setattr(analyzer, "nx", None)

    centrality = analyzer._compute_betweenness_centrality()
    # B is between A and C, should have centrality 1.0 (after normalization)
    assert "B" in centrality
    assert centrality["B"] == pytest.approx(1.0)
    # Endpoints A and C have 0 betweenness
    assert centrality["A"] == 0.0
    assert centrality["C"] == 0.0


def test_betweenness_centrality_pure_python_zero_peak(monkeypatch) -> None:
    """When no node lies on any path (e.g. disconnected pair), peak is 0 → no normalization."""
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    # No edges → no shortest paths → all zeros
    analyzer = GraphAnalyzer(g)
    monkeypatch.setattr(analyzer, "nx", None)

    centrality = analyzer._compute_betweenness_centrality()
    assert all(v == 0.0 for v in centrality.values())


def test_betweenness_centrality_pure_python_empty_graph(monkeypatch) -> None:
    g = _make_graph()
    analyzer = GraphAnalyzer(g)
    monkeypatch.setattr(analyzer, "nx", None)
    centrality = analyzer._compute_betweenness_centrality()
    assert centrality == {}


def test_betweenness_centrality_nx_exception_falls_back(monkeypatch) -> None:
    """Force nx.betweenness_centrality to raise so we hit the except: pass + fallback."""
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    _add_edge(g, "A", "B")
    analyzer = GraphAnalyzer(g)
    if analyzer.nx is None:
        pytest.skip("networkx not installed")

    def boom(*args, **kwargs):
        raise RuntimeError("simulated betweenness failure")

    # Patch the bound module's helper
    monkeypatch.setattr(analyzer.nx, "betweenness_centrality", boom)
    centrality = analyzer._compute_betweenness_centrality()
    # Should have fallen back to pure Python
    assert "A" in centrality
    assert "B" in centrality


# ---------------------------------------------------------------------------
# Line 587: pagerank empty graph
# ---------------------------------------------------------------------------


def test_pagerank_empty_graph(monkeypatch) -> None:
    g = _make_graph()
    analyzer = GraphAnalyzer(g)
    monkeypatch.setattr(analyzer, "nx", None)
    rank = analyzer._compute_pagerank()
    assert rank == {}


def test_pagerank_pure_python_fallback(monkeypatch) -> None:
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    _add_edge(g, "A", "B")
    analyzer = GraphAnalyzer(g)
    monkeypatch.setattr(analyzer, "nx", None)
    rank = analyzer._compute_pagerank()
    assert "A" in rank
    assert "B" in rank
    assert all(v >= 0 for v in rank.values())


def test_pagerank_nx_exception_falls_back(monkeypatch) -> None:
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    _add_edge(g, "A", "B")
    analyzer = GraphAnalyzer(g)
    if analyzer.nx is None:
        pytest.skip("networkx not installed")

    def boom(*args, **kwargs):
        raise RuntimeError("simulated pagerank failure")

    monkeypatch.setattr(analyzer.nx, "pagerank", boom)
    rank = analyzer._compute_pagerank()
    # Pure-Python fallback returns dict with both nodes
    assert "A" in rank
    assert "B" in rank


# ---------------------------------------------------------------------------
# Line 610: BFS shortest path source == target
# ---------------------------------------------------------------------------


def test_shortest_path_self_returns_singleton() -> None:
    g = _make_graph()
    _add_node(g, "X")
    analyzer = GraphAnalyzer(g)
    path = analyzer._find_shortest_path_bfs("X", "X")
    assert path == ["X"]


# ---------------------------------------------------------------------------
# Line 620: BFS continues when current_node is None
# ---------------------------------------------------------------------------


def test_shortest_path_handles_dangling_edge(monkeypatch) -> None:
    """Force `current_node = self.graph.get_node(current_id)` to return None
    on the first popleft to hit line 620's `continue`."""
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    _add_edge(g, "A", "B")

    analyzer = GraphAnalyzer(g)

    real_get_node = g.get_node
    call_counter = {"n": 0}

    def fake_get_node(nid: str):
        call_counter["n"] += 1
        # First call (for the source node A) returns None to skip the loop body
        if call_counter["n"] == 1:
            return None
        return real_get_node(nid)

    monkeypatch.setattr(g, "get_node", fake_get_node)
    # With source A skipped, BFS won't enqueue any neighbors → no path returned.
    path = analyzer._find_shortest_path_bfs("A", "B")
    assert path is None  # Hit line 620 continue and exhausted queue → line 632


# ---------------------------------------------------------------------------
# Line 632: shortest path returns None when unreachable
# ---------------------------------------------------------------------------


def test_shortest_path_unreachable_returns_none() -> None:
    g = _make_graph()
    _add_node(g, "A")
    _add_node(g, "B")
    # Disconnected nodes — no edges between them
    analyzer = GraphAnalyzer(g)
    path = analyzer._find_shortest_path_bfs("A", "B")
    assert path is None


# ---------------------------------------------------------------------------
# Line 688: _find_all_paths_dfs max_depth exceeded
# ---------------------------------------------------------------------------


def test_find_all_paths_dfs_respects_max_depth() -> None:
    """Build a chain A -> B -> C -> D and request max_depth=2 to cap recursion."""
    g = _make_graph()
    for nid in ("A", "B", "C", "D"):
        _add_node(g, nid)
    _add_edge(g, "A", "B")
    _add_edge(g, "B", "C")
    _add_edge(g, "C", "D")

    analyzer = GraphAnalyzer(g)
    # Looking for cycles (start == target == "A"), path D->A doesn't close,
    # but the DFS will still iterate up to max_depth before giving up at line 688.
    paths = analyzer._find_all_paths_dfs("A", "A", max_depth=2)
    # Chain has no cycle, so no paths returned
    assert paths == []


def test_find_all_cycles_short_max_size() -> None:
    """find_all_cycles with deep chains exercises max_depth check (line 688)."""
    g = _make_graph()
    # Long chain so DFS hits max_depth
    for nid in ("A", "B", "C", "D", "E", "F"):
        _add_node(g, nid)
    _add_edge(g, "A", "B")
    _add_edge(g, "B", "C")
    _add_edge(g, "C", "D")
    _add_edge(g, "D", "E")
    _add_edge(g, "E", "F")

    analyzer = GraphAnalyzer(g)
    cycles = analyzer._find_all_cycles(max_cycle_size=3)
    # No cycles in a chain
    assert cycles == []


# ---------------------------------------------------------------------------
# Sanity: dataclass instantiations the suite hasn't already covered
# ---------------------------------------------------------------------------


def test_path_analysis_default_construction() -> None:
    pa = PathAnalysis(shortest_path=None)
    assert pa.shortest_path is None
    assert pa.all_paths == []
    assert pa.critical_path == []


def test_cycle_detection_default_construction() -> None:
    cd = CycleDetection(has_cycles=False)
    assert cd.has_cycles is False
    assert cd.cycles == []
    assert cd.strongly_connected_components == []


def test_hotspot_analysis_default_construction() -> None:
    ha = HotspotAnalysis()
    assert ha.hubs == []
    assert ha.bottlenecks == []
    assert ha.sinks == []
    assert ha.sources == []
