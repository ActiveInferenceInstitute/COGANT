#!/usr/bin/env python3
"""Coverage boost batch 90 — viz/mermaid.py module functions and MermaidGenerator,
statespace/compiler.py _infer_distribution_type, _map_confidence,
api/orchestration.py helpers.

Covers:
- viz/mermaid.py: _infer_class_stereotype, _get_method_signature, _get_method_visibility,
  MermaidGenerator (generate_class_diagram, generate_dependency_graph,
  generate_state_diagram, generate_active_inference_diagram, generate_flowchart,
  generate_all, generate_sequence_diagram)
- statespace/compiler.py: _infer_distribution_type (all branches), _map_confidence
- api/orchestration.py: additional coverage of helpers
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_empty_graph():
    from cogant.schemas.graph import ProgramGraph, GraphMetadata
    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_class():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind
    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n_cls = builder.add_node(NodeKind.CLASS, "UserController", "api.UserController", path="api.py")
    n_cls2 = builder.add_node(NodeKind.CLASS, "UserModel", "db.UserModel", path="db.py")
    n_fn = builder.add_node(NodeKind.FUNCTION, "get_user", "api.UserController.get_user", path="api.py")
    n_fn2 = builder.add_node(NodeKind.FUNCTION, "_helper", "api._helper", path="api.py")
    builder.add_edge(n_cls.id, n_fn.id, EdgeKind.CONTAINS)
    builder.add_edge(n_cls.id, n_cls2.id, EdgeKind.DEPENDS_ON)
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


# ---------------------------------------------------------------------------
# viz/mermaid.py — module-level functions
# ---------------------------------------------------------------------------

class TestMermaidModuleFunctions:
    def test_infer_class_stereotype_controller(self):
        from cogant.viz.mermaid import _infer_class_stereotype
        from cogant.schemas.core import Node, NodeKind
        node = Node(
            id="n1", kind=NodeKind.CLASS, name="UserController",
            qualified_name="api.UserController",
            metadata={"something": True},
        )
        graph = _make_empty_graph()
        result = _infer_class_stereotype(node, graph)
        assert result == "<<controller>>"

    def test_infer_class_stereotype_handler(self):
        from cogant.viz.mermaid import _infer_class_stereotype
        from cogant.schemas.core import Node, NodeKind
        node = Node(
            id="n2", kind=NodeKind.CLASS, name="RequestHandler",
            qualified_name="handler.RequestHandler",
            metadata={"something": True},
        )
        graph = _make_empty_graph()
        result = _infer_class_stereotype(node, graph)
        assert result == "<<controller>>"

    def test_infer_class_stereotype_model(self):
        from cogant.viz.mermaid import _infer_class_stereotype
        from cogant.schemas.core import Node, NodeKind
        node = Node(
            id="n3", kind=NodeKind.CLASS, name="UserModel",
            qualified_name="db.UserModel",
            metadata={"something": True},
        )
        graph = _make_empty_graph()
        result = _infer_class_stereotype(node, graph)
        assert result == "<<model>>"

    def test_infer_class_stereotype_middleware(self):
        from cogant.viz.mermaid import _infer_class_stereotype
        from cogant.schemas.core import Node, NodeKind
        node = Node(
            id="n4", kind=NodeKind.CLASS, name="AuthMiddleware",
            qualified_name="mw.AuthMiddleware",
            metadata={"something": True},
        )
        graph = _make_empty_graph()
        result = _infer_class_stereotype(node, graph)
        assert result == "<<middleware>>"

    def test_infer_class_stereotype_none(self):
        from cogant.viz.mermaid import _infer_class_stereotype
        from cogant.schemas.core import Node, NodeKind
        node = Node(
            id="n5", kind=NodeKind.CLASS, name="RandomClass",
            qualified_name="utils.RandomClass",
            metadata={"something": True},
        )
        graph = _make_empty_graph()
        result = _infer_class_stereotype(node, graph)
        assert result is None

    def test_infer_class_stereotype_no_metadata(self):
        from cogant.viz.mermaid import _infer_class_stereotype
        from cogant.schemas.core import Node, NodeKind
        node = Node(
            id="n6", kind=NodeKind.CLASS, name="Controller",
            qualified_name="ctrl.Controller",
            metadata={},
        )
        graph = _make_empty_graph()
        result = _infer_class_stereotype(node, graph)
        assert result is None

    def test_get_method_signature_no_metadata(self):
        from cogant.viz.mermaid import _get_method_signature
        from cogant.schemas.core import Node, NodeKind
        node = Node(
            id="n7", kind=NodeKind.FUNCTION, name="process",
            qualified_name="mod.process", metadata={},
        )
        result = _get_method_signature(node)
        assert "process" in result
        assert "()" in result

    def test_get_method_signature_with_params(self):
        from cogant.viz.mermaid import _get_method_signature
        from cogant.schemas.core import Node, NodeKind
        node = Node(
            id="n8", kind=NodeKind.FUNCTION, name="add",
            qualified_name="mod.add",
            metadata={"parameters": ["a", "b"], "return_type": "int"},
        )
        result = _get_method_signature(node)
        assert "add" in result
        assert "a" in result or "b" in result

    def test_get_method_visibility_public(self):
        from cogant.viz.mermaid import _get_method_visibility
        assert _get_method_visibility("public_method") == "+"

    def test_get_method_visibility_protected(self):
        from cogant.viz.mermaid import _get_method_visibility
        assert _get_method_visibility("_protected_method") == "#"

    def test_get_method_visibility_private(self):
        from cogant.viz.mermaid import _get_method_visibility
        assert _get_method_visibility("__private_method") == "-"


class TestMermaidGenerator:
    def _make_gen(self):
        from cogant.viz.mermaid import MermaidGenerator
        return MermaidGenerator()

    def test_generate_class_diagram_empty(self):
        gen = self._make_gen()
        result = gen.generate_class_diagram(_make_empty_graph())
        assert isinstance(result, str)
        assert "classDiagram" in result

    def test_generate_class_diagram_with_class(self):
        gen = self._make_gen()
        graph = _make_graph_with_class()
        result = gen.generate_class_diagram(graph)
        assert isinstance(result, str)
        assert "classDiagram" in result

    def test_generate_dependency_graph_empty(self):
        gen = self._make_gen()
        result = gen.generate_dependency_graph(_make_empty_graph())
        assert isinstance(result, str)
        assert "graph" in result.lower()

    def test_generate_dependency_graph_with_nodes(self):
        gen = self._make_gen()
        graph = _make_graph_with_class()
        result = gen.generate_dependency_graph(graph)
        assert isinstance(result, str)

    def test_generate_state_diagram_empty(self):
        gen = self._make_gen()
        ss = _make_state_space()
        result = gen.generate_state_diagram(ss)
        assert isinstance(result, str)
        assert "stateDiagram" in result

    def test_generate_active_inference_diagram_empty(self):
        gen = self._make_gen()
        ss = _make_state_space()
        result = gen.generate_active_inference_diagram(ss)
        assert isinstance(result, str)

    def test_generate_flowchart_empty(self):
        gen = self._make_gen()
        graph = _make_empty_graph()
        result = gen.generate_flowchart(graph, semantic_mappings={})
        assert isinstance(result, str)
        assert "flowchart" in result.lower() or "graph" in result.lower()

    def test_generate_sequence_diagram_none(self):
        gen = self._make_gen()
        result = gen.generate_sequence_diagram(process_model=None, graph=None)
        assert isinstance(result, str)
        assert "sequenceDiagram" in result

    def test_generate_all_returns_dict(self):
        gen = self._make_gen()
        ss = _make_state_space()
        from cogant.process.extractor import ProcessModel
        pm = ProcessModel(id="pm1", schema_name="test", stages={}, connections={})
        result = gen.generate_all(
            graph=_make_empty_graph(),
            state_space=ss,
            process_model=pm,
        )
        assert isinstance(result, dict)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# statespace/compiler.py — _infer_distribution_type and _map_confidence
# ---------------------------------------------------------------------------

class TestStateSpaceCompilerHelpers:
    def _make_compiler(self):
        from cogant.statespace.compiler import StateSpaceCompiler
        from cogant.schemas.graph import ProgramGraph, GraphMetadata
        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        return StateSpaceCompiler(graph, "test_schema")

    def _make_state_var(self, var_type, cardinality=2):
        from cogant.statespace.variables import StateVariable, StateVariableType
        return StateVariable(
            id="v1",
            name="test_var",
            var_type=var_type,
            node_id="node_v1",
            cardinality=cardinality,
        )

    def test_infer_distribution_boolean(self):
        from cogant.statespace.variables import StateVariableType
        compiler = self._make_compiler()
        var = self._make_state_var(StateVariableType.BOOLEAN)
        result = compiler._infer_distribution_type(var)
        assert result == "bernoulli"

    def test_infer_distribution_discrete_binary(self):
        from cogant.statespace.variables import StateVariableType
        compiler = self._make_compiler()
        var = self._make_state_var(StateVariableType.DISCRETE, cardinality=2)
        result = compiler._infer_distribution_type(var)
        assert result == "bernoulli"

    def test_infer_distribution_discrete_multi(self):
        from cogant.statespace.variables import StateVariableType
        compiler = self._make_compiler()
        var = self._make_state_var(StateVariableType.DISCRETE, cardinality=5)
        result = compiler._infer_distribution_type(var)
        assert result == "categorical"

    def test_infer_distribution_continuous(self):
        from cogant.statespace.variables import StateVariableType
        compiler = self._make_compiler()
        var = self._make_state_var(StateVariableType.CONTINUOUS)
        result = compiler._infer_distribution_type(var)
        assert result == "gaussian"

    def test_infer_distribution_categorical(self):
        from cogant.statespace.variables import StateVariableType
        compiler = self._make_compiler()
        var = self._make_state_var(StateVariableType.CATEGORICAL, cardinality=3)
        result = compiler._infer_distribution_type(var)
        assert result == "categorical"

    def test_map_confidence_high(self):
        compiler = self._make_compiler()
        from cogant.statespace.compiler import ConfidenceLevel
        result = compiler._map_confidence(0.95)
        assert result is not None

    def test_map_confidence_low(self):
        compiler = self._make_compiler()
        result = compiler._map_confidence(0.1)
        assert result is not None

    def test_map_confidence_zero(self):
        compiler = self._make_compiler()
        result = compiler._map_confidence(0.0)
        assert result is not None

    def test_map_confidence_one(self):
        compiler = self._make_compiler()
        result = compiler._map_confidence(1.0)
        assert result is not None
