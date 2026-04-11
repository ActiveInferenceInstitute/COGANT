"""Unit tests for :class:`cogant.validate.integrity.IntegrityChecker`.

These tests exercise the real ``IntegrityChecker`` against genuine
``ProgramGraph``, ``StateSpaceModel``, and ``ProcessModel`` instances
built on the fly. Every assertion touches a concrete cogant class —
no dict-literal reports are used.
"""

from __future__ import annotations

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.process.extractor import (
    ProcessConnection,
    ProcessModel,
    Stage,
)
from cogant.schemas.core import Edge, EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import (
    Action,
    StateSpaceModel,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)
from cogant.validate.integrity import IntegrityChecker
from cogant.validate.schema_check import ValidationIssue

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def connected_graph() -> ProgramGraph:
    """Build a linear module -> class -> function graph with valid edges."""
    b = ProgramGraphBuilder(repo_uri="test://validation")
    module = b.add_node(
        kind=NodeKind.MODULE,
        name="mod",
        qualified_name="mod",
        path="mod.py",
        language="python",
    )
    cls = b.add_node(
        kind=NodeKind.CLASS,
        name="C",
        qualified_name="mod.C",
        path="mod.py",
        language="python",
    )
    fn = b.add_node(
        kind=NodeKind.FUNCTION,
        name="f",
        qualified_name="mod.C.f",
        path="mod.py",
        language="python",
    )
    b.add_edge(module.id, cls.id, EdgeKind.CONTAINS)
    b.add_edge(cls.id, fn.id, EdgeKind.CONTAINS)
    return b.finalize()


@pytest.fixture
def graph_with_dangling_edge(connected_graph: ProgramGraph) -> ProgramGraph:
    """Inject an edge whose target points to a nonexistent node."""
    # Grab any valid source
    src_id = next(iter(connected_graph.nodes))
    bogus_edge = Edge(
        id="edge:dangling",
        source_id=src_id,
        target_id="ghost_target",  # does not exist
        kind=EdgeKind.CALLS,
    )
    # Bypass builder validation — directly mutate the graph
    connected_graph.edges["edge:dangling"] = bogus_edge
    return connected_graph


