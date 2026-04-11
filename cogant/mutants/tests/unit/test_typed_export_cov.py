"""Behavioral tests for cogant.export.typed_export.TypedExporter.

Feeds a real ProgramGraph with multiple node and edge kinds to every
exporter method and asserts on the structure of the output.
"""

from __future__ import annotations

from cogant.export.typed_export import TypedExporter
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph


def _node(nid: str, kind: NodeKind, name: str | None = None) -> Node:
    return Node(
        id=nid,
        kind=kind,
        name=name or nid,
        qualified_name=f"pkg.{name or nid}",
        path="pkg/file.py",
        language="python",
    )


def _edge(eid: str, src: str, tgt: str, kind: EdgeKind, weight: float = 1.0) -> Edge:
    return Edge(id=eid, source_id=src, target_id=tgt, kind=kind, weight=weight)


def _sample_graph() -> ProgramGraph:
    meta = GraphMetadata(repo_uri="file:///tmp/repo")
    meta.languages = {"python", "javascript"}
    meta.evidence_sources = ["static"]
    meta.custom_metadata = {"total_lines": 1234}
    g = ProgramGraph(metadata=meta)
    g.add_node(_node("cls-1", NodeKind.CLASS, name="Foo"))
    g.add_node(_node("fn.1", NodeKind.FUNCTION, name="do_thing"))
    g.add_node(_node("mtd-1", NodeKind.METHOD, name="helper"))
    g.add_edge(_edge("e1", "cls-1", "fn.1", EdgeKind.CONTAINS, weight=2.0))
    g.add_edge(_edge("e2", "fn.1", "mtd-1", EdgeKind.CALLS, weight=1.5))
    return g


# --------------------------- export_typed_graph ------------------------- #


def test_export_typed_graph_includes_metadata_nodes_and_edges():
    exp = TypedExporter().export_typed_graph(_sample_graph())
    # Top-level keys
    assert set(exp.keys()) == {"metadata", "nodes", "edges"}
    # Metadata is serializable: languages is a list, timestamps are strings
    meta = exp["metadata"]
    assert meta["repo_uri"] == "file:///tmp/repo"
    assert set(meta["languages"]) == {"python", "javascript"}
    assert meta["node_count"] == 3
    assert meta["edge_count"] == 2
    assert isinstance(meta["created_at"], str)
    # Nodes contain the expected fields
    node_ids = {n["id"] for n in exp["nodes"]}
    assert node_ids == {"cls-1", "fn.1", "mtd-1"}
    # Edges contain the expected fields
    edge_ids = {e["id"] for e in exp["edges"]}
    assert edge_ids == {"e1", "e2"}
    assert exp["edges"][0]["source_id"] in node_ids


# --------------------------- export_graphviz_dot ------------------------ #


def test_export_graphviz_dot_sanitizes_ids_and_wraps_in_digraph():
    dot = TypedExporter().export_graphviz_dot(_sample_graph())
    assert dot.startswith("digraph program_graph {")
    assert dot.rstrip().endswith("}")
    # Dashes and dots in ids are converted to underscores
    assert "cls_1" in dot
    assert "fn_1" in dot
    assert "mtd_1" in dot
    # Edge labels correspond to EdgeKind values
    assert "contains" in dot
    assert "calls" in dot


def test_export_graphviz_dot_empty_graph_still_valid():
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    dot = TypedExporter().export_graphviz_dot(g)
    assert dot.startswith("digraph program_graph {")
    assert "}" in dot


# --------------------------- export_cytoscape_json ---------------------- #


def test_export_cytoscape_json_has_elements_key():
    result = TypedExporter().export_cytoscape_json(_sample_graph())
    assert "elements" in result
    # 3 nodes + 2 edges = 5 elements
    assert len(result["elements"]) == 5
    # Every element has a 'data' key
    assert all("data" in el for el in result["elements"])
    # Nodes and edges are distinguishable by the presence of 'source'
    node_elements = [e for e in result["elements"] if "source" not in e["data"]]
    edge_elements = [e for e in result["elements"] if "source" in e["data"]]
    assert len(node_elements) == 3
    assert len(edge_elements) == 2


# --------------------------- export_adjacency_matrix ------------------- #


def test_export_adjacency_matrix_records_edges_and_kinds():
    result = TypedExporter().export_adjacency_matrix(_sample_graph())
    assert "matrix" in result
    assert "node_labels" in result
    assert "edge_types" in result
    assert result["dimensions"] == [3, 3]
    # Exactly two non-zero entries (one per edge)
    nonzero = sum(1 for row in result["matrix"] for v in row if v != 0)
    assert nonzero == 2
    # Both edge kinds show up
    assert set(result["edge_types"].keys()) == {"contains", "calls"}


def test_export_adjacency_matrix_empty_graph_is_zero_by_zero():
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    result = TypedExporter().export_adjacency_matrix(g)
    assert result["dimensions"] == [0, 0]
    assert result["matrix"] == []


def test_export_adjacency_matrix_skips_dangling_edges():
    """Edges that reference missing nodes are silently ignored."""
    g = _sample_graph()
    # Directly inject a dangling edge (add_edge would reject it)
    g.edges["dangling"] = _edge("dangling", "cls-1", "missing-node", EdgeKind.CALLS)
    result = TypedExporter().export_adjacency_matrix(g)
    # Still only 2 non-zero entries — the dangling edge is ignored
    nonzero = sum(1 for row in result["matrix"] for v in row if v != 0)
    assert nonzero == 2


# --------------------------- _get_node_color --------------------------- #


def test_get_node_color_maps_known_kinds():
    ex = TypedExporter()
    # Each kind produces a distinct CSS color name
    assert ex._get_node_color(NodeKind.CLASS) == "lightblue"
    assert ex._get_node_color(NodeKind.FUNCTION) == "lightgreen"
    assert ex._get_node_color(NodeKind.METHOD) == "lightyellow"
    assert ex._get_node_color(NodeKind.MODULE) == "lightcyan"


def test_get_node_color_unknown_kind_returns_white():
    """Unmapped kinds fall back to 'white'."""
    ex = TypedExporter()
    assert ex._get_node_color(NodeKind.FILE) == "white"
