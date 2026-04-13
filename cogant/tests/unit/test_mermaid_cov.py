"""Behavioral tests for cogant.viz.mermaid.MermaidGenerator.

Tests feed real ProgramGraph / StateSpaceModel / ProcessModel fixtures
to every public generator on MermaidGenerator and assert on structural
properties of the produced Mermaid syntax.
"""

from __future__ import annotations

from cogant.process.extractor import ProcessConnection, ProcessModel, Stage
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.compiler import (
    Action,
    ObservationModality,
    StateSpaceModel,
    Transition,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import ConfidenceLevel, StateVariable, StateVariableType
from cogant.viz.mermaid import MermaidGenerator


# ---------------------------- builders ----------------------------------- #


def _node(nid: str, kind: NodeKind, name: str | None = None, **meta) -> Node:
    n = Node(
        id=nid,
        kind=kind,
        name=name or nid,
        qualified_name=f"pkg.{name or nid}",
        path="pkg/file.py",
    )
    if meta:
        n.metadata.update(meta)
    return n


def _edge(eid: str, src: str, tgt: str, kind: EdgeKind) -> Edge:
    return Edge(id=eid, source_id=src, target_id=tgt, kind=kind)


def _class_graph_with_methods() -> ProgramGraph:
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    # Controller class with public + private methods. Pass a metadata kv so
    # the stereotype inference short-circuit (empty metadata) is bypassed.
    g.add_node(_node("cls_api", NodeKind.CLASS, name="UserController", kind_hint="api"))
    g.add_node(
        _node(
            "mtd_pub",
            NodeKind.METHOD,
            name="get_user",
            parameters=["user_id"],
            return_type="User",
        )
    )
    g.add_node(_node("mtd_priv", NodeKind.METHOD, name="_validate"))
    # Model class
    g.add_node(_node("cls_model", NodeKind.CLASS, name="UserModel"))
    g.add_node(_node("cls_base", NodeKind.CLASS, name="BaseModel"))

    # Containment
    g.add_edge(_edge("e1", "cls_api", "mtd_pub", EdgeKind.CONTAINS))
    g.add_edge(_edge("e2", "cls_api", "mtd_priv", EdgeKind.CONTAINS))
    # Inheritance
    g.add_edge(_edge("e3", "cls_model", "cls_base", EdgeKind.INHERITS))
    return g


def _space_with_data() -> StateSpaceModel:
    space = StateSpaceModel(
        id="m",
        schema_name="m",
        variables={
            "v1": StateVariable(
                id="v1",
                name="open",
                var_type=StateVariableType.BOOLEAN,
                node_id="n1",
                description="Is the valve open",
            ),
            "v2": StateVariable(
                id="v2",
                name="level",
                var_type=StateVariableType.DISCRETE,
                node_id="n2",
            ),
        },
        observations={
            "o1": ObservationModality(
                id="o1", name="reading", source_node_id="n1", modality_type="sensor"
            )
        },
        actions={
            "a1": Action(id="a1", name="open_valve", controller_id="ctrl1"),
        },
        transitions={
            "t1": Transition(
                id="t1",
                source_state={"v1": "pre"},
                target_state={"v1": "post"},
                action_id="a1",
            )
        },
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )
    return space


# ---------------------------- class diagram ------------------------------ #


def test_class_diagram_header_and_class_names():
    """generate_class_diagram starts with classDiagram and lists every class."""
    gen = MermaidGenerator()
    out = gen.generate_class_diagram(_class_graph_with_methods())

    assert out.startswith("classDiagram")
    assert "UserController" in out
    assert "UserModel" in out
    assert "BaseModel" in out


def test_class_diagram_emits_visibility_and_signatures_and_stereotype():
    """Methods appear with visibility markers; controllers get a stereotype."""
    out = MermaidGenerator().generate_class_diagram(_class_graph_with_methods())

    # Public method signature with parameters and return type
    assert "+get_user(user_id): User" in out
    # Protected/underscore private method
    assert "#_validate()" in out
    # Controller stereotype
    assert "<<controller>>" in out
    # Inheritance arrow
    assert "UserModel --|> BaseModel" in out


def test_class_diagram_empty_graph_only_header():
    """Empty graph yields just the header line."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    out = MermaidGenerator().generate_class_diagram(g)
    assert out.strip() == "classDiagram"


# ---------------------------- dependency graph --------------------------- #


def test_dependency_graph_contains_modules_and_edges():
    """generate_dependency_graph wraps modules in subgraphs and emits edges."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    g.add_node(_node("m1", NodeKind.MODULE, name="services"))
    g.add_node(_node("c1", NodeKind.CLASS, name="OrderService"))
    g.add_node(_node("f1", NodeKind.FUNCTION, name="compute"))
    g.add_edge(_edge("e1", "m1", "c1", EdgeKind.CONTAINS))
    g.add_edge(_edge("e2", "c1", "f1", EdgeKind.CALLS))

    out = MermaidGenerator().generate_dependency_graph(g)

    assert out.startswith("graph TD")
    assert "subgraph" in out
    assert "services" in out
    # CALLS edge label
    assert "calls" in out


# ---------------------------- state diagram ------------------------------ #


def test_state_diagram_contains_transitions_and_notes():
    """generate_state_diagram includes states, notes, and transition labels."""
    out = MermaidGenerator().generate_state_diagram(_space_with_data())

    assert out.startswith("stateDiagram-v2")
    assert "open" in out  # variable name
    assert "level" in out
    # Note block for variable with description
    assert "note right of" in out
    # Transition label mentions the action id (literal id, not the name)
    assert "--> v1=post: a1" in out


def test_state_diagram_empty_model_header_only():
    """Empty state space yields only the stateDiagram-v2 header."""
    space = StateSpaceModel(
        id="m",
        schema_name="m",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )
    out = MermaidGenerator().generate_state_diagram(space)
    assert out.strip() == "stateDiagram-v2"


# ---------------------------- sequence diagram --------------------------- #


def test_sequence_diagram_from_process_model():
    """Process model with stages produces participants and messages."""
    pm = ProcessModel(
        id="pm",
        schema_name="x",
        stages={
            "ingest": Stage(id="ingest", name="Ingest"),
            "process": Stage(id="process", name="Process"),
        },
        connections={
            "c1": ProcessConnection(
                id="c1", source_stage_id="ingest", target_stage_id="process", trigger="next"
            )
        },
    )
    out = MermaidGenerator().generate_sequence_diagram(pm)
    assert out.startswith("sequenceDiagram")
    assert "participant ingest" in out
    assert "participant process" in out
    assert "ingest->>+process" in out


def test_sequence_diagram_from_program_graph_calls():
    """Program graph with CALLS edges produces sequence interactions."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    g.add_node(_node("a", NodeKind.FUNCTION, name="caller"))
    g.add_node(_node("b", NodeKind.FUNCTION, name="callee"))
    g.add_edge(_edge("e1", "a", "b", EdgeKind.CALLS))

    out = MermaidGenerator().generate_sequence_diagram(graph=g)
    assert out.startswith("sequenceDiagram")
    assert "participant" in out
    assert "caller" in out or "callee" in out


def test_sequence_diagram_graph_without_calls_emits_placeholder():
    """Graph with no CALLS edges produces the 'No call edges' placeholder."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    g.add_node(_node("a", NodeKind.FUNCTION, name="f"))
    out = MermaidGenerator().generate_sequence_diagram(graph=g)
    assert "No call edges found" in out


# ---------------------------- active inference --------------------------- #


def test_active_inference_diagram_has_loop_and_states():
    """The Active Inference diagram always renders the core loop edges."""
    out = MermaidGenerator().generate_active_inference_diagram(_space_with_data())
    assert out.startswith("graph TD")
    # Loop edges with labels
    assert "HS" in out
    assert "OBS" in out
    assert "BELIEFS" in out
    assert "ACTIONS" in out
    assert "Likelihood" in out
    assert "Inference" in out
    assert "Policy" in out
    assert "Transition" in out


# ---------------------------- flowchart ---------------------------------- #


def test_flowchart_emits_role_boxes_and_source_nodes():
    """generate_flowchart emits a role box and edges from source nodes."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    g.add_node(_node("src1", NodeKind.FUNCTION, name="read_sensor"))
    mappings = {
        "m1": SemanticMapping(
            id="m1",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=["src1"],
            semantic_label="sensor_reading",
        )
    }
    out = MermaidGenerator().generate_flowchart(g, mappings)

    assert out.startswith("flowchart TD")
    assert "OBSERVATION" in out
    assert "read_sensor" in out
    assert "sensor_reading" in out


# ---------------------------- generate_all ------------------------------- #


def test_generate_all_returns_expected_keys():
    """generate_all includes class/dep/sequence always; state keys only with space."""
    gen = MermaidGenerator()
    g = _class_graph_with_methods()
    space = _space_with_data()

    result = gen.generate_all(graph=g, state_space=space)

    assert "class_diagram" in result
    assert "dependency_graph" in result
    assert "sequence_diagram" in result
    assert "state_diagram" in result
    assert "active_inference_diagram" in result
    # All values are non-empty mermaid strings
    for value in result.values():
        assert isinstance(value, str)
        assert len(value) > 0


def test_generate_all_without_state_space_omits_state_diagrams():
    """When no state_space is passed, state-related keys are absent."""
    gen = MermaidGenerator()
    result = gen.generate_all(graph=_class_graph_with_methods())
    assert "state_diagram" not in result
    assert "active_inference_diagram" not in result
