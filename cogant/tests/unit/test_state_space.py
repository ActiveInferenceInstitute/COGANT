"""Unit tests for the state-space compilation pipeline.

These tests exercise the real ``StateVariableExtractor`` and
``StateSpaceCompiler`` classes against a hand-built ``ProgramGraph`` and
genuine ``SemanticMapping`` objects. No dict-literal ``state``/``transition``
structures — every assertion touches a concrete cogant dataclass.
"""

from __future__ import annotations

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.semantic import (
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.statespace.compiler import StateSpaceCompiler, StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableExtractor,
    StateVariableType,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def graph_with_hidden_state():
    """Build a real ProgramGraph with a single class node carrying a
    ``type_hint`` metadata field so the extractor can classify it.
    """
    builder = ProgramGraphBuilder(repo_uri="test://state-space")
    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="counter_service",
        qualified_name="counter_service",
        path="counter_service.py",
        language="python",
    )
    counter_var = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="counter",
        qualified_name="counter_service.counter",
        path="counter_service.py",
        language="python",
        metadata={"type_hint": "int", "cardinality": 10},
    )
    active_flag = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="is_active",
        qualified_name="counter_service.is_active",
        path="counter_service.py",
        language="python",
        metadata={"type_hint": "bool"},
    )
    builder.add_edge(module.id, counter_var.id, EdgeKind.CONTAINS)
    builder.add_edge(module.id, active_flag.id, EdgeKind.CONTAINS)
    return builder.finalize(), counter_var.id, active_flag.id


@pytest.fixture
def hidden_state_mappings(graph_with_hidden_state):
    """Real SemanticMapping objects flagging the two hidden-state nodes."""
    _, counter_id, flag_id = graph_with_hidden_state
    m_counter = SemanticMapping(
        id="mapping:counter",
        kind=MappingKind.HIDDEN_STATE,
        graph_fragment_node_ids=[counter_id],
        semantic_label="counter",
        description="integer counter",
        confidence_score=0.85,
        provenance=[ProvenanceRecord(source="static_analysis", confidence=0.85)],
    )
    m_flag = SemanticMapping(
        id="mapping:flag",
        kind=MappingKind.HIDDEN_STATE,
        graph_fragment_node_ids=[flag_id],
        semantic_label="is_active",
        description="an active flag",
        confidence_score=0.9,
        provenance=[ProvenanceRecord(source="static_analysis", confidence=0.9)],
    )
    return {m_counter.id: m_counter, m_flag.id: m_flag}


# ---------------------------------------------------- StateVariableExtractor


class TestStateVariableExtractor:
    """Tests for :class:`StateVariableExtractor`."""

    def test_extract_empty_mappings_returns_empty(self, graph_with_hidden_state) -> None:
        graph, *_ = graph_with_hidden_state
        extractor = StateVariableExtractor(graph)
        result = extractor.extract({})
        assert result == {}

    def test_extract_ignores_non_hidden_state_mappings(self, graph_with_hidden_state) -> None:
        graph, counter_id, _ = graph_with_hidden_state
        extractor = StateVariableExtractor(graph)
        mapping = SemanticMapping(
            id="mapping:obs",
            kind=MappingKind.OBSERVATION,  # not HIDDEN_STATE
            graph_fragment_node_ids=[counter_id],
            semantic_label="counter_obs",
        )
        result = extractor.extract({mapping.id: mapping})
        assert result == {}

    def test_extract_infers_boolean_from_type_hint(
        self, graph_with_hidden_state, hidden_state_mappings
    ) -> None:
        graph, _, flag_id = graph_with_hidden_state
        extractor = StateVariableExtractor(graph)
        variables = extractor.extract(hidden_state_mappings)
        flag_var = variables[f"var_{flag_id}"]
        assert isinstance(flag_var, StateVariable)
        assert flag_var.var_type is StateVariableType.BOOLEAN
        assert flag_var.cardinality == 2
        assert flag_var.domain == [False, True]
        assert flag_var.is_discrete is True

    def test_extract_infers_discrete_from_int_type_hint(
        self, graph_with_hidden_state, hidden_state_mappings
    ) -> None:
        graph, counter_id, _ = graph_with_hidden_state
        extractor = StateVariableExtractor(graph)
        variables = extractor.extract(hidden_state_mappings)
        counter_var = variables[f"var_{counter_id}"]
        assert counter_var.var_type is StateVariableType.DISCRETE
        assert counter_var.cardinality == 10  # from metadata
        assert counter_var.name == "counter"

    def test_extract_skips_missing_node_ids(self, graph_with_hidden_state) -> None:
        graph, *_ = graph_with_hidden_state
        extractor = StateVariableExtractor(graph)
        orphan_mapping = SemanticMapping(
            id="mapping:orphan",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=["does_not_exist"],
            semantic_label="orphan",
        )
        result = extractor.extract({orphan_mapping.id: orphan_mapping})
        assert result == {}  # silently skips missing nodes


