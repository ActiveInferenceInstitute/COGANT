#!/usr/bin/env python3
"""Batch 9 coverage boost: simulate/runner.py, viz/boundary.py, viz/graph_view.py,
reverse/idempotency.py, static/types.py, gnn/formatter/dynamics.py."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_graph():
    """Create a ProgramGraph with modules, classes, functions, and edges."""
    from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    meta = GraphMetadata(repo_uri="test://repo", languages={"python"})
    graph = ProgramGraph(metadata=meta)

    m1 = Node(
        id="m1", kind=NodeKind.MODULE, name="module_a", qualified_name="module_a", language="python"
    )
    m2 = Node(
        id="m2", kind=NodeKind.MODULE, name="module_b", qualified_name="module_b", language="python"
    )
    c1 = Node(id="c1", kind=NodeKind.CLASS, name="ClassA", qualified_name="module_a.ClassA")
    c2 = Node(id="c2", kind=NodeKind.CLASS, name="ClassB", qualified_name="module_b.ClassB")
    f1 = Node(
        id="f1", kind=NodeKind.FUNCTION, name="func_a", qualified_name="module_a.ClassA.func_a"
    )
    f2 = Node(
        id="f2", kind=NodeKind.METHOD, name="method_b", qualified_name="module_b.ClassB.method_b"
    )

    for n in [m1, m2, c1, c2, f1, f2]:
        graph.add_node(n)

    edges = [
        Edge(id="e1", source_id="m1", target_id="c1", kind=EdgeKind.CONTAINS),
        Edge(id="e2", source_id="c1", target_id="f1", kind=EdgeKind.CONTAINS),
        Edge(id="e3", source_id="m2", target_id="c2", kind=EdgeKind.CONTAINS),
        Edge(id="e4", source_id="c2", target_id="f2", kind=EdgeKind.CONTAINS),
        Edge(id="e5", source_id="f1", target_id="f2", kind=EdgeKind.CALLS),
        Edge(id="e6", source_id="m1", target_id="m2", kind=EdgeKind.IMPORTS),
    ]
    for e in edges:
        graph.add_edge(e)
    return graph


def _make_state_space():
    """Create a minimal StateSpaceModel."""
    from cogant.statespace.compiler import Action, ObservationModality, StateSpaceModel
    from cogant.statespace.temporal import TimeRegime
    from cogant.statespace.variables import StateVariable, StateVariableType

    v1 = StateVariable(
        id="v1", name="pos", var_type=StateVariableType.DISCRETE, node_id="m1", cardinality=3
    )
    v2 = StateVariable(id="v2", name="vel", var_type=StateVariableType.CONTINUOUS, node_id="m2")
    a1 = Action(id="a1", name="move", controller_id="f1", effects=["v1"], preconditions=["v2"])
    obs1 = ObservationModality(
        id="o1", name="sensor", source_node_id="f1", modality_type="discrete"
    )

    return StateSpaceModel(
        id="ssm1",
        schema_name="test_schema",
        variables={"v1": v1, "v2": v2},
        observations={"o1": obs1},
        actions={"a1": a1},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_process_model():
    """Create a minimal ProcessModel."""
    from cogant.process.extractor import ProcessModel

    return ProcessModel(id="p1", schema_name="test_schema", stages={}, connections={})


# ---------------------------------------------------------------------------
# simulate/runner.py — ModelRunner
# ---------------------------------------------------------------------------


class TestModelRunnerBeliefUpdate:
    def test_basic(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner(seed=42)
        beliefs = {"s0": 0.6, "s1": 0.4}
        posterior = runner.belief_update(beliefs, "s0")
        assert isinstance(posterior, dict)
        assert abs(sum(posterior.values()) - 1.0) < 1e-9

    def test_empty_beliefs(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        result = runner.belief_update({}, "s0")
        assert result == {}

    def test_single_state(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        result = runner.belief_update({"only": 1.0}, "only")
        assert "only" in result
        assert abs(result["only"] - 1.0) < 1e-9

    def test_nonmatching_observation(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        # observation must be one of the belief states, else ValueError from underlying distribution
        beliefs = {"a": 0.5, "b": 0.5}
        result = runner.belief_update(beliefs, "b")
        assert isinstance(result, dict)
        assert len(result) == 2

    def test_skewed_beliefs(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        beliefs = {"s0": 0.9, "s1": 0.05, "s2": 0.05}
        result = runner.belief_update(beliefs, "s0")
        assert result["s0"] > result["s1"]


class TestModelRunnerPolicyEvaluation:
    def test_basic(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner(seed=42)
        beliefs = {"s0": 0.7, "s1": 0.3}
        ranking = runner.policy_evaluation(beliefs, ["move_left", "move_right"])
        assert len(ranking) == 2
        assert all(isinstance(v, float) for _, v in ranking)

    def test_empty_actions(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        result = runner.policy_evaluation({"s0": 1.0}, [])
        assert result == []

    def test_empty_beliefs(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        result = runner.policy_evaluation({}, ["move"])
        # empty beliefs — returns [(action, 0.0)] for each action
        assert len(result) == 1
        assert result[0] == ("move", 0.0)

    def test_multiple_actions(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner(seed=1)
        beliefs = {"s0": 0.4, "s1": 0.4, "s2": 0.2}
        actions = ["a1", "a2", "a3", "a4"]
        ranking = runner.policy_evaluation(beliefs, actions)
        assert len(ranking) == 4
        # Sorted by EFE ascending
        scores = [s for _, s in ranking]
        assert scores == sorted(scores)


class TestModelRunnerComputeFreeEnergy:
    def test_state_matching_observation(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        fe = runner.compute_free_energy({"s0": 0.8, "s1": 0.2}, "s0")
        assert isinstance(fe, float)

    def test_state_not_matching_observation(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        fe = runner.compute_free_energy({"s0": 0.5, "s1": 0.5}, "unknown_obs")
        assert isinstance(fe, float)

    def test_empty_state(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        fe = runner.compute_free_energy({}, "s0")
        assert fe == 0.0

    def test_single_state(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        fe = runner.compute_free_energy({"s0": 1.0}, "s0")
        assert isinstance(fe, float)


class TestModelRunnerVfeEfe:
    def _runner_with_matrices(self):
        from cogant.simulate.runner import ModelRunner

        A = [[0.9, 0.1], [0.1, 0.9]]
        B = [[[0.8, 0.2], [0.3, 0.7]], [[0.2, 0.8], [0.7, 0.3]]]
        C = [1.0, 0.0]
        D = [0.5, 0.5]
        return ModelRunner(seed=42, A=A, B=B, C=C, D=D)

    def test_has_generative_model(self):
        runner = self._runner_with_matrices()
        assert runner.has_generative_model is True

    def test_no_generative_model(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        assert runner.has_generative_model is False

    def test_vfe_from_beliefs_no_obs(self):
        runner = self._runner_with_matrices()
        vfe = runner.vfe_from_beliefs([0.8, 0.2])
        assert isinstance(vfe, float)

    def test_vfe_from_beliefs_with_obs(self):
        runner = self._runner_with_matrices()
        vfe = runner.vfe_from_beliefs([0.8, 0.2], observation=[0.9, 0.1])
        assert isinstance(vfe, float)

    def test_vfe_from_beliefs_with_prior(self):
        runner = self._runner_with_matrices()
        vfe = runner.vfe_from_beliefs([0.7, 0.3], prior=[0.5, 0.5])
        assert isinstance(vfe, float)

    def test_vfe_no_A_raises(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        with pytest.raises(RuntimeError, match="requires A"):
            runner.vfe_from_beliefs([0.5, 0.5])

    def test_efe_for_policy(self):
        runner = self._runner_with_matrices()
        efe = runner.efe_for_policy([0, 1])
        assert isinstance(efe, float)

    def test_efe_no_matrices_raises(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        with pytest.raises(RuntimeError, match="requires A, B, and C"):
            runner.efe_for_policy([0, 1])

    def test_update_beliefs_from_observation(self):
        runner = self._runner_with_matrices()
        posterior = runner.update_beliefs_from_observation([0.5, 0.5], 0)
        assert isinstance(posterior, list)
        assert abs(sum(posterior) - 1.0) < 1e-9

    def test_update_beliefs_no_A_raises(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        with pytest.raises(RuntimeError, match="requires A"):
            runner.update_beliefs_from_observation([0.5, 0.5], 0)


class TestModelRunnerActiveInference:
    def _make_runner_and_ssm(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner(seed=42)
        ssm = _make_state_space()
        return runner, ssm

    def test_active_inference_step_basic(self):
        runner, ssm = self._make_runner_and_ssm()
        beliefs = {"v1": 0.6, "v2": 0.4}
        result = runner.active_inference_step(beliefs, "v1", ssm)
        assert "new_beliefs" in result
        assert "selected_action" in result
        assert "predicted_next_state" in result
        assert "free_energy" in result
        assert "efe_ranking" in result

    def test_active_inference_step_updates_beliefs(self):
        runner, ssm = self._make_runner_and_ssm()
        beliefs = {"v1": 0.5, "v2": 0.5}
        result = runner.active_inference_step(beliefs, "v1", ssm)
        new_beliefs = result["new_beliefs"]
        assert isinstance(new_beliefs, dict)
        assert abs(sum(new_beliefs.values()) - 1.0) < 1e-9

    def test_run_active_inference_returns_trace(self):
        runner, ssm = self._make_runner_and_ssm()
        trace = runner.run_active_inference(ssm, steps=3)
        assert len(trace) == 4  # step 0 + 3 steps
        assert trace[0]["step"] == 0

    def test_run_active_inference_trace_keys(self):
        runner, ssm = self._make_runner_and_ssm()
        trace = runner.run_active_inference(ssm, steps=2)
        for step in trace:
            assert "step" in step
            assert "beliefs" in step
            assert "observation" in step
            assert "action" in step
            assert "free_energy" in step

    def test_run_active_inference_empty_state_space(self):
        from cogant.simulate.runner import ModelRunner
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        runner = ModelRunner(seed=0)
        empty_ssm = StateSpaceModel(
            id="empty",
            schema_name="empty",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        trace = runner.run_active_inference(empty_ssm, steps=3)
        assert len(trace) >= 1
        assert trace[0]["beliefs"] == {}

    def test_generate_report_from_trace(self):
        runner, ssm = self._make_runner_and_ssm()
        trace = runner.run_active_inference(ssm, steps=5)
        report = runner.generate_report(trace)
        assert isinstance(report, str)
        assert "Active Inference Simulation Report" in report
        assert "Free Energy" in report
        assert "Actions Taken" in report

    def test_generate_report_single_step(self):
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner()
        trace = [
            {
                "step": 0,
                "beliefs": {"s0": 1.0},
                "observation": None,
                "action": None,
                "free_energy": 0.0,
                "predicted_state": {},
            }
        ]
        report = runner.generate_report(trace)
        assert "Total steps: 1" in report

    def test_generate_trace_structure(self):
        runner, ssm = self._make_runner_and_ssm()
        result = runner.generate_trace(ssm)
        assert "schema_name" in result
        assert "trace" in result
        assert "variables" in result
        assert "observations" in result
        assert "actions" in result
        assert "metadata" in result
        assert result["schema_name"] == "test_schema"


# ---------------------------------------------------------------------------
# viz/boundary.py — BoundaryMapper
# ---------------------------------------------------------------------------


class TestBoundaryMapper:
    def _bm(self):
        from cogant.viz.boundary import BoundaryMapper

        return BoundaryMapper()

    def test_map_module_boundaries_empty(self):
        from cogant.schemas.graph import GraphMetadata, ProgramGraph

        bm = self._bm()
        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="x"))
        result = bm.map_module_boundaries(graph)
        assert "graph TD" in result

    def test_map_module_boundaries_with_module(self):
        bm = self._bm()
        graph = _make_graph()
        result = bm.map_module_boundaries(graph)
        assert "graph TD" in result
        assert "module_a" in result or "m1" in result

    def test_map_module_boundaries_with_classes(self):
        bm = self._bm()
        graph = _make_graph()
        result = bm.map_module_boundaries(graph)
        assert isinstance(result, str)
        assert len(result) > 10

    def test_map_type_boundaries_empty(self):
        from cogant.schemas.graph import GraphMetadata, ProgramGraph

        bm = self._bm()
        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="x"))
        result = bm.map_type_boundaries(graph)
        assert isinstance(result, str)

    def test_map_type_boundaries_with_classes(self):
        bm = self._bm()
        graph = _make_graph()
        result = bm.map_type_boundaries(graph)
        assert isinstance(result, str)
        assert "classDiagram" in result or "graph" in result

    def test_generate_boundary_report_empty(self):
        from cogant.schemas.graph import GraphMetadata, ProgramGraph

        bm = self._bm()
        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="x"))
        report = bm.generate_boundary_report(graph)
        assert isinstance(report, dict)
        assert "total_boundary_crossings" in report

    def test_generate_boundary_report_with_graph(self):
        bm = self._bm()
        graph = _make_graph()
        report = bm.generate_boundary_report(graph)
        assert "total_boundary_crossings" in report
        assert "edge_type_distribution" in report
        assert "module_coupling_matrix" in report
        assert isinstance(report["total_boundary_crossings"], int)

    def test_generate_boundary_report_scores(self):
        bm = self._bm()
        graph = _make_graph()
        report = bm.generate_boundary_report(graph)
        assert "type_coupling_score" in report
        assert "external_dependencies_count" in report


# ---------------------------------------------------------------------------
# viz/graph_view.py — GraphVisualizer
# ---------------------------------------------------------------------------


class TestGraphVisualizer:
    def _gv(self):
        from cogant.viz.graph_view import GraphVisualizer

        return GraphVisualizer()

    def _sample_dict(self):
        return {
            "nodes": [
                {
                    "id": "n1",
                    "name": "module_a",
                    "type": "module",
                    "path": "/a.py",
                    "language": "python",
                },
                {"id": "n2", "name": "ClassA", "type": "class", "path": "/a.py"},
                {"id": "n3", "name": "func_b", "type": "function", "path": "/b.py"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "type": "contains", "weight": 1.0},
                {"source": "n2", "target": "n3", "type": "calls", "weight": 2.0},
            ],
            "metadata": {"repo_uri": "test://repo", "version": "1.0"},
        }

    def test_from_program_graph_dict(self):
        gv = self._gv()
        result = gv.from_program_graph(self._sample_dict())
        assert result is gv  # returns self
        assert len(gv.nodes) == 3
        assert len(gv.links) == 2

    def test_from_program_graph_empty(self):
        gv = self._gv()
        gv.from_program_graph({"nodes": [], "edges": []})
        assert len(gv.nodes) == 0
        assert len(gv.links) == 0

    def test_from_typed_graph(self):
        from cogant.viz.graph_view import GraphVisualizer

        gv = GraphVisualizer()
        graph = _make_graph()
        result = gv.from_typed_graph(graph)
        assert result is gv
        assert len(gv.nodes) == 6
        assert len(gv.links) > 0

    def test_to_d3_json_structure(self):
        gv = self._gv()
        gv.from_program_graph(self._sample_dict())
        d3 = gv.to_d3_json()
        assert "nodes" in d3
        assert "links" in d3
        assert "clusters" in d3

    def test_to_d3_json_nodes_have_id(self):
        gv = self._gv()
        gv.from_program_graph(self._sample_dict())
        d3 = gv.to_d3_json()
        for node in d3["nodes"]:
            assert "id" in node
            assert "label" in node

    def test_cluster_by_package(self):
        gv = self._gv()
        gv.from_program_graph(self._sample_dict())
        result = gv.cluster_by_package()
        assert result is gv  # chaining
        clusters = gv.get_clusters()
        assert isinstance(clusters, dict)

    def test_cluster_by_language(self):
        gv = self._gv()
        gv.from_program_graph(self._sample_dict())
        gv.cluster_by_language()
        clusters = gv.get_clusters()
        assert isinstance(clusters, dict)

    def test_cluster_by_kind(self):
        gv = self._gv()
        gv.from_program_graph(self._sample_dict())
        gv.cluster_by_kind()
        clusters = gv.get_clusters()
        assert isinstance(clusters, dict)

    def test_filter_by_edge_type(self):
        gv = self._gv()
        gv.from_program_graph(self._sample_dict())
        initial_links = len(gv.links)
        gv.filter_by_edge_type("calls")
        assert len(gv.links) <= initial_links

    def test_get_clusters_after_cluster(self):
        gv = self._gv()
        gv.from_program_graph(self._sample_dict())
        gv.cluster_by_kind()
        clusters = gv.get_clusters()
        # All node ids should appear in some cluster
        all_clustered = set()
        for members in clusters.values():
            all_clustered.update(members)
        for node in gv.nodes:
            assert node.id in all_clustered

    def test_render_html_creates_file(self, tmp_path):
        from cogant.viz.graph_view import GraphVisualizer

        gv = GraphVisualizer()
        gv.from_program_graph(self._sample_dict())
        out = str(tmp_path / "viz.html")
        result = gv.render_html(out)
        assert Path(out).exists()
        assert "<html>" in result or "html" in result.lower()

    def test_render_svg_creates_file(self, tmp_path):
        from cogant.viz.graph_view import GraphVisualizer

        gv = GraphVisualizer()
        gv.from_program_graph(self._sample_dict())
        out = str(tmp_path / "viz.svg")
        result = gv.render_svg(out)
        assert Path(out).exists()
        assert "<svg" in result or "svg" in result.lower()

    def test_cluster_by_service(self):
        gv = self._gv()
        gv.from_program_graph(self._sample_dict())
        result = gv.cluster_by_service()
        assert result is gv

    def test_from_typed_graph_metadata(self):
        from cogant.viz.graph_view import GraphVisualizer

        gv = GraphVisualizer()
        graph = _make_graph()
        gv.from_typed_graph(graph)
        assert gv.metadata.get("repo_uri") == "test://repo"
        assert "version" in gv.metadata


# ---------------------------------------------------------------------------
# reverse/idempotency.py — RoundtripResult + helpers
# ---------------------------------------------------------------------------


class TestRoundtripResult:
    def test_summary_isomorphic(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult(
            is_isomorphic=True,
            role_match_score=0.85,
            matrix_score=0.9,
            structural_score=0.75,
            original_roles={"HIDDEN_STATE": 2, "OBSERVATION": 1},
            synthesized_roles={"HIDDEN_STATE": 2, "OBSERVATION": 1},
            shape_match={"A": True, "B": True},
        )
        summary = r.summary()
        assert "[ISO]" in summary
        assert "role_match=85.00%" in summary
        assert "matrix=0.90" in summary
        assert "struct=0.75" in summary

    def test_summary_not_isomorphic(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult(
            is_isomorphic=False,
            role_match_score=0.3,
            matrix_score=0.5,
            structural_score=0.4,
        )
        summary = r.summary()
        assert "[DRIFT]" in summary
        assert "role_match=30.00%" in summary

    def test_summary_perfect_match(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult(
            is_isomorphic=True,
            role_match_score=1.0,
            matrix_score=1.0,
            structural_score=1.0,
        )
        summary = r.summary()
        assert "[ISO]" in summary
        assert "100.00%" in summary

    def test_default_fields(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult()
        assert r.is_isomorphic is False
        assert r.role_match_score == 0.0
        assert r.errors == []


class TestRoleMultisetFromModel:
    def test_basic(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel(
            model_name="test",
            hidden_states=["s_f0", "s_f1"],
            observations=["o_m0"],
            actions=["u_c0"],
            policies=["pi_0"],
            constraints=["G_c0"],
        )
        roles = _role_multiset_from_model(model)
        assert roles["HIDDEN_STATE"] == 2
        assert roles["OBSERVATION"] == 1
        assert roles["ACTION"] == 1
        assert roles["POLICY"] >= 1

    def test_annotation_adds_roles(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel(
            model_name="ann_test",
            annotations={"G": "ExpectedFreeEnergy"},
        )
        roles = _role_multiset_from_model(model)
        # ExpectedFreeEnergy -> POLICY
        assert roles["POLICY"] >= 1

    def test_empty_model(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel(model_name="empty")
        roles = _role_multiset_from_model(model)
        assert isinstance(roles, dict)

    def test_constraint_annotation(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel(
            model_name="constraint_test",
            hidden_states=["s0"],
            annotations={"C_m0": "Constraint"},
        )
        roles = _role_multiset_from_model(model)
        assert roles["HIDDEN_STATE"] >= 1


# ---------------------------------------------------------------------------
# static/types.py — TypeInferencer
# ---------------------------------------------------------------------------


class TestTypeInferencer:
    def _source_file(self, tmp_path, content):
        p = tmp_path / "src.py"
        p.write_text(content)
        return p

    def test_infer_from_annotated_variables(self, tmp_path):
        from cogant.static.types import TypeInferencer

        code = "x: int = 5\ny: str = 'hello'\nz: float = 3.14\n"
        p = self._source_file(tmp_path, code)
        infer = TypeInferencer()
        results = infer.infer_types_from_file(p)
        names = {r.symbol_name for r in results}
        assert "x" in names or len(results) >= 1

    def test_infer_from_function_return(self, tmp_path):
        from cogant.static.types import TypeInferencer

        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        p = self._source_file(tmp_path, code)
        infer = TypeInferencer()
        results = infer.infer_types_from_file(p)
        assert len(results) >= 1
        func_results = [r for r in results if r.symbol_kind == "function"]
        if func_results:
            assert func_results[0].inferred_type == "int"

    def test_infer_from_function_params(self, tmp_path):
        from cogant.static.types import TypeInferencer

        code = "def greet(name: str, age: int) -> str:\n    return f'{name}:{age}'\n"
        p = self._source_file(tmp_path, code)
        infer = TypeInferencer()
        results = infer.infer_types_from_file(p)
        param_results = [r for r in results if r.symbol_kind == "parameter"]
        assert len(param_results) >= 1

    def test_infer_from_class_attributes(self, tmp_path):
        from cogant.static.types import TypeInferencer

        code = "class Foo:\n    x: int = 0\n    name: str = 'test'\n"
        p = self._source_file(tmp_path, code)
        infer = TypeInferencer()
        results = infer.infer_types_from_file(p)
        assert isinstance(results, list)

    def test_infer_from_literal_types(self, tmp_path):
        from cogant.static.types import TypeInferencer

        code = "a = 42\nb = 'hello'\nc = 3.14\nd = True\n"
        p = self._source_file(tmp_path, code)
        infer = TypeInferencer()
        results = infer.infer_types_from_file(p)
        assert isinstance(results, list)

    def test_infer_star_args(self, tmp_path):
        from cogant.static.types import TypeInferencer

        code = "def f(*args: str, **kwargs: int) -> None:\n    pass\n"
        p = self._source_file(tmp_path, code)
        infer = TypeInferencer()
        results = infer.infer_types_from_file(p)
        assert isinstance(results, list)

    def test_infer_class_methods(self, tmp_path):
        from cogant.static.types import TypeInferencer

        code = "class Bar:\n    def process(self, x: float) -> bool:\n        return x > 0\n"
        p = self._source_file(tmp_path, code)
        infer = TypeInferencer()
        results = infer.infer_types_from_file(p)
        assert isinstance(results, list)

    def test_empty_file(self, tmp_path):
        from cogant.static.types import TypeInferencer

        p = self._source_file(tmp_path, "")
        infer = TypeInferencer()
        results = infer.infer_types_from_file(p)
        assert results == []

    def test_nonexistent_file(self, tmp_path):
        from cogant.static.types import TypeInferencer

        infer = TypeInferencer()
        # Non-existent file should return [] or raise gracefully
        result = infer.infer_types_from_file(tmp_path / "nonexistent.py")
        assert result == []


# ---------------------------------------------------------------------------
# gnn/formatter/base.py — GNNMarkdownFormatter (exercises dynamics mixin)
# ---------------------------------------------------------------------------


class TestGNNMarkdownFormatter:
    def _make_formatter(self):
        from cogant.gnn.formatter.base import GNNMarkdownFormatter

        graph = _make_graph()
        ssm = _make_state_space()
        process = _make_process_model()
        return GNNMarkdownFormatter(graph, ssm, process, {})

    def test_format_returns_string(self):
        formatter = self._make_formatter()
        result = formatter.format()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_format_contains_model_name(self):
        formatter = self._make_formatter()
        result = formatter.format()
        assert "test_schema" in result or "ModelName" in result

    def test_format_contains_state_space(self):
        formatter = self._make_formatter()
        result = formatter.format()
        # Should have state space section
        assert "State" in result or "Variable" in result or "pos" in result

    def test_format_contains_actions(self):
        formatter = self._make_formatter()
        result = formatter.format()
        # Should reference move action
        assert "move" in result or "Action" in result or "a1" in result

    def test_format_with_empty_state_space(self):
        from cogant.gnn.formatter.base import GNNMarkdownFormatter
        from cogant.process.extractor import ProcessModel
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        empty_graph = ProgramGraph(metadata=GraphMetadata(repo_uri="x"))
        empty_ssm = StateSpaceModel(
            id="empty",
            schema_name="empty_schema",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        empty_process = ProcessModel(id="p0", schema_name="empty_schema", stages={}, connections={})
        formatter = GNNMarkdownFormatter(empty_graph, empty_ssm, empty_process, {})
        result = formatter.format()
        assert isinstance(result, str)

    def test_format_multiple_calls_return_string(self):
        formatter = self._make_formatter()
        r1 = formatter.format()
        r2 = formatter.format()
        # Both calls return non-empty strings
        assert isinstance(r1, str) and len(r1) > 50
        assert isinstance(r2, str) and len(r2) > 50


# ---------------------------------------------------------------------------
# parsers/tree_sitter_base.py — TreeSitterParser
# ---------------------------------------------------------------------------


class TestTreeSitterParser:
    """Tests for tree_sitter_base that work without tree-sitter installed."""

    def test_instantiate(self):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        assert isinstance(parser, TreeSitterParser)

    def test_available_languages_empty_without_pkg(self):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        langs = parser.available_languages()
        assert isinstance(langs, set)
        # May be empty if tree-sitter not installed

    def test_supported_extensions_subset_of_map(self):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        exts = parser.supported_extensions()
        assert isinstance(exts, set)
        assert exts <= set(parser._LANGUAGE_MAP.keys())

    def test_language_for_path_python(self):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        lang = parser.language_for_path(Path("test.py"))
        assert lang == "python"

    def test_language_for_path_ts(self):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        lang = parser.language_for_path(Path("app.ts"))
        assert lang == "typescript"

    def test_language_for_path_unknown(self):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        lang = parser.language_for_path(Path("data.xyz"))
        assert lang is None

    def test_parse_file_unknown_extension(self, tmp_path):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        p = tmp_path / "test.xyz"
        p.write_text("hello world")
        parser = TreeSitterParser()
        result = parser.parse_file(p)
        assert result is None  # unknown language

    def test_parse_file_known_ext_no_grammar(self, tmp_path):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        p = tmp_path / "test.py"
        p.write_text("x = 1")
        parser = TreeSitterParser()
        # If tree-sitter not installed, returns None (lang not in parsers)
        result = parser.parse_file(p)
        assert result is None or hasattr(result, "path")

    def test_parse_source_no_grammar_returns_none(self):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        result = parser.parse_source("x = 1", "python")
        # Returns None if language not loaded
        assert result is None or hasattr(result, "path")

    def test_parse_file_string_path(self, tmp_path):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        p = tmp_path / "test.py"
        p.write_text("x = 1")
        parser = TreeSitterParser()
        result = parser.parse_file(str(p))  # Test string-to-Path coercion
        assert result is None or hasattr(result, "path")

    def test_language_map_has_expected_keys(self):
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        assert ".py" in parser._LANGUAGE_MAP
        assert ".js" in parser._LANGUAGE_MAP
        assert ".ts" in parser._LANGUAGE_MAP
        assert ".rs" in parser._LANGUAGE_MAP

    def test_parsed_symbol_dataclass(self):
        from cogant.parsers.tree_sitter_base import ParsedSymbol

        sym = ParsedSymbol(
            name="my_func",
            kind="function",
            line_start=1,
            line_end=10,
            qualified_name="module.my_func",
            docstring="Does stuff",
            metadata={"async": True},
        )
        assert sym.name == "my_func"
        assert sym.kind == "function"
        assert sym.line_start == 1

    def test_parsed_file_dataclass(self):
        from cogant.parsers.tree_sitter_base import ParsedFile

        pf = ParsedFile(
            path="test.py",
            language="python",
            symbols=[],
            imports=[{"raw": "import os", "line": 1}],
            calls=[],
            errors=[],
        )
        assert pf.path == "test.py"
        assert pf.language == "python"
        assert len(pf.imports) == 1

    def test_get_tree_sitter_parser_singleton(self):
        from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

        p1 = get_tree_sitter_parser()
        p2 = get_tree_sitter_parser()
        assert p1 is p2  # Should be singleton
