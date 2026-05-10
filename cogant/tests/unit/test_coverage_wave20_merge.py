"""Wave-20 coverage tests for cogant.graph.merge.

Targets the gaps left after test_graph_merge_cov.py:

* ``GraphMerger._merge_edges`` skip-orphan-edge branch (line 249) — the
  ``continue`` taken when a dynamic edge references a node missing from
  the merged graph.
* ``GraphMerger.merge_incremental`` (lines 392-439) — the entire
  delta-merging code path including node-metadata updates, new-node
  additions, edge weight maxing, and evidence accumulation.
* ``GraphMerger.diff`` (lines 451-489) — added/removed/changed nodes
  and edges including the metadata/path/qualified_name change branches.
"""

from __future__ import annotations

from cogant.graph.merge import GraphMerger
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph


def _node(
    nid: str,
    *,
    name: str | None = None,
    qualified_name: str | None = None,
    path: str | None = None,
    metadata: dict | None = None,
) -> Node:
    return Node(
        id=nid,
        kind=NodeKind.FUNCTION,
        name=name or nid,
        qualified_name=qualified_name or f"pkg.{nid}",
        path=path or "pkg/file.py",
        metadata=metadata or {},
    )


def _edge(
    eid: str,
    src: str,
    tgt: str,
    *,
    weight: float = 1.0,
    kind: EdgeKind = EdgeKind.CALLS,
    evidence: list[str] | None = None,
) -> Edge:
    e = Edge(id=eid, source_id=src, target_id=tgt, kind=kind, weight=weight)
    if evidence:
        e.evidence_sources = list(evidence)
    return e


def _graph(repo: str = "file:///wave20") -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri=repo))


# --------------------------------------------------------------------------- #
# _merge_edges orphan-edge skip (line 249)
# --------------------------------------------------------------------------- #


def test_merge_edges_skips_orphan_dynamic_edge_with_missing_source():
    """Dynamic edges whose source is absent from merged are dropped silently."""
    static_g = _graph()
    static_g.add_node(_node("a"))
    static_g.add_node(_node("b"))
    static_g.add_edge(_edge("e1", "a", "b"))

    dynamic_g = _graph()
    # 'orphan_src' is NOT in static; node only exists in dynamic
    dynamic_g.add_node(_node("orphan_src"))
    dynamic_g.add_node(_node("a"))
    # When dynamic is merged, this edge will reach merged graph since
    # orphan_src enters via _merge_nodes. Use a true orphan — a dynamic
    # edge whose target_id never gets added because we drop the node.
    # We achieve that by giving the edge a target that isn't anywhere.
    bad_edge = Edge(
        id="bad",
        source_id="a",
        target_id="never_added",
        kind=EdgeKind.CALLS,
        weight=1.0,
    )
    dynamic_g.edges["bad"] = bad_edge  # bypass add_edge's validation

    merged, prov = GraphMerger().merge_graphs(static_g, dynamic_g)
    # The orphan edge with a missing target was skipped
    assert "bad" not in merged.edges
    # Original edge survived
    assert "e1" in merged.edges


def test_merge_edges_skips_orphan_dynamic_edge_with_missing_target():
    """Mirror test: missing target also triggers the continue branch."""
    static_g = _graph()
    static_g.add_node(_node("a"))
    static_g.add_node(_node("b"))

    dynamic_g = _graph()
    dynamic_g.add_node(_node("a"))
    dynamic_g.add_node(_node("b"))
    bad_edge = Edge(
        id="orphan",
        source_id="phantom_source",  # not in either graph
        target_id="b",
        kind=EdgeKind.CALLS,
    )
    dynamic_g.edges["orphan"] = bad_edge

    merged, _ = GraphMerger().merge_graphs(static_g, dynamic_g)
    assert "orphan" not in merged.edges


# --------------------------------------------------------------------------- #
# merge_incremental (lines 392-439)
# --------------------------------------------------------------------------- #


def test_merge_incremental_adds_new_nodes_from_delta():
    base = _graph()
    base.add_node(_node("a"))
    base.add_node(_node("b"))
    base.add_edge(_edge("e1", "a", "b"))

    delta = _graph()
    delta.add_node(_node("c"))  # new
    delta.add_node(_node("a"))  # existing, should not duplicate

    merged = GraphMerger().merge_incremental(base, delta)
    assert {"a", "b", "c"} == set(merged.nodes.keys())
    assert "e1" in merged.edges


