"""Behavioral tests for cogant.validate.provenance_check.ProvenanceChecker.

Feed the checker real ProgramGraph / StateSpaceModel instances with known
coverage gaps and assert on the emitted ProvenanceGap dataclasses.
"""

from __future__ import annotations

from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import (
    Action,
    ObservationModality,
    StateSpaceModel,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType
from cogant.validate.provenance_check import ProvenanceChecker

# ---------------------------- builders ----------------------------------- #


def _node(nid: str) -> Node:
    return Node(
        id=nid,
        kind=NodeKind.FUNCTION,
        name=nid,
        qualified_name=f"pkg.{nid}",
        path="pkg/file.py",
    )


def _edge(eid: str, src: str, tgt: str) -> Edge:
    return Edge(id=eid, source_id=src, target_id=tgt, kind=EdgeKind.CALLS)


def _space() -> StateSpaceModel:
    return StateSpaceModel(
        id="model_x",
        schema_name="x",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


# ---------------------------- construction ------------------------------- #


def test_empty_checker_has_empty_state():
    """Default construction yields empty records and zero gaps."""
    checker = ProvenanceChecker()
    assert checker.provenance_records == {}
    assert checker.get_gaps() == []


def test_provided_records_are_preserved():
    """Passing records via ctor keeps them on the instance."""
    records = {"n1": ["evidence-a", "evidence-b"]}
    checker = ProvenanceChecker(provenance_records=records)
    assert checker.provenance_records == records


# ---------------------------- graph provenance --------------------------- #


def test_graph_provenance_gaps_for_unrecorded_nodes_and_edges():
    """Nodes and edges with no provenance records produce warning gaps."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge(_edge("e1", "a", "b"))

    gaps = ProvenanceChecker().check_graph_provenance(graph)

    gap_ids = {g.element_id for g in gaps}
    assert {"a", "b", "e1"}.issubset(gap_ids)
    # Correct typing per element
    types = {g.element_id: g.element_type for g in gaps}
    assert types["a"] == "node"
    assert types["e1"] == "edge"
    # All severity warnings
    assert all(g.severity == "warning" for g in gaps)


def test_graph_provenance_no_gaps_when_records_cover_all():
    """Nodes and edges with at least one record produce no gaps."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge(_edge("e1", "a", "b"))

    records = {"a": ["src"], "b": ["src"], "e1": ["src"]}
    checker = ProvenanceChecker(provenance_records=records)
    assert checker.check_graph_provenance(graph) == []


def test_graph_provenance_empty_record_list_is_gap():
    """An entry with an empty list is treated the same as no record."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph.add_node(_node("a"))

    records: dict[str, list[object]] = {"a": []}
    gaps = ProvenanceChecker(provenance_records=records).check_graph_provenance(graph)

    assert any(g.element_id == "a" and g.element_type == "node" for g in gaps)


# ---------------------------- state space provenance --------------------- #


def test_state_space_variable_gap_when_neither_var_nor_source_node_recorded():
    """Variable with no records and unrecorded source node → gap."""
    space = _space()
    space.variables["v1"] = StateVariable(
        id="v1",
        name="v1",
        var_type=StateVariableType.BOOLEAN,
        node_id="node1",
    )

    gaps = ProvenanceChecker().check_state_space_provenance(space)

    assert any(g.element_id == "v1" and g.element_type == "variable" for g in gaps)


def test_state_space_variable_no_gap_when_source_node_recorded():
    """Variable with recorded source node is not a gap, even without own records."""
    space = _space()
    space.variables["v1"] = StateVariable(
        id="v1",
        name="v1",
        var_type=StateVariableType.BOOLEAN,
        node_id="node1",
    )
    records = {"node1": ["evidence"]}
    checker = ProvenanceChecker(provenance_records=records)

    gaps = checker.check_state_space_provenance(space)
    # v1 should not produce a gap because its source node is recorded
    assert not any(g.element_id == "v1" for g in gaps)


def test_state_space_observation_and_action_gaps():
    """Observation and Action both emit gaps when unrecorded."""
    space = _space()
    space.observations["o1"] = ObservationModality(
        id="o1",
        name="obs",
        source_node_id="obs_node",
        modality_type="sensor",
    )
    space.actions["a1"] = Action(id="a1", name="act", controller_id="ctrl_node")

    gaps = ProvenanceChecker().check_state_space_provenance(space)

    assert any(g.element_id == "o1" and g.element_type == "observation" for g in gaps)
    assert any(g.element_id == "a1" and g.element_type == "action" for g in gaps)


def test_state_space_observation_no_gap_when_source_node_recorded():
    """Observation with a recorded source node is not a gap."""
    space = _space()
    space.observations["o1"] = ObservationModality(
        id="o1",
        name="obs",
        source_node_id="obs_node",
        modality_type="sensor",
    )
    checker = ProvenanceChecker(provenance_records={"obs_node": ["evidence"]})

    gaps = checker.check_state_space_provenance(space)
    assert not any(g.element_id == "o1" for g in gaps)


def test_state_space_action_no_gap_when_controller_recorded():
    """Action whose controller node is recorded is not a gap."""
    space = _space()
    space.actions["a1"] = Action(id="a1", name="act", controller_id="ctrl_node")
    checker = ProvenanceChecker(provenance_records={"ctrl_node": ["evidence"]})

    gaps = checker.check_state_space_provenance(space)
    assert not any(g.element_id == "a1" for g in gaps)


# ---------------------------- coverage percentage ------------------------ #


def test_get_coverage_percentage_empty_total_returns_100():
    """Zero elements → 100% coverage by convention."""
    assert ProvenanceChecker().get_coverage_percentage(0) == 100.0


def test_get_coverage_percentage_reflects_warnings():
    """Coverage drops proportionally to the number of warning gaps."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))

    checker = ProvenanceChecker()
    checker.check_graph_provenance(graph)

    # 2 elements, both produce gaps → 0% coverage
    assert checker.get_coverage_percentage(2) == 0.0

    # 4 elements (2 gaps + 2 covered) → 50%
    assert checker.get_coverage_percentage(4) == 50.0


# ---------------------------- merge / add -------------------------------- #


def test_merge_records_adds_new_and_extends_existing():
    """merge_records appends to existing keys and inserts new ones."""
    checker = ProvenanceChecker(provenance_records={"a": ["x"]})
    checker.merge_records({"a": ["y"], "b": ["z"]})

    assert checker.provenance_records["a"] == ["x", "y"]
    assert checker.provenance_records["b"] == ["z"]


def test_add_record_creates_list_and_appends():
    """add_record initialises missing keys and appends otherwise."""
    checker = ProvenanceChecker()
    checker.add_record("n1", "rec-1")
    checker.add_record("n1", "rec-2")
    assert checker.provenance_records["n1"] == ["rec-1", "rec-2"]


# ---------------------------- reset semantics ---------------------------- #


def test_check_graph_provenance_resets_between_runs():
    """Consecutive graph checks don't accumulate gaps from prior runs."""
    graph_dirty = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph_dirty.add_node(_node("x"))

    graph_clean = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph_clean.add_node(_node("x"))
    checker = ProvenanceChecker(provenance_records={"x": ["ev"]})

    # First, dirty graph with no records on a separate checker
    first = ProvenanceChecker().check_graph_provenance(graph_dirty)
    assert first != []

    # Second, a fresh checker with records should yield no gaps
    assert checker.check_graph_provenance(graph_clean) == []
