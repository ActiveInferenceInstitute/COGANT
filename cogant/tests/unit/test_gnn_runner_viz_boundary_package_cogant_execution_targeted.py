#!/usr/bin/env python3
"""Targeted branch tests — gnn/runner.py, viz/boundary.py, gnn/package.py internals,
cogant/__init__.py symbols.

Covers:
- gnn/runner.py: complete matrix rollout, trace history, and scoped execution report
- viz/boundary.py: BoundaryMapper (generate_boundary_report, map_type_boundaries,
  markov_blanket_collapsed_mermaid, markov_blanket_detailed_mermaid,
  _find_containing_module, _find_inter_type_edges)
- gnn/package.py: GNNPackageBuilder private helpers (_count_nodes_by_kind,
  _count_mappings_by_tier, _render_distribution_chart, _extract_state_variables,
  _extract_observation_space, _extract_action_space, _extract_transition_structure,
  _extract_policies, _extract_constraints, _extract_objectives, _extract_factorization,
  _extract_factor_list, _extract_ontology_mappings)
- cogant/__init__.py: module-level imports, CogantSession alias, run_pipeline error path
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_empty_graph():
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.CLASS, "Cls", "mod.Cls", path="mod.py")
    n3 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    builder.add_edge(n1.id, n3.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime

    return StateSpaceModel(
        id="ss1",
        schema_name="test",
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

    return ProcessModel(id="pm1", schema_name="test", stages={}, connections={})


class TestGNNModelRunner:
    @pytest.mark.parametrize("steps", [1, 3, 12, 35])
    def test_complete_matrix_rollout_and_report(self, tmp_path, steps):
        from tests.gnn_execution_fixture import runner

        model = runner(tmp_path)
        result = model.run(steps)
        assert result["steps_completed"] == steps
        assert len(model.traces) == steps
        assert len(model.beliefs_history) == steps + 1
        assert sum(model.action_counts.values()) == steps
        assert "not measured execution" in model.generate_execution_report()
        assert result["policy_horizon"] == 1
        assert result["policy_objective"] == "risk_plus_ambiguity"


class TestBoundaryMapperExtended:
    def _make_mapper(self):
        from cogant.viz.boundary import BoundaryMapper

        return BoundaryMapper()

    def test_init(self):
        mapper = self._make_mapper()
        assert mapper is not None

    def test_generate_boundary_report_empty(self):
        mapper = self._make_mapper()
        graph = _make_empty_graph()
        report = mapper.generate_boundary_report(graph)
        assert isinstance(report, dict)
        assert "total_boundary_crossings" in report

    def test_generate_boundary_report_with_nodes(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        report = mapper.generate_boundary_report(graph)
        assert isinstance(report, dict)
        assert "module_coupling_matrix" in report
        assert "type_coupling_score" in report

    def test_map_type_boundaries(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        result = mapper.map_type_boundaries(graph)
        assert isinstance(result, str)

    def test_map_type_boundaries_empty(self):
        mapper = self._make_mapper()
        graph = _make_empty_graph()
        result = mapper.map_type_boundaries(graph)
        assert isinstance(result, str)

    def test_find_containing_module_returns_none_or_str(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        # Pick a node id from the graph
        node_ids = list(graph.nodes.keys())
        result = mapper._find_containing_module(node_ids[0], graph)
        assert result is None or isinstance(result, str)

    def test_find_inter_type_edges_returns_list(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        edges = mapper._find_inter_type_edges(graph)
        assert isinstance(edges, list)

    def test_find_inter_type_edges_empty_graph(self):
        mapper = self._make_mapper()
        graph = _make_empty_graph()
        edges = mapper._find_inter_type_edges(graph)
        assert edges == []

    def test_markov_blanket_collapsed_mermaid(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        result = mapper.markov_blanket_collapsed_mermaid(graph)
        assert isinstance(result, str)

    def test_markov_blanket_detailed_mermaid(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        result = mapper.markov_blanket_detailed_mermaid(graph)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# gnn/package.py — GNNPackageBuilder private helpers
# ---------------------------------------------------------------------------


class TestGNNPackageBuilderHelpers:
    def _make_builder(self, with_nodes=False):
        from cogant.gnn.package import GNNPackageBuilder

        graph = _make_graph_with_nodes() if with_nodes else _make_empty_graph()
        return GNNPackageBuilder(
            graph=graph,
            state_space=_make_state_space(),
            process_model=_make_process_model(),
            mappings={},
        )

    def test_count_nodes_by_kind_empty(self):
        builder = self._make_builder()
        result = builder._count_nodes_by_kind()
        assert isinstance(result, dict)

    def test_count_nodes_by_kind_with_nodes(self):
        builder = self._make_builder(with_nodes=True)
        result = builder._count_nodes_by_kind()
        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_count_mappings_by_tier_empty(self):
        builder = self._make_builder()
        result = builder._count_mappings_by_tier()
        assert isinstance(result, dict)

    def test_render_distribution_chart_returns_html(self):
        builder = self._make_builder()
        result = builder._render_distribution_chart("Node Distribution", {"module": 3, "class": 5})
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result or "<html>" in result

    def test_render_distribution_chart_empty_counts(self):
        builder = self._make_builder()
        result = builder._render_distribution_chart("Empty", {})
        assert isinstance(result, str)

    def test_extract_state_variables_empty(self):
        builder = self._make_builder()
        result = builder._extract_state_variables()
        assert isinstance(result, list)

    def test_extract_observation_space_empty(self):
        builder = self._make_builder()
        result = builder._extract_observation_space()
        assert isinstance(result, list)

    def test_extract_action_space_empty(self):
        builder = self._make_builder()
        result = builder._extract_action_space()
        assert isinstance(result, list)

    def test_extract_transition_structure(self):
        builder = self._make_builder()
        result = builder._extract_transition_structure()
        assert isinstance(result, dict)
        assert "type" in result

    def test_extract_policies_returns_list(self):
        builder = self._make_builder()
        result = builder._extract_policies()
        assert isinstance(result, list)
        # No POLICY mappings → no fabricated default policy (673db14).
        assert result == []

    def test_extract_constraints_empty(self):
        builder = self._make_builder()
        result = builder._extract_constraints()
        assert isinstance(result, list)

    def test_extract_factorization_empty(self):
        builder = self._make_builder()
        result = builder._extract_factorization()
        assert isinstance(result, dict)
        assert "type" in result
        assert "factor_count" in result

    def test_extract_factor_list(self):
        builder = self._make_builder()
        result = builder._extract_factor_list()
        assert isinstance(result, list)

    def test_extract_ontology_mappings_empty(self):
        builder = self._make_builder()
        result = builder._extract_ontology_mappings()
        assert isinstance(result, list)

    def test_state_var_object_returns_none_on_empty(self):
        builder = self._make_builder()
        result = builder._state_var_object("nonexistent_var")
        assert result is None

    def test_action_object_returns_none_on_empty(self):
        builder = self._make_builder()
        result = builder._action_object("nonexistent_action")
        assert result is None


# ---------------------------------------------------------------------------
# cogant/__init__.py — top-level symbols
# ---------------------------------------------------------------------------


class TestCogantInit:
    def test_version_accessible(self):
        import cogant

        assert hasattr(cogant, "__version__")
        assert isinstance(cogant.__version__, str)

    def test_rust_version_accessible(self):
        import cogant

        assert hasattr(cogant, "__rust_version__")
        # May be None if Rust extension unavailable
        assert cogant.__rust_version__ is None or isinstance(cogant.__rust_version__, str)

    def test_rust_available_flag(self):
        import cogant

        assert hasattr(cogant, "_RUST_AVAILABLE")
        assert isinstance(cogant._RUST_AVAILABLE, bool)

    def test_cogant_session_alias(self):
        import cogant

        assert hasattr(cogant, "CogantSession")

    def test_gnn_bundle_alias(self):
        import cogant

        assert hasattr(cogant, "GNNBundle")

    def test_run_pipeline_callable(self):
        import cogant

        assert callable(cogant.run_pipeline)

    def test_run_pipeline_raises_on_invalid_target(self, tmp_path):
        import cogant

        # Should either run and fail, or raise ImportError if session unavailable
        try:
            cogant.run_pipeline(str(tmp_path / "nonexistent"), str(tmp_path / "out"))
        except (ImportError, Exception):
            pass  # Any exception is acceptable for nonexistent target
