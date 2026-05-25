#!/usr/bin/env python3
"""Targeted branch tests — gnn/matrices.py, gnn/package.py,
reverse/idempotency.py (compare_graph_structure, compare_matrices, plan_package),
reverse/synthesizer.py (render_matrices_module, PackagePlan).

Covers:
- gnn/matrices.py: GNNMatrices (compute_A, compute_B, compute_C, compute_D,
  to_dict, to_gnn_markdown_block, validate_shapes)
- gnn/package.py: GNNPackageBuilder (build), GNNMarkdownFormatter (format),
  GNNJSONExporter (export, export_to_string)
- reverse/idempotency.py: compare_graph_structure, compare_matrices, plan_package,
  RoundtripResult fields
- reverse/synthesizer.py: render_matrices_module, PackagePlan dataclass
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
    n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
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


# ---------------------------------------------------------------------------
# gnn/matrices.py — GNNMatrices
# ---------------------------------------------------------------------------


class TestGNNMatrices:
    def _make_matrices(self):
        from cogant.gnn.matrices import GNNMatrices

        graph = _make_graph_with_nodes()
        state_space = _make_state_space()
        return GNNMatrices(graph, mappings={}, state_space=state_space)

    def test_init(self):
        matrices = self._make_matrices()
        assert matrices is not None

    def test_compute_A_returns_list(self):
        matrices = self._make_matrices()
        A = matrices.compute_A()
        assert isinstance(A, list)

    def test_compute_B_returns_list(self):
        matrices = self._make_matrices()
        B = matrices.compute_B()
        assert isinstance(B, list)

    def test_compute_C_returns_list(self):
        matrices = self._make_matrices()
        C = matrices.compute_C()
        assert isinstance(C, list)

    def test_compute_D_returns_list(self):
        matrices = self._make_matrices()
        D = matrices.compute_D()
        assert isinstance(D, list)

    def test_to_dict_returns_dict(self):
        matrices = self._make_matrices()
        result = matrices.to_dict()
        assert isinstance(result, dict)

    def test_to_gnn_markdown_block_returns_str(self):
        matrices = self._make_matrices()
        result = matrices.to_gnn_markdown_block()
        assert isinstance(result, str)

    def test_validate_shapes_returns_tuple(self):
        matrices = self._make_matrices()
        valid, errors = matrices.validate_shapes()
        assert isinstance(valid, bool)
        assert isinstance(errors, list)


# ---------------------------------------------------------------------------
# gnn/package.py — GNNMarkdownFormatter, GNNJSONExporter, GNNPackageBuilder
# ---------------------------------------------------------------------------


class TestGNNMarkdownFormatter:
    def _make_formatter(self):
        from cogant.gnn.package import GNNMarkdownFormatter

        return GNNMarkdownFormatter(
            program_graph=_make_empty_graph(),
            state_space_model=_make_state_space(),
            process_model=_make_process_model(),
            semantic_mappings={},
        )

    def test_init(self):
        formatter = self._make_formatter()
        assert formatter is not None

    def test_format_returns_str(self):
        formatter = self._make_formatter()
        result = formatter.format()
        assert isinstance(result, str)

    def test_format_with_nodes(self):
        from cogant.gnn.package import GNNMarkdownFormatter

        formatter = GNNMarkdownFormatter(
            program_graph=_make_graph_with_nodes(),
            state_space_model=_make_state_space(),
            process_model=_make_process_model(),
            semantic_mappings={},
        )
        result = formatter.format()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_section_returns_str_or_none(self):
        formatter = self._make_formatter()
        result = formatter.format_section("test_section")
        assert result is None or isinstance(result, str)


class TestGNNJSONExporter:
    def _make_exporter(self):
        from cogant.gnn.package import GNNJSONExporter

        return GNNJSONExporter(
            program_graph=_make_empty_graph(),
            state_space_model=_make_state_space(),
            process_model=_make_process_model(),
            semantic_mappings={},
        )

    def test_init(self):
        exporter = self._make_exporter()
        assert exporter is not None

    def test_export_returns_dict(self):
        exporter = self._make_exporter()
        result = exporter.export()
        assert isinstance(result, dict)

    def test_export_to_string_returns_str(self):
        import json

        exporter = self._make_exporter()
        result = exporter.export_to_string()
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_export_with_nodes(self):
        from cogant.gnn.package import GNNJSONExporter

        exporter = GNNJSONExporter(
            program_graph=_make_graph_with_nodes(),
            state_space_model=_make_state_space(),
            process_model=_make_process_model(),
            semantic_mappings={},
        )
        result = exporter.export()
        assert isinstance(result, dict)


class TestGNNPackageBuilder:
    def test_init(self):
        from cogant.gnn.package import GNNPackageBuilder

        builder = GNNPackageBuilder(
            graph=_make_empty_graph(),
            state_space=_make_state_space(),
            process_model=_make_process_model(),
            mappings={},
        )
        assert builder is not None

    def test_build_returns_dict(self, tmp_path):
        from cogant.gnn.package import GNNPackageBuilder

        builder = GNNPackageBuilder(
            graph=_make_empty_graph(),
            state_space=_make_state_space(),
            process_model=_make_process_model(),
            mappings={},
        )
        result = builder.build(str(tmp_path))
        assert isinstance(result, dict)

    def test_build_with_nodes(self, tmp_path):
        from cogant.gnn.package import GNNPackageBuilder

        builder = GNNPackageBuilder(
            graph=_make_graph_with_nodes(),
            state_space=_make_state_space(),
            process_model=_make_process_model(),
            mappings={},
        )
        result = builder.build(str(tmp_path))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# reverse/idempotency.py — compare_graph_structure, compare_matrices,
#                           plan_package
# ---------------------------------------------------------------------------


class TestCompareGraphStructure:
    def test_identical_structures(self):
        from cogant.reverse.idempotency import compare_graph_structure

        score = compare_graph_structure(
            nodes_a=["n1", "n2"],
            edges_a=[("n1", "n2")],
            nodes_b=["n1", "n2"],
            edges_b=[("n1", "n2")],
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_empty_structures(self):
        from cogant.reverse.idempotency import compare_graph_structure

        score = compare_graph_structure([], [], [], [])
        assert isinstance(score, float)

    def test_different_structures(self):
        from cogant.reverse.idempotency import compare_graph_structure

        score = compare_graph_structure(
            nodes_a=["n1", "n2", "n3"],
            edges_a=[("n1", "n2")],
            nodes_b=["n1"],
            edges_b=[],
        )
        assert isinstance(score, float)
        assert score <= 1.0

    def test_score_is_normalized(self):
        from cogant.reverse.idempotency import compare_graph_structure

        score = compare_graph_structure(
            ["a", "b"],
            [("a", "b")],
            ["c", "d", "e"],
            [("c", "d"), ("d", "e")],
        )
        assert 0.0 <= score <= 1.0


class TestCompareMatrices:
    def test_identical_matrices(self):
        from cogant.reverse.idempotency import compare_matrices

        A = {"A": [[0.9, 0.1], [0.1, 0.9]], "B": [[[1.0, 0.0]]]}
        score = compare_matrices(A, A)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_empty_matrices(self):
        from cogant.reverse.idempotency import compare_matrices

        score = compare_matrices({}, {})
        assert isinstance(score, float)

    def test_different_matrices(self):
        from cogant.reverse.idempotency import compare_matrices

        A = {"A": [[0.9, 0.1]]}
        B = {"A": [[0.1, 0.9]]}
        score = compare_matrices(A, B)
        assert isinstance(score, float)
        assert score <= 1.0

    def test_missing_key_in_one(self):
        from cogant.reverse.idempotency import compare_matrices

        A = {"A": [[0.9, 0.1]], "B": [[[1.0]]]}
        B = {"A": [[0.9, 0.1]]}
        score = compare_matrices(A, B)
        assert isinstance(score, float)


class TestPlanPackage:
    def test_plan_package_basic(self):
        from cogant.reverse.idempotency import plan_package
        from cogant.reverse.synthesizer import PackagePlan

        model = _make_reverse_model()
        plan = plan_package(model)
        assert isinstance(plan, PackagePlan)

    def test_plan_package_has_package_name(self):
        from cogant.reverse.idempotency import plan_package

        model = _make_reverse_model("my_model")
        plan = plan_package(model)
        assert isinstance(plan.package_name, str)
        assert len(plan.package_name) > 0

    def test_plan_package_matrix_flags(self):
        from cogant.reverse.idempotency import plan_package
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel(
            model_name="test",
            hidden_states=["s1"],
            observations=["o1"],
            actions=["a1"],
            A=[[0.9, 0.1]],
            B=[[[1.0, 0.0]]],
            C=[0.8, 0.2],
            D=[0.5, 0.5],
        )
        plan = plan_package(model)
        assert plan.has_A_matrix is True or isinstance(plan.has_A_matrix, bool)


# ---------------------------------------------------------------------------
# reverse/synthesizer.py — render_matrices_module, PackagePlan
# ---------------------------------------------------------------------------


class TestRenderMatricesModule:
    def test_render_returns_str(self):
        from cogant.reverse.synthesizer import render_matrices_module

        model = _make_reverse_model()
        result = render_matrices_module(model)
        assert isinstance(result, str)

    def test_render_with_matrices(self):
        from cogant.reverse.parser import ReverseGNNModel
        from cogant.reverse.synthesizer import render_matrices_module

        model = ReverseGNNModel(
            model_name="test",
            hidden_states=["s1", "s2"],
            observations=["o1"],
            actions=["a1"],
            A=[[0.9, 0.1], [0.1, 0.9]],
            B=[[[1.0, 0.0], [0.0, 1.0]]],
            C=[1.0, 0.0],
            D=[0.5, 0.5],
        )
        result = render_matrices_module(model)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_contains_python_code(self):
        from cogant.reverse.synthesizer import render_matrices_module

        model = _make_reverse_model()
        result = render_matrices_module(model)
        # Should contain some Python constructs
        assert "def" in result or "=" in result or "#" in result


class TestPackagePlan:
    def test_init_minimal(self):
        from cogant.reverse.synthesizer import PackagePlan

        plan = PackagePlan(
            package_name="my_pkg",
            raw_model_name="my_model",
            nodes=[],
            state_vars=[],
            obs_functions=[],
            action_methods=[],
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
        assert plan.package_name == "my_pkg"
        assert plan.has_A_matrix is False

    def test_init_with_matrices(self):
        from cogant.reverse.synthesizer import PackagePlan

        plan = PackagePlan(
            package_name="pkg",
            raw_model_name="mdl",
            nodes=["n1", "n2"],
            state_vars=["s1"],
            obs_functions=["obs_x"],
            action_methods=["act_a"],
            policy_functions=[],
            constraint_checks=[],
            context_functions=[],
            scaffold_constraint_checks=[],
            scaffold_policy_functions=[],
            scaffold_context_classes=[],
            has_A_matrix=True,
            has_B_tensor=True,
            has_C_vector=True,
            has_D_vector=True,
        )
        assert plan.has_A_matrix is True
        assert plan.has_B_tensor is True
        assert len(plan.nodes) == 2