def test_merge_incremental_updates_existing_node_metadata():
    """When delta has the same node id, metadata is merged into existing."""
    base = _graph()
    base.add_node(_node("a", metadata={"score": 1, "label": "old"}))

    delta = _graph()
    delta.add_node(_node("a", metadata={"score": 5, "extra": "from_delta"}))

    merged = GraphMerger().merge_incremental(base, delta)
    merged_node = merged.nodes["a"]
    # 'score' is overwritten, 'label' kept, 'extra' added (dict.update semantics)
    assert merged_node.metadata["score"] == 5
    assert merged_node.metadata["label"] == "old"
    assert merged_node.metadata["extra"] == "from_delta"


def test_merge_incremental_adds_new_edges_from_delta():
    base = _graph()
    base.add_node(_node("a"))
    base.add_node(_node("b"))

    delta = _graph()
    delta.add_node(_node("a"))
    delta.add_node(_node("b"))
    delta.add_edge(_edge("new_edge", "a", "b", evidence=["delta"]))

    merged = GraphMerger().merge_incremental(base, delta)
    assert "new_edge" in merged.edges
    assert merged.edges["new_edge"].evidence_sources == ["delta"]


def test_merge_incremental_skips_orphan_delta_edge():
    """A delta edge with an unresolvable endpoint is skipped."""
    base = _graph()
    base.add_node(_node("a"))

    delta = _graph()
    delta.add_node(_node("a"))
    bad_edge = Edge(
        id="bad",
        source_id="a",
        target_id="never_added",
        kind=EdgeKind.CALLS,
    )
    delta.edges["bad"] = bad_edge

    merged = GraphMerger().merge_incremental(base, delta)
    assert "bad" not in merged.edges


def test_merge_incremental_updates_existing_edge_weight_to_max():
    """Same source/target/kind: weight is taken as max(existing, delta)."""
    base = _graph()
    base.add_node(_node("a"))
    base.add_node(_node("b"))
    base.add_edge(_edge("e_base", "a", "b", weight=0.3, evidence=["static"]))

    delta = _graph()
    delta.add_node(_node("a"))
    delta.add_node(_node("b"))
    delta.add_edge(_edge("e_delta", "a", "b", weight=0.9, evidence=["dynamic"]))

    merged = GraphMerger().merge_incremental(base, delta)
    # Single edge with maxed weight and merged evidence
    assert len(merged.edges) == 1
    surviving = next(iter(merged.edges.values()))
    assert surviving.weight == 0.9
    assert set(surviving.evidence_sources) == {"static", "dynamic"}


def test_merge_incremental_does_not_duplicate_evidence():
    """Existing evidence sources are not appended twice."""
    base = _graph()
    base.add_node(_node("a"))
    base.add_node(_node("b"))
    base.add_edge(_edge("e_base", "a", "b", weight=0.5, evidence=["common"]))

    delta = _graph()
    delta.add_node(_node("a"))
    delta.add_node(_node("b"))
    delta.add_edge(_edge("e_delta", "a", "b", weight=0.5, evidence=["common"]))

    merged = GraphMerger().merge_incremental(base, delta)
    surviving = next(iter(merged.edges.values()))
    assert surviving.evidence_sources.count("common") == 1


def test_merge_incremental_skips_base_edge_when_node_missing():
    """If node was somehow filtered out, base edge is skipped."""
    base = _graph()
    base.add_node(_node("a"))
    # Manually inject an orphan edge into base
    base.edges["orphan"] = Edge(
        id="orphan",
        source_id="a",
        target_id="ghost",  # never added as node
        kind=EdgeKind.CALLS,
    )

    delta = _graph()

    merged = GraphMerger().merge_incremental(base, delta)
    assert "orphan" not in merged.edges


def test_merge_incremental_preserves_metadata_languages():
    base_meta = GraphMetadata(repo_uri="file:///inc")
    base_meta.languages = {"python"}
    base = ProgramGraph(metadata=base_meta)

    delta_meta = GraphMetadata(repo_uri="file:///inc")
    delta_meta.languages = {"javascript"}
    delta = ProgramGraph(metadata=delta_meta)

    merged = GraphMerger().merge_incremental(base, delta)
    assert merged.metadata.languages == {"python", "javascript"}


# --------------------------------------------------------------------------- #
# diff (lines 451-489)
# --------------------------------------------------------------------------- #


