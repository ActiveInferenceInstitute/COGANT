#!/usr/bin/env python3
"""Smoke tests for graph TypedDict aliases and SVG DOT export (coverage gate helpers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from cogant.export.svg_export import SVGExporter
from cogant.graph.types import (
    AdjacencyMatrix,
    CentralityDict,
    CommunityList,
    GraphStats,
    PathList,
)
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

pytestmark = pytest.mark.unit


def test_graph_stats_typed_dict_and_aliases() -> None:
    """Import-time types are exercised by real values (not mocks)."""
    stats: GraphStats = {
        "node_count": 3,
        "edge_count": 2,
        "density": 0.5,
        "is_dag": True,
        "component_count": 1,
    }
    assert stats["node_count"] == 3

    c: CentralityDict = {"a": 0.1, "b": 0.9}
    assert c["b"] == 0.9

    comm: CommunityList = [frozenset({"x", "y"})]
    assert len(comm[0]) == 2

    paths: PathList = [["n1", "n2"], ["n0"]]
    assert paths[0][1] == "n2"

    adj: AdjacencyMatrix = [[0, 1], [0, 0]]
    assert adj[0][1] == 1


@dataclass
class _PartitionBlanket:
    """Minimal stand-in for SVG export (expects .partitions and optional .edges)."""

    partitions: dict[str, list[str]]
    edges: list[Edge] = field(default_factory=list)


def test_svg_exporter_graph_to_dot_and_fallback(tmp_path: Path) -> None:
    """Exercise DOT generation and no-graphviz fallback path."""
    metadata = GraphMetadata(repo_uri="test://svg", languages={"python"})
    graph = ProgramGraph(metadata=metadata)
    n0 = Node(
        id="n0",
        kind=NodeKind.FUNCTION,
        name="f",
        qualified_name="f",
        path="m.py",
    )
    n1 = Node(
        id="n1",
        kind=NodeKind.CLASS,
        name="C",
        qualified_name="C",
        path="m.py",
    )
    graph.add_node(n0)
    graph.add_node(n1)
    graph.add_edge(
        Edge(
            id="e0",
            source_id="n0",
            target_id="n1",
            kind=EdgeKind.CALLS,
        )
    )

    exp = SVGExporter()
    dot = exp.graph_to_dot(graph)
    assert "digraph program_graph" in dot
    assert "n0" in dot or "n_0" in dot or "func" in dot.lower()

    out_svg = str(tmp_path / "g.svg")
    result = exp.export_program_graph(graph, out_svg)
    # With or without graphviz we get a path string back.
    assert isinstance(result, str)
    p = Path(result)
    assert p.exists()


def test_svg_exporter_blanket_to_dot_clusters() -> None:
    """Cover blanket_to_dot with partition clusters and unknown region color."""
    exp = SVGExporter()
    e1 = Edge(
        id="be1",
        source_id="node-a",
        target_id="node.b",
        kind=EdgeKind.READS,
    )
    blanket = _PartitionBlanket(
        partitions={
            "core": ["node-a"],
            "markov": ["node.b"],
            "external": ["node/c"],
            "other_region": ["z"],
        },
        edges=[e1],
    )
    dot = exp.blanket_to_dot(blanket)  # type: ignore[arg-type]
    assert "digraph markov_blanket" in dot
    assert "cluster_0" in dot
    assert "other_region" in dot
    assert "->" in dot


def test_svg_exporter_export_markov_blanket_fallback(tmp_path: Path) -> None:
    """Same as program graph: DOT file or SVG when graphviz exists."""
    exp = SVGExporter()
    blanket = _PartitionBlanket(partitions={"core": ["a1"]}, edges=[])
    out_svg = str(tmp_path / "blanket.svg")
    result = exp.export_markov_blanket(blanket, out_svg)  # type: ignore[arg-type]
    assert isinstance(result, str)
    assert Path(result).exists()


def test_svg_exporter_dot_fallback_when_graphviz_unavailable(
    tmp_path: Path,
) -> None:
    """Cover logger + .dot write paths when rendering is disabled."""
    metadata = GraphMetadata(repo_uri="test://dotfb", languages={"python"})
    graph = ProgramGraph(metadata=metadata)
    graph.add_node(
        Node(
            id="only",
            kind=NodeKind.MODULE,
            name="m",
            qualified_name="m",
            path="x.py",
        )
    )
    exp = SVGExporter()
    exp._graphviz_available = False
    out = str(tmp_path / "out.svg")
    path = exp.export_program_graph(graph, out)
    assert path.endswith(".dot")
    assert Path(path).read_text().startswith("digraph")

    exp2 = SVGExporter()
    exp2._graphviz_available = False
    blanket = _PartitionBlanket(partitions={"core": ["only"]}, edges=[])
    p2 = exp2.export_markov_blanket(blanket, str(tmp_path / "mb.svg"))  # type: ignore[arg-type]
    assert p2.endswith(".dot")
    assert "markov_blanket" in Path(p2).read_text()


def test_svg_exporter_safe_id_and_node_color() -> None:
    """Private helpers used by graph_to_dot."""
    exp = SVGExporter()
    assert exp._safe_id("a-b.c/d") == "a_b_c_d"
    assert exp._get_node_color("class") == "lightblue"
    assert exp._get_node_color("unknown_kind") == "white"


def test_svg_exporter_render_failure_path(tmp_path: Path) -> None:
    """_render_dot_to_svg raises RuntimeError when graphviz returns non-zero."""
    exp = SVGExporter()
    if not exp._graphviz_available:
        pytest.skip("graphviz not installed")

    bad_dot = "this is not valid dot {"
    out_svg = str(tmp_path / "bad.svg")
    with pytest.raises(RuntimeError, match="graphviz"):
        exp._render_dot_to_svg(bad_dot, out_svg)
