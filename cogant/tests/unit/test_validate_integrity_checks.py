"""Behavioral tests for cogant.validate.integrity.IntegrityChecker.

Drive the integrity checker through real ProgramGraph / StateSpaceModel /
ProcessModel fixtures designed to trigger each branch: dangling edges,
orphaned nodes, cycles, duplicate IDs, dangling variable references, and
invalid entry/exit stages.
"""

from __future__ import annotations

from cogant.process.extractor import ProcessConnection, ProcessModel, Stage
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import (
    Action,
    Preference,
    StateSpaceModel,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType
from cogant.validate.integrity import IntegrityChecker

# ------------------------------ builders --------------------------------- #


def _node(nid: str, name: str = "node") -> Node:
    return Node(
        id=nid,
        kind=NodeKind.FUNCTION,
        name=name,
        qualified_name=f"pkg.{name}",
        path="pkg/file.py",
    )


def _edge(eid: str, src: str, tgt: str, kind: EdgeKind = EdgeKind.CALLS) -> Edge:
    return Edge(id=eid, source_id=src, target_id=tgt, kind=kind)


def _empty_space() -> StateSpaceModel:
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


# ------------------------------ program graph ---------------------------- #


def test_clean_graph_is_valid():
    """A well-formed linear graph has no integrity issues."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge(_edge("e1", "a", "b"))

    checker = IntegrityChecker()
    issues = checker.check_program_graph(graph)

    # No errors (orphans might be info/warning but errors are the gate)
    assert checker.is_valid()
    # Only allowed severities
    assert all(i.severity in {"error", "warning", "info"} for i in issues)


def test_dangling_edge_endpoints_are_errors():
    """Edges whose endpoints are missing from the node set raise errors."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph.add_node(_node("a"))
    # Insert directly — add_edge would drop the edge for missing target.
    graph.edges["e1"] = _edge("e1", "a", "ghost")

    issues = IntegrityChecker().check_program_graph(graph)
    errors = [i for i in issues if i.severity == "error"]

    assert any("target not in nodes" in e.message for e in errors)


def test_orphaned_node_is_flagged_as_warning():
    """A node not reachable from any entry point is a warning."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_node(_node("orphan"))
    graph.add_edge(_edge("e1", "a", "b"))
    # orphan has no incoming OR outgoing from other nodes — but it is its own
    # entry point (no incoming), so the BFS will reach it from itself. To make
    # it genuinely unreachable we add an inbound edge so it is neither an
    # entry point nor reachable from any entry point.
    graph.add_edge(_edge("e2", "orphan", "orphan"))  # self-loop only

    issues = IntegrityChecker().check_program_graph(graph)
    warnings = [i for i in issues if i.severity == "warning"]
    # The self-loop makes 'orphan' have an incoming edge (itself) so it is
    # not an entry point, and nothing else reaches it → unreachable.
    assert any("Unreachable node" in w.message and "orphan" in w.message for w in warnings)


def test_cycle_detection_emits_info_issue():
    """A cycle in the graph emits an info-severity integrity issue."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_node(_node("c"))
    graph.add_edge(_edge("e1", "a", "b"))
    graph.add_edge(_edge("e2", "b", "c"))
    graph.add_edge(_edge("e3", "c", "a"))  # back edge

    issues = IntegrityChecker().check_program_graph(graph)
    info = [i for i in issues if i.severity == "info"]
    assert any("Cycle detected" in i.message for i in info)


# ------------------------------ state space ------------------------------ #


def test_state_space_clean_passes_integrity():
    """Empty state space is valid."""
    checker = IntegrityChecker()
    issues = checker.check_state_space(_empty_space())
    assert checker.is_valid()
    assert issues == []


def test_state_space_action_with_dangling_effect_is_error():
    """Action.effects referencing a missing variable → error."""
    space = _empty_space()
    space.variables["v1"] = StateVariable(
        id="v1", name="v1", var_type=StateVariableType.BOOLEAN, node_id="n1"
    )
    space.actions["a1"] = Action(
        id="a1",
        name="a1",
        controller_id="ctrl",
        effects=["v_missing"],
    )

    issues = IntegrityChecker().check_state_space(space)
    errors = [i for i in issues if i.severity == "error"]

    assert any(
        "references non-existent variable" in e.message and "v_missing" in e.message for e in errors
    )


def test_state_space_preference_with_dangling_scope_is_error():
    """Preference.scope referencing a missing variable → error."""
    space = _empty_space()
    space.variables["v1"] = StateVariable(
        id="v1", name="v1", var_type=StateVariableType.BOOLEAN, node_id="n1"
    )
    space.preferences["p1"] = Preference(
        id="p1",
        name="p1",
        description="",
        scope=["v1", "ghost"],
        expression="",
    )

    issues = IntegrityChecker().check_state_space(space)
    errors = [i for i in issues if i.severity == "error"]
    assert any("Preference p1 references non-existent variable" in e.message for e in errors)


# ------------------------------ process model ---------------------------- #


def test_process_model_clean_integrity():
    """Minimal well-formed process model has no errors."""
    stage = Stage(id="s1", name="Start")
    pm = ProcessModel(
        id="pm",
        schema_name="x",
        stages={"s1": stage},
        connections={},
        entry_stage_id="s1",
        exit_stage_ids=["s1"],
    )
    checker = IntegrityChecker()
    issues = checker.check_process_model(pm)
    assert checker.is_valid()
    assert issues == []


def test_process_model_connection_dangling_endpoint_is_error():
    """Connection referencing an unknown stage → error."""
    stage = Stage(id="s1", name="Start")
    conn = ProcessConnection(id="c1", source_stage_id="s1", target_stage_id="ghost")
    pm = ProcessModel(
        id="pm",
        schema_name="x",
        stages={"s1": stage},
        connections={"c1": conn},
    )
    issues = IntegrityChecker().check_process_model(pm)
    errors = [i for i in issues if i.severity == "error"]
    assert any("target not in stages" in e.message for e in errors)


def test_process_model_invalid_entry_and_exit_stages_are_errors():
    """entry_stage_id / exit_stage_ids not in stages → errors."""
    stage = Stage(id="s1", name="Start")
    pm = ProcessModel(
        id="pm",
        schema_name="x",
        stages={"s1": stage},
        connections={},
        entry_stage_id="ghost_entry",
        exit_stage_ids=["ghost_exit"],
    )
    issues = IntegrityChecker().check_process_model(pm)
    errors = [i for i in issues if i.severity == "error"]
    assert any("Entry stage not in stages" in e.message for e in errors)
    assert any("Exit stage not in stages" in e.message for e in errors)
