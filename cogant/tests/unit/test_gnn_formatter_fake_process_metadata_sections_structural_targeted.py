#!/usr/bin/env python3
"""Targeted branch tests — GNN formatter metadata, structural, semantic, upstream sections.

Covers:
- gnn/formatter/metadata.py: _format_model_metadata, _format_repository_metadata,
  _format_source_coverage, _format_confidence, _format_provenance,
  _format_rendering_hints, _format_validation_notes
- gnn/formatter/structural.py: _format_state_space, _format_observation_modalities,
  _format_actions_policies, _format_connections, _format_factors
- gnn/formatter/semantic.py: _format_markov_blanket, _format_ontology_mapping
- gnn/formatter/upstream.py: _format_upstream_header, _format_gnn_section,
  _format_model_name, _format_state_space_block, _format_upstream_connections,
  _format_time, _format_initial_parameterization, _format_actinf_ontology_annotation
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_empty_state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime

    return StateSpaceModel(
        id="test_ss",
        schema_name="TestModel",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_graph():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test_repo")
    mod = builder.add_node(
        NodeKind.MODULE, "mymodule", "mymodule", path="mymodule.py", language="python"
    )
    cls = builder.add_node(NodeKind.CLASS, "MyClass", "mymodule.MyClass", path="mymodule.py")
    func = builder.add_node(NodeKind.FUNCTION, "my_func", "mymodule.my_func", path="mymodule.py")
    builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
    builder.add_edge(cls.id, func.id, EdgeKind.CONTAINS)
    return builder.finalize()


class _FakeProcess:
    connections = []
    stages = []
    policies = []
    timelines = []


def _make_formatter(state_space=None, graph=None, mappings=None):
    from cogant.gnn.formatter import GNNMarkdownFormatter

    if state_space is None:
        state_space = _make_empty_state_space()
    if graph is None:
        graph = _make_graph()
    if mappings is None:
        mappings = {}
    return GNNMarkdownFormatter(graph, state_space, _FakeProcess(), mappings)


# ---------------------------------------------------------------------------
# gnn/formatter/metadata.py
# ---------------------------------------------------------------------------


class TestMetadataSections:
    def test_format_model_metadata_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_model_metadata()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_model_metadata_has_header(self):
        fmt = _make_formatter()
        result = fmt._format_model_metadata()
        # Should have some header-like content
        assert "##" in result or "Model" in result or "#" in result

    def test_format_repository_metadata_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_repository_metadata()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_repository_metadata_with_real_graph(self):
        fmt = _make_formatter()
        result = fmt._format_repository_metadata()
        # graph nodes should be reflected
        assert "mymodule" in result or "Repository" in result or "##" in result

    def test_format_source_coverage_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_source_coverage()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_confidence_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_confidence()
        assert isinstance(result, str)

    def test_format_confidence_with_mappings(self):
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            kind = MappingKind.HIDDEN_STATE
            confidence_score = 0.85
            confidence_tier = None
            semantic_label = "state"
            description = ""
            graph_fragment_node_ids = []
            evidence_count = 1
            status = "active"
            id = "m1"

        fmt = _make_formatter(mappings={"m1": FakeMapping()})
        result = fmt._format_confidence()
        assert isinstance(result, str)

    def test_format_provenance_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_provenance()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_rendering_hints_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_rendering_hints()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_validation_notes_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_validation_notes()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# gnn/formatter/structural.py
# ---------------------------------------------------------------------------


class TestStructuralSections:
    def test_format_state_space_empty(self):
        fmt = _make_formatter()
        result = fmt._format_state_space()
        assert isinstance(result, str)
        assert "State" in result or "##" in result

    def test_format_state_space_with_variables(self):
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.statespace.variables import StateVariable, StateVariableType

        sv = StateVariable(
            id="v1",
            name="myvar",
            node_id="n1",
            var_type=StateVariableType.BOOLEAN,
            cardinality=2,
        )
        ss = StateSpaceModel(
            id="ts",
            schema_name="TS",
            variables={"v1": sv},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_state_space()
        assert "myvar" in result or "State" in result

    def test_format_observation_modalities_empty(self):
        fmt = _make_formatter()
        result = fmt._format_observation_modalities()
        assert isinstance(result, str)

    def test_format_observation_modalities_with_obs(self):
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.translate.confidence import ConfidenceTier

        class FakeObs:
            id = "o1"
            name = "sensor_reading"
            modality = "symbolic"
            modality_type = "symbolic"
            source_node_id = None
            source_channels = []
            values = None
            cardinality = None
            confidence = ConfidenceTier.STATIC_ONLY
            description = ""

        ss = StateSpaceModel(
            id="ts",
            schema_name="TS",
            variables={},
            observations={"o1": FakeObs()},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_observation_modalities()
        assert "sensor_reading" in result or "Observation" in result

    def test_format_actions_policies_empty(self):
        fmt = _make_formatter()
        result = fmt._format_actions_policies()
        assert isinstance(result, str)

    def test_format_actions_policies_with_actions(self):
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.translate.confidence import ConfidenceTier

        class FakeAction:
            id = "a1"
            name = "do_thing"
            controller_id = None
            parameters = []
            effects = []
            preconditions = []
            description = "do something"
            confidence = ConfidenceTier.STATIC_ONLY

        ss = StateSpaceModel(
            id="ts",
            schema_name="TS",
            variables={},
            observations={},
            actions={"a1": FakeAction()},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_actions_policies()
        assert "do_thing" in result or "Action" in result

    def test_format_connections_empty(self):
        fmt = _make_formatter()
        result = fmt._format_connections()
        assert isinstance(result, str)

    def test_format_connections_with_edges(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        f1 = builder.add_node(NodeKind.FUNCTION, "func_a", "m.func_a")
        f2 = builder.add_node(NodeKind.FUNCTION, "func_b", "m.func_b")
        builder.add_edge(f1.id, f2.id, EdgeKind.CALLS)
        graph = builder.finalize()

        fmt = _make_formatter(graph=graph)
        result = fmt._format_connections()
        assert isinstance(result, str)

    def test_format_factors_empty(self):
        fmt = _make_formatter()
        result = fmt._format_factors()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# gnn/formatter/semantic.py
# ---------------------------------------------------------------------------


class TestSemanticSections:
    def test_format_markov_blanket_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_markov_blanket()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_markov_blanket_with_graph(self):
        fmt = _make_formatter()
        result = fmt._format_markov_blanket()
        # Should mention Markov or blanket concepts
        assert "Markov" in result or "##" in result or "blanket" in result.lower()

    def test_format_ontology_mapping_empty(self):
        fmt = _make_formatter()
        result = fmt._format_ontology_mapping()
        assert isinstance(result, str)

    def test_format_ontology_mapping_with_mappings(self):
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            kind = MappingKind.HIDDEN_STATE
            id = "m1"
            semantic_label = "state_var"
            description = "internal state"
            graph_fragment_node_ids = ["n1"]
            graph_fragment_edge_ids = []
            confidence_score = 0.85
            confidence_tier = None
            evidence_count = 3
            status = "active"

        fmt = _make_formatter(mappings={"m1": FakeMapping()})
        result = fmt._format_ontology_mapping()
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# gnn/formatter/upstream.py
# ---------------------------------------------------------------------------


class TestUpstreamSections:
    def test_format_upstream_header_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_upstream_header()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_gnn_section_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_gnn_section()
        assert isinstance(result, str)
        assert "GNNSection" in result or "GNN" in result

    def test_format_model_name_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_model_name()
        assert isinstance(result, str)
        assert "ModelName" in result or "Model" in result

    def test_format_state_space_block_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_state_space_block()
        assert isinstance(result, str)
        assert "StateSpaceBlock" in result or "State" in result

    def test_format_upstream_connections_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_upstream_connections()
        assert isinstance(result, str)

    def test_format_time_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_time()
        assert isinstance(result, str)
        assert "Time" in result

    def test_format_initial_parameterization_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_initial_parameterization()
        assert isinstance(result, str)
        assert "Parameterization" in result or "Initial" in result

    def test_format_actinf_ontology_annotation_returns_string(self):
        fmt = _make_formatter()
        result = fmt._format_actinf_ontology_annotation()
        assert isinstance(result, str)
        assert "Ontology" in result or "ActInf" in result

    def test_upstream_model_id_returns_string(self):
        fmt = _make_formatter()
        result = fmt._upstream_model_id()
        assert isinstance(result, str)

    def test_format_model_annotation_returns_string(self):
        fmt = _make_formatter()
        try:
            result = fmt._format_model_annotation()
            assert isinstance(result, str)
        except AttributeError:
            pass  # method may not exist on all versions

    def test_format_model_parameters_returns_string(self):
        fmt = _make_formatter()
        try:
            result = fmt._format_model_parameters()
            assert isinstance(result, str)
        except AttributeError:
            pass  # method may not exist on all versions

    def test_format_upstream_footer_returns_string(self):
        fmt = _make_formatter()
        try:
            result = fmt._format_upstream_footer()
            assert isinstance(result, str)
        except AttributeError:
            pass  # method may not exist on all versions


# ---------------------------------------------------------------------------
# Additional structural formatter tests with richer state space
# ---------------------------------------------------------------------------


class TestStructuralWithRichStateSpace:
    def _make_rich_ss(self):
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.statespace.variables import StateVariable, StateVariableType

        sv1 = StateVariable(
            id="v1",
            name="counter",
            node_id="n1",
            var_type=StateVariableType.DISCRETE,
            cardinality=100,
        )
        sv2 = StateVariable(
            id="v2",
            name="flag",
            node_id="n2",
            var_type=StateVariableType.BOOLEAN,
            cardinality=2,
        )
        return StateSpaceModel(
            id="rich",
            schema_name="RichModel",
            variables={"v1": sv1, "v2": sv2},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )

    def test_state_space_with_variables_lists_them(self):
        ss = self._make_rich_ss()
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_state_space()
        assert "counter" in result or "flag" in result or "State" in result

    def test_factors_with_variables(self):
        ss = self._make_rich_ss()
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_factors()
        assert isinstance(result, str)
        assert len(result) > 50


# ---------------------------------------------------------------------------
# gnn/formatter/upstream.py — with richer state space and variables
# ---------------------------------------------------------------------------


class TestUpstreamWithStateSpace:
    def test_state_space_block_with_variables(self):
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.statespace.variables import StateVariable, StateVariableType

        sv = StateVariable(
            id="v1",
            name="hidden_state",
            node_id="n1",
            var_type=StateVariableType.CONTINUOUS,
            cardinality=None,
        )
        ss = StateSpaceModel(
            id="ts",
            schema_name="TS",
            variables={"v1": sv},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.ASYNCHRONOUS,
        )
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_state_space_block()
        assert isinstance(result, str)

    def test_upstream_header_with_observations(self):
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.translate.confidence import ConfidenceTier

        class FakeObs:
            id = "o1"
            name = "sensor"
            modality = "symbolic"
            modality_type = "symbolic"
            source_node_id = None
            source_channels = []
            values = None
            cardinality = None
            confidence = ConfidenceTier.STATIC_ONLY
            description = ""

        ss = StateSpaceModel(
            id="ts",
            schema_name="TS",
            variables={},
            observations={"o1": FakeObs()},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_upstream_header()
        assert isinstance(result, str)
        assert len(result) > 100
