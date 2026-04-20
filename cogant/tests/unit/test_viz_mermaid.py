"""Unit tests for viz/mermaid.py — MermaidGenerator."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import pytest
from cogant.viz.mermaid import MermaidGenerator
from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph, GraphMetadata


def _graph() -> ProgramGraph:
    b = ProgramGraphBuilder(repo_uri="test://mermaid")
    mod = b.add_node(kind=NodeKind.MODULE, name="mymod", qualified_name="mymod")
    cls = b.add_node(kind=NodeKind.CLASS, name="MyClass", qualified_name="mymod.MyClass")
    fn_a = b.add_node(kind=NodeKind.METHOD, name="run", qualified_name="mymod.MyClass.run")
    fn_b = b.add_node(kind=NodeKind.FUNCTION, name="helper", qualified_name="mymod.helper")
    b.add_edge(source_id=mod.id, target_id=cls.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=cls.id, target_id=fn_a.id, kind=EdgeKind.CONTAINS)
    b.add_edge(source_id=fn_a.id, target_id=fn_b.id, kind=EdgeKind.CALLS)
    b.add_edge(source_id=mod.id, target_id=fn_b.id, kind=EdgeKind.IMPORTS)
    return b.finalize()


def _state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime
    return StateSpaceModel(
        id="ss:mermaid",
        schema_name="mermaid_test",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
        metadata={},
    )


@pytest.fixture
def mg():
    return MermaidGenerator()


@pytest.fixture
def graph():
    return _graph()


@pytest.mark.unit
def test_init():
    assert MermaidGenerator() is not None


@pytest.mark.unit
def test_generate_class_diagram_returns_str(mg, graph):
    result = mg.generate_class_diagram(graph)
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.unit
def test_generate_class_diagram_empty(mg):
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="empty"))
    result = mg.generate_class_diagram(g)
    assert isinstance(result, str)


@pytest.mark.unit
def test_generate_dependency_graph_returns_str(mg, graph):
    result = mg.generate_dependency_graph(graph)
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.unit
def test_generate_dependency_graph_empty(mg):
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="empty"))
    result = mg.generate_dependency_graph(g)
    assert isinstance(result, str)


@pytest.mark.unit
def test_generate_state_diagram_returns_str(mg):
    result = mg.generate_state_diagram(_state_space())
    assert isinstance(result, str)


@pytest.mark.unit
def test_generate_sequence_diagram_with_graph(mg, graph):
    result = mg.generate_sequence_diagram(graph=graph)
    assert isinstance(result, str)


@pytest.mark.unit
def test_generate_sequence_diagram_no_args(mg):
    result = mg.generate_sequence_diagram()
    assert isinstance(result, str)


@pytest.mark.unit
def test_generate_active_inference_diagram(mg):
    result = mg.generate_active_inference_diagram(_state_space())
    assert isinstance(result, str)


@pytest.mark.unit
def test_generate_flowchart_returns_str(mg, graph):
    mappings = {"sv1": {"kind": "HIDDEN_STATE", "confidence": 0.9}}
    result = mg.generate_flowchart(graph, mappings)
    assert isinstance(result, str)


@pytest.mark.unit
def test_generate_all_returns_dict(mg, graph):
    d = mg.generate_all(graph)
    assert isinstance(d, dict)
    assert len(d) > 0


@pytest.mark.unit
def test_generate_all_with_state_space(mg, graph):
    d = mg.generate_all(graph, state_space=_state_space())
    assert isinstance(d, dict)


@pytest.mark.unit
def test_render_active_inference_diagram(mg):
    result = mg.render_active_inference_diagram(_state_space())
    assert isinstance(result, str)


@pytest.mark.unit
def test_render_rule_firing_trace_empty(mg):
    result = mg.render_rule_firing_trace([])
    assert isinstance(result, str)


@pytest.mark.unit
def test_render_markov_blanket_dict(mg):
    blanket = {"internal": ["a", "b"], "sensory": ["c"], "active": ["d"], "external": ["e"]}
    result = mg.render_markov_blanket(blanket)
    assert isinstance(result, str)
