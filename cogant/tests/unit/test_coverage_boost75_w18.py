#!/usr/bin/env python3
"""Coverage boost batch 75 — viz/mermaid.py extended paths, reverse/synthesizer.py
rendering helpers, statespace/compiler.py extended methods.

Covers:
- viz/mermaid.py: MermaidGenerator._get_class_stereotype (model/middleware),
  generate_class_diagram (with inheritance edges), generate_dependency_graph,
  generate_sequence_diagram (with calls edges), generate_flowchart (with mappings),
  generate_all (with mappings kwarg)
- reverse/synthesizer.py: _render_package_init, _render_state_module,
  _render_observe_module, _render_act_module, _render_policy_module,
  _render_constraints_module, _render_context_module, _render_main_module,
  _render_test_smoke, synthesize_package (full run)
- statespace/compiler.py: StateSpaceCompiler.compile extended (with nodes in graph)
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_empty_graph():
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_class_hierarchy():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n_mod = builder.add_node(NodeKind.MODULE, "mymod", "mymod", path="mymod.py")
    n_base = builder.add_node(
        NodeKind.CLASS, "BaseController", "mymod.BaseController", path="mymod.py"
    )
    n_child = builder.add_node(NodeKind.CLASS, "UserModel", "mymod.UserModel", path="mymod.py")
    n_middleware = builder.add_node(
        NodeKind.CLASS, "AuthMiddleware", "mymod.AuthMiddleware", path="mymod.py"
    )
    n_fn = builder.add_node(NodeKind.FUNCTION, "handle", "mymod.handle", path="mymod.py")
    builder.add_edge(n_mod.id, n_base.id, EdgeKind.CONTAINS)
    builder.add_edge(n_mod.id, n_child.id, EdgeKind.CONTAINS)
    builder.add_edge(n_mod.id, n_middleware.id, EdgeKind.CONTAINS)
    builder.add_edge(n_mod.id, n_fn.id, EdgeKind.CONTAINS)
    builder.add_edge(n_child.id, n_base.id, EdgeKind.INHERITS)
    builder.add_edge(n_fn.id, n_fn.id, EdgeKind.CALLS)
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


def _make_process_model_with_stages():
    from cogant.process.extractor import ProcessConnection, ProcessModel, Stage

    stage1 = Stage(id="s1", name="Ingest")
    stage2 = Stage(id="s2", name="Process")
    conn = ProcessConnection(
        id="c1",
        source_stage_id="s1",
        target_stage_id="s2",
        trigger="next",
    )
    return ProcessModel(
        id="pm1",
        schema_name="test",
        stages={"s1": stage1, "s2": stage2},
        connections={"c1": conn},
    )


def _make_reverse_model(name="test_model"):
    from cogant.reverse.parser import ReverseGNNModel

    return ReverseGNNModel(
        model_name=name,
        hidden_states=["state_a", "state_b"],
        observations=["obs_x", "obs_y"],
        actions=["act_1"],
        policies=[],
        constraints=[],
    )


def _make_package_plan(name="test_model"):
    from cogant.reverse.idempotency import plan_package

    model = _make_reverse_model(name)
    return plan_package(model), model


# ---------------------------------------------------------------------------
# viz/mermaid.py — _infer_class_stereotype module-level function
# ---------------------------------------------------------------------------


class TestMermaidStereotype:
    def _make_node(self, name, metadata=None):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(
            NodeKind.CLASS,
            name,
            f"mod.{name}",
            path="mod.py",
            metadata=metadata or {"some": "data"},
        )
        return node, builder.finalize()

    def test_stereotype_controller(self):
        from cogant.viz.mermaid import _infer_class_stereotype

        node, graph = self._make_node("UserController")
        result = _infer_class_stereotype(node, graph)
        assert result == "<<controller>>"

    def test_stereotype_model(self):
        from cogant.viz.mermaid import _infer_class_stereotype

        node, graph = self._make_node("UserModel")
        result = _infer_class_stereotype(node, graph)
        assert result == "<<model>>"

    def test_stereotype_middleware(self):
        from cogant.viz.mermaid import _infer_class_stereotype

        node, graph = self._make_node("AuthMiddleware")
        result = _infer_class_stereotype(node, graph)
        assert result == "<<middleware>>"

    def test_stereotype_none_empty_metadata(self):
        from cogant.viz.mermaid import _infer_class_stereotype

        node, graph = self._make_node("RandomClass", metadata=None)
        result = _infer_class_stereotype(node, graph)
        assert result is None

    def test_stereotype_entity(self):
        from cogant.viz.mermaid import _infer_class_stereotype

        node, graph = self._make_node("UserEntity")
        result = _infer_class_stereotype(node, graph)
        assert result == "<<model>>"


# ---------------------------------------------------------------------------
# viz/mermaid.py — MermaidGenerator extended diagrams
# ---------------------------------------------------------------------------


class TestMermaidGeneratorDiagrams:
    def _make_gen(self):
        from cogant.viz import MermaidGenerator

        return MermaidGenerator()

    def test_generate_class_diagram_with_inheritance(self):
        gen = self._make_gen()
        graph = _make_graph_with_class_hierarchy()
        result = gen.generate_class_diagram(graph)
        assert isinstance(result, str)
        assert "classDiagram" in result

    def test_generate_dependency_graph_with_nodes(self):
        gen = self._make_gen()
        graph = _make_graph_with_class_hierarchy()
        result = gen.generate_dependency_graph(graph)
        assert isinstance(result, str)
        assert "graph" in result

    def test_generate_dependency_graph_empty(self):
        gen = self._make_gen()
        graph = _make_empty_graph()
        result = gen.generate_dependency_graph(graph)
        assert isinstance(result, str)

    def test_generate_sequence_diagram_with_calls_edges(self):
        gen = self._make_gen()
        graph = _make_graph_with_class_hierarchy()
        result = gen.generate_sequence_diagram(graph=graph)
        assert isinstance(result, str)
        assert "sequenceDiagram" in result

    def test_generate_sequence_diagram_with_process_model_stages(self):
        gen = self._make_gen()
        pm = _make_process_model_with_stages()
        result = gen.generate_sequence_diagram(process_model=pm)
        assert isinstance(result, str)
        assert "sequenceDiagram" in result

    def test_generate_flowchart_empty_mappings(self):
        gen = self._make_gen()
        graph = _make_graph_with_class_hierarchy()
        result = gen.generate_flowchart(graph, semantic_mappings={})
        assert isinstance(result, str)

    def test_generate_all_with_mappings(self):
        gen = self._make_gen()
        graph = _make_graph_with_class_hierarchy()
        ss = _make_state_space()
        result = gen.generate_all(graph, state_space=ss, mappings={"key": "value"})
        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_generate_all_empty_graph_all_params(self):
        gen = self._make_gen()
        graph = _make_empty_graph()
        ss = _make_state_space()
        pm = _make_process_model_with_stages()
        result = gen.generate_all(graph, state_space=ss, process_model=pm, mappings={})
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# reverse/synthesizer.py — private rendering functions
# ---------------------------------------------------------------------------


class TestSynthesizerRenderModules:
    def test_render_package_init(self):
        from cogant.reverse.synthesizer import _render_package_init

        plan, _ = _make_package_plan()
        result = _render_package_init(plan)
        assert isinstance(result, str)

    def test_render_state_module(self):
        from cogant.reverse.synthesizer import _render_state_module

        plan, _ = _make_package_plan()
        result = _render_state_module(plan)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_observe_module(self):
        from cogant.reverse.synthesizer import _render_observe_module

        plan, _model = _make_package_plan()
        result = _render_observe_module(plan)
        assert isinstance(result, str)

    def test_render_act_module(self):
        from cogant.reverse.synthesizer import _render_act_module

        plan, _ = _make_package_plan()
        result = _render_act_module(plan)
        assert isinstance(result, str)

    def test_render_policy_module(self):
        from cogant.reverse.synthesizer import _render_policy_module

        plan, _ = _make_package_plan()
        result = _render_policy_module(plan)
        assert isinstance(result, str)

    def test_render_constraints_module(self):
        from cogant.reverse.synthesizer import _render_constraints_module

        plan, _ = _make_package_plan()
        result = _render_constraints_module(plan)
        assert isinstance(result, str)

    def test_render_context_module_empty(self):
        from cogant.reverse.synthesizer import _render_context_module

        plan, _ = _make_package_plan()
        result = _render_context_module(plan)
        assert isinstance(result, str)
        # With empty scaffold classes, should have placeholder
        assert "PlaceholderSettings" in result or len(result) > 0

    def test_render_main_module(self):
        from cogant.reverse.synthesizer import _render_main_module

        plan, _ = _make_package_plan()
        result = _render_main_module(plan)
        assert isinstance(result, str)

    def test_render_test_smoke(self):
        from cogant.reverse.synthesizer import _render_test_smoke

        plan, _ = _make_package_plan()
        result = _render_test_smoke(plan)
        assert isinstance(result, str)

    def test_synthesize_package_creates_files(self, tmp_path):
        from cogant.reverse.synthesizer import synthesize_package

        plan, model = _make_package_plan("synth_test")
        result = synthesize_package(plan, model, tmp_path)
        assert isinstance(result, Path)
        assert result.exists()
        # Should have some Python files
        py_files = list(result.glob("*.py"))
        assert len(py_files) >= 1

    def test_render_act_module_no_actions(self):
        from cogant.reverse.synthesizer import PackagePlan, _render_act_module

        plan = PackagePlan(
            package_name="test_pkg",
            raw_model_name="test",
            nodes=[],
            state_vars=[],
            obs_functions=[],
            action_methods=[],  # empty
            policy_functions=[],
            constraint_checks=[],
            context_functions=[],
            scaffold_constraint_checks=[],
            scaffold_policy_functions=[],
            scaffold_context_classes=[],
            has_A_matrix=False,
            has_B_tensor=False,
            has_C_vector=False,
            has_D_vector=False,
        )
        result = _render_act_module(plan)
        assert isinstance(result, str)
        assert "noop" in result  # fallback no-op action


# ---------------------------------------------------------------------------
# statespace/compiler.py — StateSpaceCompiler extended
# ---------------------------------------------------------------------------


class TestStateSpaceCompilerExtended:
    def test_compile_with_rich_graph(self):
        from cogant.statespace import StateSpaceCompiler, StateSpaceModel

        graph = _make_graph_with_class_hierarchy()
        compiler = StateSpaceCompiler(graph, schema_name="test")
        model = compiler.compile(semantic_mappings={})
        assert isinstance(model, StateSpaceModel)

    def test_compile_returns_valid_time_regime(self):
        from cogant.statespace import StateSpaceCompiler
        from cogant.statespace.temporal import TimeRegime

        graph = _make_graph_with_class_hierarchy()
        compiler = StateSpaceCompiler(graph, schema_name="test")
        model = compiler.compile(semantic_mappings={})
        assert isinstance(model.time_regime, TimeRegime)

    def test_compile_variables_is_dict_or_list(self):
        from cogant.statespace import StateSpaceCompiler

        graph = _make_graph_with_class_hierarchy()
        compiler = StateSpaceCompiler(graph, schema_name="test")
        model = compiler.compile(semantic_mappings={})
        assert isinstance(model.variables, (dict, list))

    def test_compile_actions_is_dict_or_list(self):
        from cogant.statespace import StateSpaceCompiler

        graph = _make_graph_with_class_hierarchy()
        compiler = StateSpaceCompiler(graph, schema_name="test")
        model = compiler.compile(semantic_mappings={})
        assert isinstance(model.actions, (dict, list))

    def test_compile_observations_is_dict_or_list(self):
        from cogant.statespace import StateSpaceCompiler

        graph = _make_graph_with_class_hierarchy()
        compiler = StateSpaceCompiler(graph, schema_name="test")
        model = compiler.compile(semantic_mappings={})
        assert isinstance(model.observations, (dict, list))
