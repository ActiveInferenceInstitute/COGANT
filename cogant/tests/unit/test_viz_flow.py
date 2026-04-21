"""Unit tests for viz/flow.py — FlowDiagrammer (including generate_cfg real impl)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import matplotlib

matplotlib.use("Agg")
import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.viz.flow import CallGraph, ControlFlowGraph, DependencyGraph, FlowDiagrammer


def _small_graph() -> ProgramGraph:
    b = ProgramGraphBuilder(repo_uri="test://flow")
    mod = b.add_node(kind=NodeKind.MODULE, name="mymod", qualified_name="mymod")
    fn_a = b.add_node(kind=NodeKind.FUNCTION, name="main", qualified_name="mymod.main")
    fn_b = b.add_node(kind=NodeKind.FUNCTION, name="helper", qualified_name="mymod.helper")
    fn_c = b.add_node(kind=NodeKind.METHOD, name="process", qualified_name="mymod.Cls.process")
    b.add_edge(source_id=mod.id, target_id=fn_a.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=fn_a.id, target_id=fn_b.id, kind=EdgeKind.CALLS)
    b.add_edge(source_id=fn_a.id, target_id=fn_c.id, kind=EdgeKind.CALLS)
    b.add_edge(source_id=mod.id, target_id=fn_b.id, kind=EdgeKind.IMPORTS)
    return b.finalize()


@pytest.fixture
def fd():
    return FlowDiagrammer()


@pytest.fixture
def graph():
    return _small_graph()


# ── generate_cfg ──────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_generate_cfg_no_graph(fd):
    node = Node(id="fn1", kind=NodeKind.FUNCTION, name="foo", qualified_name="foo")
    cfg = fd.generate_cfg(node, graph=None)
    assert isinstance(cfg, ControlFlowGraph)
    assert cfg.entry_node_id is not None
    assert len(cfg.exit_node_ids) >= 1


@pytest.mark.unit
def test_generate_cfg_with_calls(fd, graph):
    fn_node = next(n for n in graph.nodes.values() if n.name == "main")
    cfg = fd.generate_cfg(fn_node, graph=graph)
    assert cfg.entry_node_id is not None
    assert len(cfg.exit_node_ids) >= 1
    # Should have entry + call blocks + exit
    assert len(cfg.nodes) >= 3


@pytest.mark.unit
def test_generate_cfg_has_edges(fd, graph):
    fn_node = next(n for n in graph.nodes.values() if n.name == "main")
    cfg = fd.generate_cfg(fn_node, graph=graph)
    assert len(cfg.edges) >= 1


@pytest.mark.unit
def test_generate_cfg_to_dict(fd):
    node = Node(id="fn2", kind=NodeKind.FUNCTION, name="bar", qualified_name="bar")
    cfg = fd.generate_cfg(node)
    d = cfg.to_dict()
    assert "function_id" in d
    assert "nodes" in d and "edges" in d


# ── generate_call_graph ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_generate_call_graph(fd, graph):
    cg = fd.generate_call_graph(graph)
    assert isinstance(cg, CallGraph)
    assert len(cg.nodes) >= 2  # main + helper at least


@pytest.mark.unit
def test_generate_call_graph_has_edges(fd, graph):
    cg = fd.generate_call_graph(graph)
    assert len(cg.edges) >= 1


@pytest.mark.unit
def test_generate_call_graph_entry_points(fd, graph):
    cg = fd.generate_call_graph(graph)
    assert isinstance(cg.entry_points, list)


@pytest.mark.unit
def test_generate_call_graph_empty(fd):
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="empty"))
    cg = fd.generate_call_graph(g)
    assert cg.nodes == {}
    assert cg.edges == []


@pytest.mark.unit
def test_call_graph_to_dict(fd, graph):
    cg = fd.generate_call_graph(graph)
    d = cg.to_dict()
    assert "nodes" in d and "edges" in d and "entry_points" in d


# ── generate_dependency_graph ──────────────────────────────────────────────────


@pytest.mark.unit
def test_generate_dependency_graph(fd, graph):
    dg = fd.generate_dependency_graph(graph)
    assert isinstance(dg, DependencyGraph)


@pytest.mark.unit
def test_dependency_graph_to_dict(fd, graph):
    dg = fd.generate_dependency_graph(graph)
    d = dg.to_dict()
    assert "nodes" in d and "edges" in d and "roots" in d


# ── to_mermaid_flowchart / sequence ────────────────────────────────────────────


@pytest.mark.unit
def test_to_mermaid_flowchart_no_graph_context(fd):
    node = Node(id="fn3", kind=NodeKind.FUNCTION, name="baz", qualified_name="baz")
    cfg = fd.generate_cfg(node)
    mermaid = fd.to_mermaid_flowchart(cfg)
    assert "flowchart" in mermaid.lower() or "graph" in mermaid.lower() or mermaid.strip()


@pytest.mark.unit
def test_to_mermaid_sequence_empty(fd):
    cg = CallGraph()
    seq = fd.to_mermaid_sequence(cg)
    assert isinstance(seq, str)


@pytest.mark.unit
def test_to_mermaid_sequence_with_calls(fd, graph):
    cg = fd.generate_call_graph(graph)
    seq = fd.to_mermaid_sequence(cg)
    assert isinstance(seq, str)


# ── PNG / PDF exports ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_to_png_with_cfg(fd, tmp_path):
    node = Node(id="fn4", kind=NodeKind.FUNCTION, name="qux", qualified_name="qux")
    cfg = fd.generate_cfg(node)
    out = fd.to_png(cfg, str(tmp_path / "cfg.png"))
    assert isinstance(out, str)


@pytest.mark.unit
def test_to_pdf_with_call_graph(fd, graph, tmp_path):
    cg = fd.generate_call_graph(graph)
    out = fd.to_pdf(cg, str(tmp_path / "cg.pdf"))
    assert isinstance(out, str)
