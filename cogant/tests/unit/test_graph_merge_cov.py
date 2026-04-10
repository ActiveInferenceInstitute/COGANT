"""Behavioral tests for cogant.graph.merge.GraphMerger.

Exercises pairwise and multi-graph merge, all three conflict resolution
strategies, metadata merging, and the statistics roll-up.
"""

from __future__ import annotations

import pytest

from cogant.graph.merge import GraphMerger, MergeConflict, MergeProvenance
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph


# --------------------------- builders ----------------------------------- #


def _node(nid: str, name: str | None = None) -> Node:
    return Node(
        id=nid,
        kind=NodeKind.FUNCTION,
        name=name or nid,
        qualified_name=f"pkg.{name or nid}",
        path="pkg/file.py",
    )


def _edge(
    eid: str,
    src: str,
    tgt: str,
    *,
    weight: float = 1.0,
    evidence_sources: list[str] | None = None,
) -> Edge:
    e = Edge(id=eid, source_id=src, target_id=tgt, kind=EdgeKind.CALLS, weight=weight)
    if evidence_sources:
        e.evidence_sources = list(evidence_sources)
    return e


def _graph(
    repo: str,
    *,
    languages: set[str] | None = None,
    evidence: list[str] | None = None,
) -> ProgramGraph:
    meta = GraphMetadata(repo_uri=repo)
    if languages:
        meta.languages = set(languages)
    if evidence:
        meta.evidence_sources = list(evidence)
    return ProgramGraph(metadata=meta)


# --------------------------- merge entry points ------------------------- #


def test_merge_with_no_graphs_raises_valueerror():
    """merge([]) and merge_multiple_graphs([]) both raise ValueError."""
    with pytest.raises(ValueError):
        GraphMerger().merge([])
    with pytest.raises(ValueError):
        GraphMerger().merge_multiple_graphs([])


def test_merge_single_graph_returns_it_unchanged():
    """Merging a singleton returns the same graph instance."""
    g = _graph("file:///tmp/only")
    g.add_node(_node("a"))
    result = GraphMerger().merge([g])
    assert result is g


# --------------------------- pairwise merge ----------------------------- #


def test_merge_graphs_adds_nodes_and_edges_from_both():
    """Nodes/edges unique to each side appear in the output."""
    static_g = _graph("file:///tmp/repo")
    static_g.add_node(_node("a"))
    static_g.add_node(_node("b"))
    static_g.add_edge(_edge("e1", "a", "b"))

    dynamic_g = _graph("file:///tmp/repo")
    dynamic_g.add_node(_node("b"))  # overlap
    dynamic_g.add_node(_node("c"))  # only in dynamic
    dynamic_g.add_edge(_edge("e2", "b", "c"))

    merger = GraphMerger()
    merged, prov = merger.merge_graphs(static_g, dynamic_g)

    assert set(merged.nodes.keys()) == {"a", "b", "c"}
    assert "e1" in merged.edges and "e2" in merged.edges
    assert prov.nodes_added == 3
    assert prov.edges_added >= 2


def test_merge_graphs_combines_metadata_languages_and_evidence():
    """Merged metadata is the union of languages and evidence sources."""
    static_g = _graph(
        "file:///tmp/repo", languages={"python"}, evidence=["static"]
    )
    dynamic_g = _graph(
        "file:///tmp/repo", languages={"javascript"}, evidence=["dynamic"]
    )

    merged, _ = GraphMerger().merge_graphs(static_g, dynamic_g)

    assert merged.metadata.languages == {"python", "javascript"}
    assert set(merged.metadata.evidence_sources) == {"static", "dynamic"}
    assert merged.metadata.repo_uri == "file:///tmp/repo"


def test_merge_graphs_records_provenance_in_history():
    """Each merge appends a MergeProvenance entry to merge_history."""
    merger = GraphMerger()
    merger.merge_graphs(_graph("f"), _graph("f"))
    merger.merge_graphs(_graph("f"), _graph("f"))

    assert len(merger.merge_history) == 2
    assert all(isinstance(p, MergeProvenance) for p in merger.merge_history)


# --------------------------- conflict resolution ------------------------ #


def _conflicting_pair() -> tuple[ProgramGraph, ProgramGraph]:
    static_g = _graph("file:///tmp/repo")
    static_g.add_node(_node("a"))
    static_g.add_node(_node("b"))
    static_g.add_edge(_edge("e_static", "a", "b", weight=0.5, evidence_sources=["static"]))

    dynamic_g = _graph("file:///tmp/repo")
    dynamic_g.add_node(_node("a"))
    dynamic_g.add_node(_node("b"))
    dynamic_g.add_edge(
        _edge("e_dynamic", "a", "b", weight=1.0, evidence_sources=["dynamic"])
    )
    return static_g, dynamic_g