@pytest.fixture
def state_space_with_bad_action_reference() -> StateSpaceModel:
    """A StateSpaceModel whose action references a missing variable."""
    var = StateVariable(
        id="var:counter",
        name="counter",
        var_type=StateVariableType.DISCRETE,
        node_id="n1",
        cardinality=5,
        confidence=ConfidenceLevel.HIGH,
    )
    bad_action = Action(
        id="act:bogus",
        name="bogus",
        controller_id="ctrl1",
        effects=["var:nonexistent"],  # dangling
    )
    return StateSpaceModel(
        id="ss:test",
        schema_name="test",
        variables={var.id: var},
        observations={},
        actions={bad_action.id: bad_action},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


@pytest.fixture
def clean_state_space() -> StateSpaceModel:
    """A StateSpaceModel with consistent variable references."""
    var = StateVariable(
        id="var:x",
        name="x",
        var_type=StateVariableType.BOOLEAN,
        node_id="n1",
        cardinality=2,
    )
    return StateSpaceModel(
        id="ss:clean",
        schema_name="clean",
        variables={var.id: var},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


@pytest.fixture
def process_model_valid() -> ProcessModel:
    """A valid ProcessModel with consistent stage references."""
    s1 = Stage(id="stage:a", name="A", node_ids=["n1"])
    s2 = Stage(id="stage:b", name="B", node_ids=["n2"])
    conn = ProcessConnection(
        id="conn:1",
        source_stage_id="stage:a",
        target_stage_id="stage:b",
        trigger="done",
    )
    return ProcessModel(
        id="proc:valid",
        schema_name="valid",
        stages={s1.id: s1, s2.id: s2},
        connections={conn.id: conn},
        entry_stage_id="stage:a",
        exit_stage_ids=["stage:b"],
    )


@pytest.fixture
def process_model_dangling() -> ProcessModel:
    """A ProcessModel whose entry/exit points at a missing stage."""
    s1 = Stage(id="stage:only", name="only")
    return ProcessModel(
        id="proc:dangling",
        schema_name="dangling",
        stages={s1.id: s1},
        connections={},
        entry_stage_id="stage:missing",  # dangling
        exit_stage_ids=["stage:also_missing"],
    )


# -------------------------------------------------------- construction


class TestIntegrityCheckerConstruction:
    """Tests for IntegrityChecker construction."""

    def test_constructs_with_empty_issues(self) -> None:
        checker = IntegrityChecker()
        assert checker.issues == []
        assert checker.is_valid() is True


# -------------------------------------------------- program graph checks


class TestProgramGraphIntegrity:
    """Tests for :meth:`check_program_graph`."""

    def test_clean_graph_has_no_error_issues(
        self, connected_graph: ProgramGraph
    ) -> None:
        checker = IntegrityChecker()
        issues = checker.check_program_graph(connected_graph)
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []

    def test_dangling_edge_target_reports_error(
        self, graph_with_dangling_edge: ProgramGraph
    ) -> None:
        checker = IntegrityChecker()
        issues = checker.check_program_graph(graph_with_dangling_edge)
        # At least one error about the missing target
        assert any(
            i.severity == "error" and "ghost_target" in i.message
            for i in issues
        )
        assert checker.is_valid() is False

    def test_issues_are_validation_issue_instances(
        self, graph_with_dangling_edge: ProgramGraph
    ) -> None:
        checker = IntegrityChecker()
        issues = checker.check_program_graph(graph_with_dangling_edge)
        for i in issues:
            assert isinstance(i, ValidationIssue)
            assert i.id
            assert i.category == "integrity"


# ---------------------------------------------------- state space checks


class TestStateSpaceIntegrity:
    """Tests for :meth:`check_state_space`."""

    def test_clean_state_space_has_no_errors(
        self, clean_state_space: StateSpaceModel
    ) -> None:
        checker = IntegrityChecker()
        issues = checker.check_state_space(clean_state_space)
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []
        assert checker.is_valid() is True

    def test_action_with_missing_variable_reports_error(
        self, state_space_with_bad_action_reference: StateSpaceModel
    ) -> None:
        checker = IntegrityChecker()
        issues = checker.check_state_space(state_space_with_bad_action_reference)
        assert any(
            i.severity == "error" and "nonexistent" in i.message
            for i in issues
        )


# ---------------------------------------------------- process model checks


class TestProcessModelIntegrity:
    """Tests for :meth:`check_process_model`."""

    def test_valid_process_model_no_errors(
        self, process_model_valid: ProcessModel
    ) -> None:
        checker = IntegrityChecker()
        issues = checker.check_process_model(process_model_valid)
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []

    def test_dangling_entry_stage_reports_error(
        self, process_model_dangling: ProcessModel
    ) -> None:
        checker = IntegrityChecker()
        issues = checker.check_process_model(process_model_dangling)
        assert any(
            i.severity == "error" and "stage:missing" in i.message
            for i in issues
        )

    def test_dangling_exit_stage_reports_error(
        self, process_model_dangling: ProcessModel
    ) -> None:
        checker = IntegrityChecker()
        issues = checker.check_process_model(process_model_dangling)
        assert any(
            i.severity == "error" and "stage:also_missing" in i.message
            for i in issues
        )


# ----------------------------------------------------- get_issues / reset


class TestCheckerStateIsolation:
    """Tests for checker state isolation across multiple runs."""

    def test_each_check_clears_issues(
        self,
        graph_with_dangling_edge: ProgramGraph,
    ) -> None:
        checker = IntegrityChecker()
        checker.check_program_graph(graph_with_dangling_edge)
        assert checker.issues  # has issues

        # Running a new check on a fresh clean graph clears previous issues
        fresh_builder = ProgramGraphBuilder(repo_uri="test://fresh")
        fresh_builder.add_node(
            kind=NodeKind.MODULE,
            name="solo",
            qualified_name="solo",
            path="solo.py",
        )
        fresh_graph = fresh_builder.finalize()
        checker.check_program_graph(fresh_graph)
        errors = [i for i in checker.issues if i.severity == "error"]
        assert errors == []
