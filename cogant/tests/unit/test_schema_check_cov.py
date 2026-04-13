"""Behavioral tests for cogant.validate.schema_check.SchemaValidator.

Tests exercise the public validator entry points with real ProgramGraph,
StateSpaceModel, and ProcessModel instances — no mocks. Each test drives
the validator into a specific code path and asserts on the concrete
ValidationIssue objects it produces.
"""

from __future__ import annotations

import pytest

from cogant.process.extractor import ProcessConnection, ProcessModel, Stage
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import (
    Action,
    ObservationModality,
    StateSpaceModel,
    Transition,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import ConfidenceLevel, StateVariable, StateVariableType
from cogant.validate.schema_check import SchemaValidator, ValidationIssue


# ---------------------------- helpers / builders -------------------------- #


def _make_node(
    node_id: str,
    *,
    name: str | None = "my_node",
    qname: str | None = "pkg.my_node",
    kind: NodeKind = NodeKind.FUNCTION,
) -> Node:
    return Node(
        id=node_id,
        kind=kind,
        name=name or "",
        qualified_name=qname or "",
        path="pkg/file.py",
    )


def _make_edge(
    edge_id: str,
    source_id: str,
    target_id: str,
    *,
    kind: EdgeKind = EdgeKind.CALLS,
    weight: float = 1.0,
) -> Edge:
    return Edge(
        id=edge_id,
        source_id=source_id,
        target_id=target_id,
        kind=kind,
        weight=weight,
    )


def _empty_state_space(schema: str = "test") -> StateSpaceModel:
    return StateSpaceModel(
        id=f"model_{schema}",
        schema_name=schema,
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


# ---------------------------- program graph path -------------------------- #


def test_validate_empty_program_graph_has_no_issues():
    """An empty graph with valid metadata produces zero issues."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/repo"))
    validator = SchemaValidator()

    issues = validator.validate_program_graph(graph)

    assert issues == []
    assert validator.is_valid()
    assert validator.get_errors() == []
    assert validator.get_warnings() == []


def test_validate_program_graph_flags_node_missing_name_and_qname():
    """Nodes with blank name / qualified_name produce warnings."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/repo"))
    graph.add_node(_make_node("n1", name="", qname=""))

    issues = SchemaValidator().validate_program_graph(graph)

    assert any(i.severity == "warning" and "missing name" in i.message for i in issues)
    assert any(
        i.severity == "warning" and "missing qualified_name" in i.message for i in issues
    )
    assert all(i.category == "schema" for i in issues)


def test_validate_program_graph_flags_dangling_edge_endpoints():
    """Edge referencing a non-existent node is an integrity error."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/repo"))
    a = _make_node("a")
    graph.add_node(a)
    # Insert the edge directly so add_edge's own existence check doesn't drop it.
    graph.edges["e1"] = _make_edge("e1", "a", "ghost")

    validator = SchemaValidator()
    issues = validator.validate_program_graph(graph)

    errors = validator.get_errors()
    assert any("non-existent target" in e.message for e in errors)
    assert all(i.id.startswith("issue_") for i in issues)
    assert not validator.is_valid()


def test_validate_program_graph_flags_missing_edge_ids_and_negative_weight():
    """Empty source_id/target_id/id and negative weight all raise issues."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/repo"))
    graph.add_node(_make_node("a"))
    graph.add_node(_make_node("b"))

    # Edge with empty source_id, missing id, and negative weight
    graph.edges["bad"] = Edge(
        id="",
        source_id="",
        target_id="b",
        kind=EdgeKind.CALLS,
        weight=-0.5,
    )

    validator = SchemaValidator()
    issues = validator.validate_program_graph(graph)

    messages = [i.message for i in issues]
    assert any("Edge missing id" in m for m in messages)
    assert any("missing source_id" in m for m in messages)
    assert any("negative weight" in m for m in messages)