def test_merge_graphs_union_strategy_picks_max_weight():
    """Union resolution uses max weight of conflicting edges."""
    static_g, dynamic_g = _conflicting_pair()
    merged, prov = GraphMerger().merge_graphs(static_g, dynamic_g, conflict_resolution="union")

    # One edge survives (the static one, updated)
    merged_edge = next(iter(merged.edges.values()))
    assert merged_edge.weight == 1.0
    # A conflict was recorded with union resolution
    assert any(c.resolution == "union" for c in prov.conflicts)


def test_merge_graphs_static_priority_keeps_static_weight():
    """static_priority leaves the static edge weight unchanged."""
    static_g, dynamic_g = _conflicting_pair()
    merged, prov = GraphMerger().merge_graphs(
        static_g, dynamic_g, conflict_resolution="static_priority"
    )
    merged_edge = next(iter(merged.edges.values()))
    assert merged_edge.weight == 0.5
    assert any(c.resolution == "static_priority" for c in prov.conflicts)


def test_merge_graphs_dynamic_priority_uses_dynamic_weight():
    """dynamic_priority overwrites with the dynamic weight."""
    static_g, dynamic_g = _conflicting_pair()
    merged, prov = GraphMerger().merge_graphs(
        static_g, dynamic_g, conflict_resolution="dynamic_priority"
    )
    merged_edge = next(iter(merged.edges.values()))
    assert merged_edge.weight == 1.0
    assert any(c.resolution == "dynamic_priority" for c in prov.conflicts)
    # Conflict type is classified correctly
    assert all(c.conflict_type == "edge_weight_mismatch" for c in prov.conflicts)


def test_merge_graphs_no_weight_conflict_merges_evidence():
    """Same-kind edges without weight mismatch just merge evidence sources."""
    static_g = _graph("file:///tmp/repo")
    static_g.add_node(_node("a"))
    static_g.add_node(_node("b"))
    static_g.add_edge(_edge("e1", "a", "b", weight=1.0, evidence_sources=["static"]))

    dynamic_g = _graph("file:///tmp/repo")
    dynamic_g.add_node(_node("a"))
    dynamic_g.add_node(_node("b"))
    dynamic_g.add_edge(_edge("e2", "a", "b", weight=1.0, evidence_sources=["dynamic"]))

    merged, prov = GraphMerger().merge_graphs(static_g, dynamic_g)

    merged_edge = next(iter(merged.edges.values()))
    assert set(merged_edge.evidence_sources) == {"static", "dynamic"}
    # No conflict because weights match
    assert prov.conflicts == []


# --------------------------- multi-graph merge -------------------------- #


def test_merge_list_three_graphs_pairwise():
    """merge() iterates pairwise across the full list."""
    graphs = []
    for name in "xyz":
        g = _graph(f"file:///tmp/{name}")
        g.add_node(_node(name))
        graphs.append(g)
    # Connect the second two so their edge is kept
    graphs[1].add_node(_node("y2"))
    graphs[1].add_edge(_edge("ey", "y", "y2"))

    merged = GraphMerger().merge(graphs)

    assert {"x", "y", "z", "y2"}.issubset(merged.nodes)


def test_merge_multiple_graphs_returns_accumulated():
    """merge_multiple_graphs propagates nodes from every tuple."""
    graphs = [
        ("s", _graph("f")),
        ("d", _graph("f")),
    ]
    graphs[0][1].add_node(_node("a"))
    graphs[1][1].add_node(_node("b"))

    merged = GraphMerger().merge_multiple_graphs(graphs)
    assert {"a", "b"}.issubset(merged.nodes)


# --------------------------- statistics --------------------------------- #


def test_statistics_empty_history():
    """get_merge_statistics handles the empty-history case."""
    assert GraphMerger().get_merge_statistics() == {"total_merges": 0}


def test_statistics_sums_across_history():
    """Statistics aggregate counts over every recorded merge."""
    merger = GraphMerger()
    # Perform two merges
    s1, d1 = _conflicting_pair()
    merger.merge_graphs(s1, d1)
    s2, d2 = _conflicting_pair()
    merger.merge_graphs(s2, d2)

    stats = merger.get_merge_statistics()
    assert stats["total_merges"] == 2
    assert stats["total_conflicts"] >= 2
    assert stats["total_nodes_added"] >= 4