# ---------------------------------------------------------- StateSpaceCompiler


class TestStateSpaceCompiler:
    """Tests for :class:`StateSpaceCompiler`."""

    def test_compiler_constructs_with_graph(self, graph_with_hidden_state) -> None:
        graph, *_ = graph_with_hidden_state
        compiler = StateSpaceCompiler(graph, schema_name="test_schema")
        assert compiler.graph is graph
        assert compiler.schema_name == "test_schema"
        assert isinstance(compiler.var_extractor, StateVariableExtractor)

    def test_compile_returns_state_space_model(
        self, graph_with_hidden_state, hidden_state_mappings
    ) -> None:
        graph, *_ = graph_with_hidden_state
        compiler = StateSpaceCompiler(graph, schema_name="counter")
        model = compiler.compile(hidden_state_mappings)
        assert isinstance(model, StateSpaceModel)
        assert model.schema_name == "counter"
        assert isinstance(model.time_regime, TimeRegime)

    def test_compile_populates_hidden_state_variables(
        self, graph_with_hidden_state, hidden_state_mappings
    ) -> None:
        graph, counter_id, flag_id = graph_with_hidden_state
        compiler = StateSpaceCompiler(graph, schema_name="counter")
        model = compiler.compile(hidden_state_mappings)
        assert f"var_{counter_id}" in model.variables
        assert f"var_{flag_id}" in model.variables
        assert len(model.variables) == 2

    def test_compile_with_empty_mappings_returns_empty_variables(
        self, graph_with_hidden_state
    ) -> None:
        graph, *_ = graph_with_hidden_state
        compiler = StateSpaceCompiler(graph, schema_name="empty")
        model = compiler.compile({})
        assert model.variables == {}
        assert isinstance(model.observations, dict)
        assert isinstance(model.actions, dict)

    def test_compile_result_id_is_schema_derived(
        self, graph_with_hidden_state, hidden_state_mappings
    ) -> None:
        graph, *_ = graph_with_hidden_state
        compiler = StateSpaceCompiler(graph, schema_name="my_schema")
        model = compiler.compile(hidden_state_mappings)
        # Compiler sets some id on the model — must be a non-empty string
        assert isinstance(model.id, str)
        assert model.id  # non-empty


# ----------------------------------------------------- StateVariable dataclass


class TestStateVariableDataclass:
    """Tests for the StateVariable dataclass itself."""

    def test_minimal_construction(self) -> None:
        v = StateVariable(
            id="var:x",
            name="x",
            var_type=StateVariableType.CONTINUOUS,
            node_id="n1",
        )
        assert v.id == "var:x"
        assert v.var_type is StateVariableType.CONTINUOUS
        assert v.cardinality is None
        assert v.confidence is ConfidenceLevel.MEDIUM
        assert v.mutations == []
        assert v.reads == []

    def test_state_variable_type_enum_values(self) -> None:
        assert StateVariableType.BOOLEAN.value == "boolean"
        assert StateVariableType.DISCRETE.value == "discrete"
        assert StateVariableType.CONTINUOUS.value == "continuous"
        assert StateVariableType.CATEGORICAL.value == "categorical"
        assert StateVariableType.VECTOR.value == "vector"
        assert StateVariableType.COMPOSITE.value == "composite"