def test_diff_detects_added_and_removed_nodes():
    g1 = _graph()
    g1.add_node(_node("a"))
    g1.add_node(_node("b"))

    g2 = _graph()
    g2.add_node(_node("b"))
    g2.add_node(_node("c"))

    diff = GraphMerger().diff(g1, g2)
    assert diff.added_nodes == ["c"]
    assert diff.removed_nodes == ["a"]


def test_diff_detects_changed_node_name():
    g1 = _graph()
    g1.add_node(_node("a", name="old_name"))

    g2 = _graph()
    g2.add_node(_node("a", name="new_name"))

    diff = GraphMerger().diff(g1, g2)
    assert "a" in diff.changed_nodes
    assert diff.changed_nodes["a"]["name"]["old"] == "old_name"
    assert diff.changed_nodes["a"]["name"]["new"] == "new_name"


def test_diff_detects_changed_qualified_name():
    g1 = _graph()
    g1.add_node(_node("a", qualified_name="pkg.old"))

    g2 = _graph()
    g2.add_node(_node("a", qualified_name="pkg.new"))

    diff = GraphMerger().diff(g1, g2)
    assert "qualified_name" in diff.changed_nodes["a"]


def test_diff_detects_changed_path():
    g1 = _graph()
    g1.add_node(_node("a", path="pkg/old.py"))

    g2 = _graph()
    g2.add_node(_node("a", path="pkg/new.py"))

    diff = GraphMerger().diff(g1, g2)
    assert "path" in diff.changed_nodes["a"]


def test_diff_detects_changed_metadata():
    g1 = _graph()
    g1.add_node(_node("a", metadata={"v": 1}))

    g2 = _graph()
    g2.add_node(_node("a", metadata={"v": 2}))

    diff = GraphMerger().diff(g1, g2)
    assert "metadata" in diff.changed_nodes["a"]


def test_diff_no_changes_for_identical_node():
    """A node with identical fields produces no entry in changed_nodes."""
    g1 = _graph()
    g1.add_node(_node("a", name="x", qualified_name="pkg.x", path="pkg/x.py"))

    g2 = _graph()
    g2.add_node(_node("a", name="x", qualified_name="pkg.x", path="pkg/x.py"))

    diff = GraphMerger().diff(g1, g2)
    assert "a" not in diff.changed_nodes


def test_diff_detects_added_and_removed_edges():
    g1 = _graph()
    g1.add_node(_node("a"))
    g1.add_node(_node("b"))
    g1.add_node(_node("c"))
    g1.add_edge(_edge("e1", "a", "b"))
    g1.add_edge(_edge("e2", "b", "c"))

    g2 = _graph()
    g2.add_node(_node("a"))
    g2.add_node(_node("b"))
    g2.add_node(_node("c"))
    g2.add_edge(_edge("e1", "a", "b"))  # kept
    g2.add_edge(_edge("e_new", "c", "a"))  # added

    diff = GraphMerger().diff(g1, g2)
    assert ("c", "a") in diff.added_edges
    assert ("b", "c") in diff.removed_edges


def test_diff_empty_graphs_yield_empty_diff():
    g1 = _graph()
    g2 = _graph()
    diff = GraphMerger().diff(g1, g2)
    assert diff.added_nodes == []
    assert diff.removed_nodes == []
    assert diff.changed_nodes == {}
    assert diff.added_edges == []
    assert diff.removed_edges == []


def test_diff_records_multiple_node_changes_in_one_entry():
    """A single node with multiple changed fields produces one dict entry."""
    g1 = _graph()
    g1.add_node(_node("a", name="o", path="o.py", metadata={"k": 1}))

    g2 = _graph()
    g2.add_node(_node("a", name="n", path="n.py", metadata={"k": 2}))

    diff = GraphMerger().diff(g1, g2)
    assert {"name", "path", "metadata"}.issubset(diff.changed_nodes["a"].keys())


def test_diff_added_and_removed_edges_are_sorted():
    g1 = _graph()
    for nid in ["a", "b", "c", "d"]:
        g1.add_node(_node(nid))
    g1.add_edge(_edge("e1", "c", "d"))
    g1.add_edge(_edge("e2", "a", "b"))

    g2 = _graph()
    for nid in ["a", "b", "c", "d"]:
        g2.add_node(_node(nid))

    diff = GraphMerger().diff(g1, g2)
    # Removed edges are sorted by (source, target)
    assert diff.removed_edges == sorted(diff.removed_edges)
