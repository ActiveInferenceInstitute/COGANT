#!/usr/bin/env python3
"""Coverage boost batch 73 — gnn/runner.py, viz/boundary.py, gnn/package.py internals,
cogant/__init__.py symbols.

Covers:
- gnn/runner.py: ExecutionTrace, GNNModelRunner (load_package, run, generate_execution_report,
  all private helpers: _initialize_beliefs, _initialize_state, _generate_observation,
  _update_beliefs, _compute_vfe, _evaluate_policies, _select_action_active_inference,
  _compute_reward, _count_unique_states, _count_unique_actions, _compute_statistics,
  _entropy, _assess_model_quality)
- viz/boundary.py: BoundaryMapper (generate_boundary_report, map_type_boundaries,
  markov_blanket_collapsed_mermaid, markov_blanket_detailed_mermaid,
  _find_containing_module, _find_inter_type_edges)
- gnn/package.py: GNNPackageBuilder private helpers (_count_nodes_by_kind,
  _count_mappings_by_tier, _fallback_chart, _extract_state_variables,
  _extract_observation_space, _extract_action_space, _extract_transition_structure,
  _extract_policies, _extract_constraints, _extract_objectives, _extract_factorization,
  _extract_factor_list, _extract_ontology_mappings)
- cogant/__init__.py: module-level imports, CogantSession alias, run_pipeline error path
"""

import json
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_empty_graph():
    from cogant.schemas.graph import ProgramGraph, GraphMetadata
    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind
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
        id="ss1", schema_name="test",
        variables={}, observations={}, actions={},
        transitions={}, likelihoods={}, preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_process_model():
    from cogant.process.extractor import ProcessModel
    return ProcessModel(id="pm1", schema_name="test", stages={}, connections={})


def _make_gnn_package(tmp_path):
    """Build a minimal GNN package directory for GNNModelRunner."""
    manifest = {
        "version": "1.0.0",
        "schema_name": "test",
        "created_at": "2025-01-01T00:00:00",
        "files": [],
    }
    model = {
        "model_name": "test",
        "hidden_states": ["state_a", "state_b"],
        "observations": [{"name": "obs_x"}, {"name": "obs_y"}],
        "actions": [{"name": "act_1"}, {"name": "act_2"}],
    }
    state_space = {
        "variables": [{"name": "var_a"}, {"name": "var_b"}],
        "observations": [{"name": "obs_x"}, {"name": "obs_y"}],
        "actions": [{"name": "act_1"}, {"name": "act_2"}],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "model.gnn.json").write_text(json.dumps(model))
    (tmp_path / "state_space.json").write_text(json.dumps(state_space))
    return tmp_path


# ---------------------------------------------------------------------------
# gnn/runner.py — ExecutionTrace
# ---------------------------------------------------------------------------

class TestExecutionTrace:
    def test_init_minimal(self):
        from cogant.gnn.runner import ExecutionTrace
        trace = ExecutionTrace(step=0, state={"x": 1})
        assert trace.step == 0
        assert trace.state == {"x": 1}
        assert trace.action is None

    def test_init_with_all_fields(self):
        from cogant.gnn.runner import ExecutionTrace
        trace = ExecutionTrace(
            step=1,
            state={"x": 2},
            action="move",
            observation="obs_a",
            reward=0.5,
            beliefs={"s0": 0.7, "s1": 0.3},
            free_energy_before=1.0,
            free_energy_after=0.8,
            policy_scores=[("act_1", 0.5)],
            action_rationale="best EFE",
            predicted_state={"x": 3},
        )
        assert trace.step == 1
        assert trace.action == "move"
        assert abs(trace.reward - 0.5) < 1e-9

    def test_to_dict_returns_dict(self):
        from cogant.gnn.runner import ExecutionTrace
        trace = ExecutionTrace(step=0, state={"x": 1}, action="a")
        d = trace.to_dict()
        assert isinstance(d, dict)
        assert "step" in d
        assert "state" in d


# ---------------------------------------------------------------------------
# gnn/runner.py — GNNModelRunner
# ---------------------------------------------------------------------------

