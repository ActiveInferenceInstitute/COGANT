"""Unit tests for viz/boundary.py — BoundaryMapper."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import pytest
from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph, GraphMetadata
from cogant.viz.boundary import BoundaryMapper


def _graph_with_modules() -> ProgramGraph:
    b = ProgramGraphBuilder(repo_uri="test://boundary")
    mod_a = b.add_node(kind=NodeKind.MODULE, name="mod_a", qualified_name="mod_a")
    mod_b = b.add_node(kind=NodeKind.MODULE, name="mod_b", qualified_name="mod_b")
    cls_a = b.add_node(kind=NodeKind.CLASS, name="ClassA", qualified_name="mod_a.ClassA")
    fn_b = b.add_node(kind=NodeKind.FUNCTION, name="func_b", qualified_name="mod_b.func_b")
    b.add_edge(source_id=mod_a.id, target_id=cls_a.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=mod_b.id, target_id=fn_b.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=mod_a.id, target_id=mod_b.id, kind=EdgeKind.IMPORTS)
    return b.finalize()


@pytest.fixture
def bm():
    return BoundaryMapper()


@pytest.fixture
def graph():
    return _graph_with_modules()


@pytest.mark.unit
def test_map_module_boundaries_returns_str(bm, graph):
    result = bm.map_module_boundaries(graph)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.unit
def test_map_module_boundaries_empty_graph(bm):
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="empty"))
    result = bm.map_module_boundaries(g)
    assert isinstance(result, str)


@pytest.mark.unit
def test_map_type_boundaries_returns_str(bm, graph):
    result = bm.map_type_boundaries(graph)
    assert isinstance(result, str)


@pytest.mark.unit
def test_map_type_boundaries_empty(bm):
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="empty"))
    result = bm.map_type_boundaries(g)
    assert isinstance(result, str)


@pytest.mark.unit
def test_generate_boundary_report_returns_dict(bm, graph):
    report = bm.generate_boundary_report(graph)
    assert isinstance(report, dict)


@pytest.mark.unit
def test_generate_boundary_report_empty(bm):
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="empty"))
    report = bm.generate_boundary_report(g)
    assert isinstance(report, dict)


@pytest.mark.unit
def test_boundary_mapper_init():
    bm = BoundaryMapper()
    assert bm is not None
