#!/usr/bin/env python3
"""Targeted branch tests — gnn/package.py helper methods.

Covers:
- GNNPackageBuilder: static helpers (_checksum, _checksum_dict, _enum_value),
  count helpers (_count_graph_nodes, _count_graph_edges, _count_edges_by_kind,
  _count_state_space_elements, _count_nodes_by_kind, _count_mappings_by_tier),
  extract helpers (_extract_classes, _extract_relationships,
  _extract_ontology_mappings, _extract_factorization, _extract_factor_list,
  _extract_state_variables, _extract_observation_space, _extract_action_space,
  _extract_constraints, _extract_preferences, _extract_source_evidence,
  _state_var_object, _action_object, _is_deterministic)
"""

import pytest

pytestmark = pytest.mark.unit


def _make_state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime

    return StateSpaceModel(
        id="ss1",
        schema_name="test_schema",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_process_model():
    from cogant.process.extractor import ProcessModel

    return ProcessModel(
        id="pm1",
        schema_name="test_process",
        stages={},
        connections={},
    )


def _make_minimal_builder(tmp_path=None):
    """Create a GNNPackageBuilder with minimal empty objects."""
    from cogant.gnn.package import GNNPackageBuilder
    from cogant.graph.builder import ProgramGraphBuilder

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    graph = builder.finalize()

    state_space = _make_state_space()
    process_model = _make_process_model()
    mappings: dict = {}

    return GNNPackageBuilder(
        graph=graph,
        state_space=state_space,
        process_model=process_model,
        mappings=mappings,
    )


def _make_builder_with_nodes():
    """Create a builder whose graph has some nodes and edges."""
    from cogant.gnn.package import GNNPackageBuilder
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    mod = builder.add_node(NodeKind.MODULE, "mymod", "mymod", path="mymod.py")
    cls = builder.add_node(NodeKind.CLASS, "MyClass", "mymod.MyClass", path="mymod.py")
    fn = builder.add_node(NodeKind.FUNCTION, "fn", "mymod.fn", path="mymod.py")
    builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
    builder.add_edge(mod.id, fn.id, EdgeKind.CONTAINS)
    graph = builder.finalize()

    state_space = _make_state_space()
    process_model = _make_process_model()
    mappings: dict = {}

    return GNNPackageBuilder(
        graph=graph,
        state_space=state_space,
        process_model=process_model,
        mappings=mappings,
    )


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------


class TestChecksumHelpers:
    def test_checksum_returns_string(self):
        from cogant.gnn.package import GNNPackageBuilder

        result = GNNPackageBuilder._checksum("hello world")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex

    def test_checksum_deterministic(self):
        from cogant.gnn.package import GNNPackageBuilder

        r1 = GNNPackageBuilder._checksum("data")
        r2 = GNNPackageBuilder._checksum("data")
        assert r1 == r2

    def test_checksum_different_inputs(self):
        from cogant.gnn.package import GNNPackageBuilder

        r1 = GNNPackageBuilder._checksum("hello")
        r2 = GNNPackageBuilder._checksum("world")
        assert r1 != r2

    def test_checksum_dict_returns_string(self):
        from cogant.gnn.package import GNNPackageBuilder

        result = GNNPackageBuilder._checksum_dict({"key": "value"})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_checksum_dict_deterministic(self):
        from cogant.gnn.package import GNNPackageBuilder

        r1 = GNNPackageBuilder._checksum_dict({"a": 1, "b": 2})
        r2 = GNNPackageBuilder._checksum_dict({"a": 1, "b": 2})
        assert r1 == r2

    def test_checksum_dict_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        result = GNNPackageBuilder._checksum_dict({})
        assert isinstance(result, str)


class TestEnumValue:
    def test_enum_returns_value(self):
        from cogant.gnn.package import _enum_value
        from cogant.schemas.core import NodeKind

        assert _enum_value(NodeKind.FUNCTION) == NodeKind.FUNCTION.value

    def test_non_enum_returns_as_is(self):
        from cogant.gnn.package import _enum_value

        assert _enum_value("plain string") == "plain string"
        assert _enum_value(42) == 42
        assert _enum_value(None) is None


# ---------------------------------------------------------------------------
# Count helpers
# ---------------------------------------------------------------------------


class TestCountHelpers:
    def test_count_graph_nodes_empty(self):
        b = _make_minimal_builder()
        assert b._count_graph_nodes() == 0

    def test_count_graph_nodes_with_nodes(self):
        b = _make_builder_with_nodes()
        assert b._count_graph_nodes() == 3

    def test_count_graph_edges_empty(self):
        b = _make_minimal_builder()
        assert b._count_graph_edges() == 0

    def test_count_graph_edges_with_edges(self):
        b = _make_builder_with_nodes()
        assert b._count_graph_edges() == 2

    def test_count_edges_by_kind_empty(self):
        b = _make_minimal_builder()
        result = b._count_edges_by_kind()
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_count_edges_by_kind_with_edges(self):
        b = _make_builder_with_nodes()
        result = b._count_edges_by_kind()
        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_count_state_space_elements_empty(self):
        b = _make_minimal_builder()
        result = b._count_state_space_elements()
        assert "variables" in result
        assert "observations" in result
        assert "actions" in result

    def test_count_nodes_by_kind(self):
        b = _make_builder_with_nodes()
        result = b._count_nodes_by_kind()
        assert isinstance(result, dict)
        # Should have module, class, function kinds
        assert len(result) >= 1

    def test_count_nodes_by_kind_empty(self):
        b = _make_minimal_builder()
        result = b._count_nodes_by_kind()
        assert result == {}

    def test_count_mappings_by_tier_empty(self):
        b = _make_minimal_builder()
        result = b._count_mappings_by_tier()
        assert isinstance(result, dict)

    def test_count_mappings_by_tier_with_mappings(self):
        from cogant.gnn.package import GNNPackageBuilder
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.semantic import ConfidenceTier, MappingKind, SemanticMapping

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        # Create a real SemanticMapping
        m = SemanticMapping(
            id="m1",
            kind=MappingKind.HIDDEN_STATE,
            semantic_label="test",
            confidence_tier=ConfidenceTier.STATIC_ONLY,
        )
        mappings = {"m1": m}
        b = GNNPackageBuilder(
            graph=graph,
            state_space=_make_state_space(),
            process_model=_make_process_model(),
            mappings=mappings,
        )
        result = b._count_mappings_by_tier()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Extract helpers
# ---------------------------------------------------------------------------


class TestExtractClasses:
    def test_empty_graph_returns_empty(self):
        b = _make_minimal_builder()
        result = b._extract_classes()
        assert result == []

    def test_returns_class_names(self):
        b = _make_builder_with_nodes()
        result = b._extract_classes()
        assert "MyClass" in result


class TestExtractRelationships:
    def test_empty_graph_returns_empty(self):
        b = _make_minimal_builder()
        result = b._extract_relationships()
        assert result == []

    def test_returns_edges(self):
        b = _make_builder_with_nodes()
        result = b._extract_relationships()
        assert len(result) == 2
        assert all("source" in r and "target" in r and "kind" in r for r in result)


class TestExtractOntologyMappings:
    def test_empty_mappings_returns_empty(self):
        b = _make_minimal_builder()
        result = b._extract_ontology_mappings()
        assert result == []

    def test_with_mapping(self):
        from cogant.gnn.package import GNNPackageBuilder
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.semantic import ConfidenceTier, MappingKind, SemanticMapping

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        m = SemanticMapping(
            id="m1",
            kind=MappingKind.OBSERVATION,
            semantic_label="obs",
            confidence_tier=ConfidenceTier.STATIC_ONLY,
        )
        b = GNNPackageBuilder(
            graph=graph,
            state_space=_make_state_space(),
            process_model=_make_process_model(),
            mappings={"m1": m},
        )
        result = b._extract_ontology_mappings()
        assert len(result) == 1
        assert result[0]["id"] == "m1"

    def test_non_dict_mappings(self):
        b = _make_minimal_builder()
        b.mappings = None  # type: ignore
        result = b._extract_ontology_mappings()
        assert result == []


class TestExtractFactorization:
    def test_empty_state_space(self):
        b = _make_minimal_builder()
        result = b._extract_factorization()
        assert isinstance(result, dict)
        assert "type" in result

    def test_extract_factor_list_empty(self):
        b = _make_minimal_builder()
        result = b._extract_factor_list()
        assert isinstance(result, list)


class TestExtractStateVariables:
    def test_empty_returns_empty(self):
        b = _make_minimal_builder()
        result = b._extract_state_variables()
        assert result == []


class TestExtractObservationSpace:
    def test_empty_returns_empty(self):
        b = _make_minimal_builder()
        result = b._extract_observation_space()
        assert result == []


class TestExtractActionSpace:
    def test_empty_returns_empty(self):
        b = _make_minimal_builder()
        result = b._extract_action_space()
        assert result == []


class TestExtractConstraints:
    def test_empty_returns_empty(self):
        b = _make_minimal_builder()
        result = b._extract_constraints()
        assert result == []

    def test_with_constraint_mapping(self):
        from cogant.gnn.package import GNNPackageBuilder
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.semantic import ConfidenceTier, MappingKind, SemanticMapping

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        m = SemanticMapping(
            id="c1",
            kind=MappingKind.CONSTRAINT,
            semantic_label="constraint",
            confidence_tier=ConfidenceTier.STATIC_ONLY,
        )
        b = GNNPackageBuilder(
            graph=graph,
            state_space=_make_state_space(),
            process_model=_make_process_model(),
            mappings={"c1": m},
        )
        result = b._extract_constraints()
        assert len(result) == 1
        assert result[0]["id"] == "c1"


class TestExtractPreferences:
    def test_empty_returns_empty(self):
        b = _make_minimal_builder()
        result = b._extract_preferences()
        assert result == []


class TestExtractSourceEvidence:
    def test_returns_dict_with_keys(self):
        b = _make_minimal_builder()
        result = b._extract_source_evidence()
        assert "graph_nodes" in result
        assert "graph_edges" in result
        assert "timestamp" in result
        assert result["graph_nodes"] == 0


class TestStateVarObject:
    def test_missing_returns_none(self):
        b = _make_minimal_builder()
        result = b._state_var_object("nonexistent")
        assert result is None


class TestActionObject:
    def test_missing_returns_none(self):
        b = _make_minimal_builder()
        result = b._action_object("nonexistent")
        assert result is None


class TestIsDeterministic:
    def test_empty_graph_returns_bool(self):
        b = _make_minimal_builder()
        result = b._is_deterministic()
        assert isinstance(result, bool)