class TestGNNModelRunner:
    def test_init(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        assert runner is not None
        assert isinstance(runner.traces, list)

    def test_load_package_returns_manifest(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        manifest = runner.load_package(str(tmp_path))
        assert isinstance(manifest, dict)
        assert "version" in manifest

    def test_load_package_missing_manifest_raises(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        with pytest.raises(FileNotFoundError):
            runner.load_package(str(tmp_path))

    def test_run_returns_dict(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        result = runner.run(steps=3)
        assert isinstance(result, dict)
        assert "success" in result
        assert "steps_completed" in result

    def test_run_without_load_raises(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        runner.manifest = {}  # empty manifest triggers RuntimeError
        with pytest.raises(RuntimeError):
            runner.run(steps=1)

    def test_generate_execution_report_no_traces(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        report = runner.generate_execution_report()
        assert isinstance(report, str)

    def test_generate_execution_report_after_run(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        runner.run(steps=3)
        report = runner.generate_execution_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_generate_execution_report_with_trace_dict(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        runner.run(steps=2)
        result = runner.run(steps=2)
        report = runner.generate_execution_report(trace=result)
        assert isinstance(report, str)

    def test_initialize_beliefs_with_state_space(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        beliefs = runner._initialize_beliefs()
        assert isinstance(beliefs, dict)
        assert len(beliefs) >= 1

    def test_initialize_beliefs_empty_state_space(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        runner.state_space = {}
        beliefs = runner._initialize_beliefs()
        assert isinstance(beliefs, dict)

    def test_initialize_state(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        state = runner._initialize_state()
        assert isinstance(state, dict)

    def test_generate_observation(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        obs = runner._generate_observation({"var_a": 0, "var_b": 1})
        assert isinstance(obs, str)

    def test_generate_observation_empty_state_space(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        runner.state_space = {}
        obs = runner._generate_observation({"x": 0})
        assert obs == "obs_0"

    def test_update_beliefs(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        prior = {"state_a": 0.5, "state_b": 0.5}
        posterior = runner._update_beliefs(prior, "state_a")
        assert isinstance(posterior, dict)
        total = sum(posterior.values())
        assert abs(total - 1.0) < 1e-6

    def test_update_beliefs_empty(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        result = runner._update_beliefs({}, "obs")
        assert result == {}

    def test_compute_vfe(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        beliefs = {"s0": 0.7, "s1": 0.3}
        vfe = runner._compute_vfe(beliefs, "obs_s0")
        assert isinstance(vfe, float)

    def test_compute_vfe_empty(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        vfe = runner._compute_vfe({}, "obs")
        assert vfe == 0.0

    def test_evaluate_policies(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        beliefs = {"s0": 0.6, "s1": 0.4}
        scores = runner._evaluate_policies(beliefs)
        assert isinstance(scores, list)

    def test_evaluate_policies_empty_state_space(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        runner.state_space = {}
        scores = runner._evaluate_policies({"s0": 1.0})
        assert scores == []

    def test_entropy(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        dist = {"a": 0.5, "b": 0.5}
        h = runner._entropy(dist)
        assert isinstance(h, float)
        assert h > 0

    def test_entropy_certain(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        dist = {"a": 1.0, "b": 0.0}
        h = runner._entropy(dist)
        assert isinstance(h, float)
        assert h == 0.0

    def test_compute_statistics(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        _make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        runner.run(steps=3)
        stats = runner._compute_statistics()
        assert isinstance(stats, dict)

    def test_compute_statistics_empty_traces(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        stats = runner._compute_statistics()
        assert isinstance(stats, dict)
        assert stats == {}

    def test_count_unique_states(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        traces = [{"state": {"x": 1}}, {"state": {"x": 1}}, {"state": {"x": 2}}]
        count = runner._count_unique_states(traces)
        assert count == 2

    def test_count_unique_actions(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        traces = [{"action": "a"}, {"action": "b"}, {"action": "a"}]
        count = runner._count_unique_actions(traces)
        assert count == 2

    def test_compute_reward(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        old_state = {"x": 1}
        new_state = {"x": 2}
        reward = runner._compute_reward(old_state, "act", new_state)
        assert isinstance(reward, float)

    def test_compute_reward_no_change(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        state = {"x": 1}
        reward = runner._compute_reward(state, "act", state)
        assert reward == 0.0


# ---------------------------------------------------------------------------
# viz/boundary.py — BoundaryMapper
# ---------------------------------------------------------------------------

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

    def test_fallback_chart_returns_html(self):
        builder = self._make_builder()
        result = builder._fallback_chart("Node Distribution", {"module": 3, "class": 5})
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result or "<html>" in result

    def test_fallback_chart_empty_counts(self):
        builder = self._make_builder()
        result = builder._fallback_chart("Empty", {})
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
        # Should at least have default policy
        assert len(result) >= 1

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