def test_validate_graph_metadata_warns_on_missing_repo_uri():
    """Blank repo_uri yields a metadata warning."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri=""))

    issues = SchemaValidator().validate_program_graph(graph)

    assert any(
        i.severity == "warning" and "repo_uri" in i.message and i.affected_ids == []
        for i in issues
    )


# ---------------------------- state space path ---------------------------- #


def test_validate_state_space_empty_is_clean():
    """Empty state space validates cleanly."""
    validator = SchemaValidator()
    issues = validator.validate_state_space(_empty_state_space())
    assert issues == []
    assert validator.is_valid()


def test_validate_state_space_flags_missing_variable_and_observation_names():
    """StateVariable / ObservationModality with blank name → warning."""
    space = _empty_state_space()
    space.variables["v1"] = StateVariable(
        id="v1",
        name="",  # missing name
        var_type=StateVariableType.BOOLEAN,
        node_id="node1",
    )
    space.observations["o1"] = ObservationModality(
        id="o1",
        name="",  # missing name
        source_node_id="node1",
        modality_type="sensor",
    )

    issues = SchemaValidator().validate_state_space(space)

    assert any("State variable v1 missing name" in i.message for i in issues)
    assert any("Observation o1 missing name" in i.message for i in issues)


def test_validate_state_space_flags_actions_and_transitions_missing_ids():
    """Action with empty id → error; transition with empty id → error."""
    space = _empty_state_space()
    # Dataclass forbids empty id via default, so we construct then clear.
    action = Action(id="aX", name="", controller_id="ctrl")
    action.id = ""
    space.actions["aX"] = action

    trans = Transition(id="tX", source_state={}, target_state={})
    trans.id = ""
    space.transitions["tX"] = trans

    validator = SchemaValidator()
    issues = validator.validate_state_space(space)
    errors = validator.get_errors()

    assert any("Action missing id" in e.message for e in errors)
    assert any("Transition missing id" in e.message for e in errors)
    # Missing action name is a warning, not an error
    assert any("missing name" in i.message for i in issues if i.severity == "warning")


# ---------------------------- process model path -------------------------- #


def test_validate_process_model_empty_is_clean():
    """Empty process model validates cleanly."""
    pm = ProcessModel(
        id="process_test",
        schema_name="test",
        stages={},
        connections={},
    )
    assert SchemaValidator().validate_process_model(pm) == []


def test_validate_process_model_flags_stage_and_connection_problems():
    """Missing stage name → warning; dangling connection endpoints → errors."""
    stage_good = Stage(id="s1", name="Start")
    stage_noname = Stage(id="s2", name="")

    conn_dangling = ProcessConnection(
        id="c1",
        source_stage_id="s1",
        target_stage_id="ghost_stage",  # not in stages
    )

    pm = ProcessModel(
        id="process_test",
        schema_name="test",
        stages={"s1": stage_good, "s2": stage_noname},
        connections={"c1": conn_dangling},
    )

    validator = SchemaValidator()
    issues = validator.validate_process_model(pm)
    errors = validator.get_errors()

    assert any("Stage s2 missing name" in i.message for i in issues if i.severity == "warning")
    assert any("non-existent target stage" in e.message for e in errors)


def test_validate_process_model_flags_empty_stage_and_connection_ids():
    """Blank stage.id and connection.id → errors."""
    bad_stage = Stage(id="s1", name="Start")
    bad_stage.id = ""
    bad_conn = ProcessConnection(id="c1", source_stage_id="", target_stage_id="")
    bad_conn.id = ""

    pm = ProcessModel(
        id="process_test",
        schema_name="test",
        stages={"s1": bad_stage},
        connections={"c1": bad_conn},
    )

    errors = [i for i in SchemaValidator().validate_process_model(pm) if i.severity == "error"]
    messages = [e.message for e in errors]
    assert any("Stage missing id" in m for m in messages)
    assert any("Connection missing id" in m for m in messages)


# ---------------------------- issue bookkeeping --------------------------- #


def test_get_errors_and_warnings_partition_issues():
    """get_errors / get_warnings filter by severity, is_valid reflects errors only."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/repo"))
    # Warning: empty name
    graph.add_node(_make_node("a", name=""))
    # Error: dangling edge target
    graph.add_node(_make_node("b"))
    graph.edges["e"] = _make_edge("e", "a", "ghost")

    validator = SchemaValidator()
    validator.validate_program_graph(graph)

    errors = validator.get_errors()
    warnings = validator.get_warnings()

    assert all(e.severity == "error" for e in errors)
    assert all(w.severity == "warning" for w in warnings)
    assert len(errors) + len(warnings) <= len(validator.get_issues())
    assert validator.is_valid() is False


def test_validate_program_graph_resets_issues_between_runs():
    """Calling validate_program_graph twice discards the previous run's issues."""
    graph_dirty = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/repo"))
    graph_dirty.add_node(_make_node("a", name=""))

    graph_clean = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/repo"))
    graph_clean.add_node(_make_node("a"))

    validator = SchemaValidator()
    assert validator.validate_program_graph(graph_dirty) != []
    assert validator.validate_program_graph(graph_clean) == []
