"""Unit tests for viz/graph_view.py — GraphVisualizer."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import pytest
from cogant.viz.graph_view import GraphVisualizer
from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph, GraphMetadata


def _typed_graph() -> ProgramGraph:
    b = ProgramGraphBuilder(repo_uri="test://graphview")
    mod_a = b.add_node(kind=NodeKind.MODULE, name="pkg.mod_a", qualified_name="pkg.mod_a")
    mod_b = b.add_node(kind=NodeKind.MODULE, name="pkg.mod_b", qualified_name="pkg.mod_b")
    cls = b.add_node(kind=NodeKind.CLASS, name="MyClass", qualified_name="pkg.mod_a.MyClass")
    fn = b.add_node(kind=NodeKind.FUNCTION, name="helper", qualified_name="pkg.mod_b.helper")
    b.add_edge(source_id=mod_a.id, target_id=cls.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=mod_b.id, target_id=fn.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=mod_a.id, target_id=mod_b.id, kind=EdgeKind.IMPORTS)
    b.add_edge(source_id=cls.id, target_id=fn.id, kind=EdgeKind.CALLS)
    return b.finalize()


def _graph_dict() -> dict:
    return {
        "nodes": [
            {"id": "n1", "name": "mod_a", "kind": "MODULE", "qualified_name": "mod_a"},
            {"id": "n2", "name": "ClassA", "kind": "CLASS", "qualified_name": "mod_a.ClassA"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "kind": "CONTAINS"},
        ],
    }


@pytest.fixture
def gv():
    return GraphVisualizer()


@pytest.fixture
def graph():
    return _typed_graph()


@pytest.mark.unit
def test_init():
    assert GraphVisualizer() is not None


@pytest.mark.unit
def test_from_program_graph_dict_returns_self(gv):
    result = gv.from_program_graph(_graph_dict())
    assert result is gv


@pytest.mark.unit
def test_from_typed_graph_returns_self(gv, graph):
    result = gv.from_typed_graph(graph)
    assert result is gv


@pytest.mark.unit
def test_cluster_by_package(gv, graph):
    gv.from_typed_graph(graph)
    result = gv.cluster_by_package()
    assert result is gv


@pytest.mark.unit
def test_cluster_by_kind(gv, graph):
    gv.from_typed_graph(graph)
    result = gv.cluster_by_kind()
    assert result is gv


@pytest.mark.unit
def test_get_clusters(gv, graph):
    gv.from_typed_graph(graph).cluster_by_kind()
    clusters = gv.get_clusters()
    assert isinstance(clusters, dict)


@pytest.mark.unit
def test_filter_by_edge_type(gv, graph):
    gv.from_typed_graph(graph)
    result = gv.filter_by_edge_type("CALLS")
    assert result is gv


@pytest.mark.unit
def test_to_d3_json_returns_dict(gv, graph):
    gv.from_typed_graph(graph)
    d = gv.to_d3_json()
    assert isinstance(d, dict)
    assert "nodes" in d and "links" in d


@pytest.mark.unit
def test_render_html_creates_file(gv, graph, tmp_path):
    gv.from_typed_graph(graph)
    out = str(tmp_path / "graph.html")
    result = gv.render_html(out)
    assert result == out
    assert os.path.exists(out)


@pytest.mark.unit
def test_render_html_content_not_empty(gv, graph, tmp_path):
    gv.from_typed_graph(graph)
    out = str(tmp_path / "graph2.html")
    gv.render_html(out)
    content = open(out).read()
    assert len(content) > 50


@pytest.mark.unit
def test_render_svg_creates_file(gv, graph, tmp_path):
    gv.from_typed_graph(graph)
    out = str(tmp_path / "graph.svg")
    result = gv.render_svg(out)
    assert result == out
    assert os.path.exists(out)


@pytest.mark.unit
def test_from_program_graph_empty_dict(gv):
    result = gv.from_program_graph({"nodes": [], "edges": []})
    assert result is gv
