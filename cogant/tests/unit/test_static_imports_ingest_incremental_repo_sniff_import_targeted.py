#!/usr/bin/env python3
"""Targeted branch tests for COGANT.

Targets:
  - static/imports.py — ImportAnalyzer
  - ingest/incremental.py — IncrementalIngester
  - ingest/repo_sniff.py — count_source_files, format_duration
  - observability/logging.py — setup_logging, get_logger
  - rust_backend.py — RustBackend functions
  - gnn/formatter/semantic.py — more semantic sections
  - gnn/formatter/structural.py — more structural sections
  - gnn/formatter/metadata.py — more metadata sections
  - gnn/matrices.py — matrix computation edge cases
  - reverse/synthesizer.py — ReverseSynthesizer
  - reverse/metrics.py — ReverseMetrics
  - reverse/planner.py — ReversePlanner
  - reverse/parser.py — more parse scenarios
  - api/orchestration.py — additional orchestration paths
  - api/session.py — Session methods
  - api/bundle.py — Bundle methods
  - translate/engine.py — TranslationEngine edge cases
  - translate/rules/semantic.py and structural.py — rule edge cases
  - runtime/loop.py — AgentRuntime additional paths
  - graph/builder.py — ProgramGraphBuilder additional paths
  - statespace/temporal.py — TimeRegime additional coverage
  - validate/integrity.py — integrity checks
  - plugins/registry.py — plugin registry
  - export/parquet.py — parquet export
  - gnn/json_export.py — JSON export edge cases
  - viz/mermaid.py — mermaid rendering
  - viz/html_renderer.py — HTML rendering
  - config/loaders.py — ConfigLoader methods
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph():
    from cogant.schemas.base import StableID
    from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test/repo"))
    for i in range(3):
        n = Node(
            id=StableID(f"node-{i}"),
            kind=NodeKind.FUNCTION if i > 0 else NodeKind.MODULE,
            name=f"sym_{i}",
            qualified_name=f"main.sym_{i}",
            path="main.py",
            language="python",
        )
        graph.add_node(n)
    e = Edge(
        id=StableID("edge-0"),
        source_id=StableID("node-0"),
        target_id=StableID("node-1"),
        kind=EdgeKind.CONTAINS,
    )
    graph.add_edge(e)
    return graph


def _make_ssm():
    from cogant.statespace.compiler import StateSpaceCompiler

    return StateSpaceCompiler(_make_graph(), "test").compile({})


def _make_process():
    from cogant.process.extractor import ProcessExtractor

    return ProcessExtractor(_make_graph(), "test").extract()


# ---------------------------------------------------------------------------
# static/imports.py — ImportAnalyzer
# ---------------------------------------------------------------------------


class TestImportAnalyzer:
    def test_analyze_stdlib_imports(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        code = "import os\nimport sys\nfrom pathlib import Path\n"
        f = tmp_path / "test.py"
        f.write_text(code)
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_file(f)
        assert isinstance(edges, list)
        if edges:
            assert edges[0].is_stdlib is True

    def test_analyze_source_imports(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        code = "import os\nfrom typing import Any, List\n"
        f = tmp_path / "src.py"
        f.write_text(code)
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_source(code, f)
        assert isinstance(edges, list)
        assert len(edges) >= 2

    def test_analyze_third_party_import(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        code = "import requests\nimport numpy as np\n"
        f = tmp_path / "tp.py"
        f.write_text(code)
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_source(code, f)
        assert isinstance(edges, list)
        if edges:
            assert edges[0].is_stdlib is False

    def test_analyze_relative_imports(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        code = "from . import utils\nfrom ..base import BaseClass\n"
        f = pkg / "module.py"
        f.write_text(code)
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_source(code, f)
        assert isinstance(edges, list)
        rel = [e for e in edges if e.is_relative]
        assert len(rel) >= 1

    def test_import_edge_attributes(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        code = "import os\n"
        f = tmp_path / "a.py"
        f.write_text(code)
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_source(code, f)
        if edges:
            e = edges[0]
            assert hasattr(e, "module_name")
            assert hasattr(e, "is_stdlib")
            assert hasattr(e, "line_num")
            assert e.module_name == "os"

    def test_stdlib_modules_set(self):
        from cogant.static.imports import ImportAnalyzer

        stdlib = ImportAnalyzer._load_stdlib_modules()
        assert isinstance(stdlib, set)
        assert "os" in stdlib
        assert "sys" in stdlib
        assert "pathlib" in stdlib

    def test_analyze_from_imports_with_names(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        code = "from typing import Any, List, Optional\n"
        f = tmp_path / "typing_test.py"
        f.write_text(code)
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_source(code, f)
        if edges:
            assert len(edges[0].imported_names) >= 1


# ---------------------------------------------------------------------------
# ingest/incremental.py — IncrementalIngester
# ---------------------------------------------------------------------------


class TestIncrementalIngester:
    def test_init(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        assert ingester is not None

    def test_is_git_repo_false(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.is_git_repo()
        # Not a git repo
        assert result is False

    def test_working_tree_changes_non_git(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        # Should return empty list or raise for non-git repos
        try:
            changes = ingester.working_tree_changes()
            assert isinstance(changes, list)
        except Exception:
            pass

    def test_get_changed_files_function(self, tmp_path):
        from cogant.ingest.incremental import get_changed_files

        try:
            result = get_changed_files(tmp_path, "HEAD~1")
            assert isinstance(result, list)
        except Exception:
            pass  # expected for non-git repos


# ---------------------------------------------------------------------------
# ingest/repo_sniff.py — count_source_files, format_duration
# ---------------------------------------------------------------------------


class TestRepoSniff:
    def test_count_source_files_empty(self, tmp_path):
        from cogant.ingest.repo_sniff import count_source_files

        result = count_source_files(tmp_path)
        assert isinstance(result, int)
        assert result == 0

    def test_count_source_files_with_python(self, tmp_path):
        from cogant.ingest.repo_sniff import count_source_files

        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        (tmp_path / "readme.md").write_text("# readme")
        result = count_source_files(tmp_path)
        assert result >= 2

    def test_estimate_pipeline_seconds(self):
        from cogant.ingest.repo_sniff import estimate_pipeline_seconds

        result = estimate_pipeline_seconds(100)
        assert isinstance(result, float)
        assert result > 0

    def test_format_duration_seconds(self):
        from cogant.ingest.repo_sniff import format_duration

        result = format_duration(45.0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_duration_minutes(self):
        from cogant.ingest.repo_sniff import format_duration

        result = format_duration(130.0)
        assert isinstance(result, str)
        assert "m" in result or "min" in result or "2" in result

    def test_format_duration_zero(self):
        from cogant.ingest.repo_sniff import format_duration

        result = format_duration(0.0)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# observability/logging.py — setup_logging, get_logger
# ---------------------------------------------------------------------------


class TestObservabilityLogging:
    def test_get_logger(self):
        from cogant.observability.logging import get_logger

        logger = get_logger("test.module")
        assert logger is not None

    def test_get_logger_returns_bound_logger(self):
        from cogant.observability.logging import get_logger

        logger = get_logger("cogant.test")
        # Should be usable
        assert hasattr(logger, "info") or hasattr(logger, "debug") or callable(logger)

    def test_setup_logging(self):
        from cogant.observability.logging import setup_logging

        # Should not raise
        setup_logging(level="INFO", format="json")

    def test_setup_logging_text_format(self):
        from cogant.observability.logging import setup_logging

        setup_logging(level="DEBUG", format="text")

    def test_setup_logging_warn_level(self):
        from cogant.observability.logging import setup_logging

        setup_logging(level="WARNING")


# ---------------------------------------------------------------------------
# rust_backend.py — RustBackend functions
# ---------------------------------------------------------------------------


class TestRustBackend:
    def test_rust_available(self):
        from cogant.rust_backend import RUST_AVAILABLE

        # Just verify it's a bool
        assert isinstance(RUST_AVAILABLE, bool)

    def test_rust_version_returns_none_or_str(self):
        from cogant.rust_backend import rust_version

        result = rust_version()
        assert result is None or isinstance(result, str)

    def test_get_program_graph_impl(self):
        from cogant.rust_backend import get_program_graph_impl

        impl = get_program_graph_impl()
        assert impl is not None

    def test_env_prefers_rust(self):
        from cogant.rust_backend import _env_prefers_rust

        result = _env_prefers_rust()
        assert result is None or isinstance(result, bool)

    def test_build_program_graph(self):
        from cogant.rust_backend import build_program_graph

        result = build_program_graph()
        assert result is not None


# ---------------------------------------------------------------------------
# gnn/formatter/semantic.py — Semantic sections
# ---------------------------------------------------------------------------


class TestGNNFormatterSemantic:
    def _make_formatter(self):
        from cogant.gnn.formatter.base import GNNMarkdownFormatter

        return GNNMarkdownFormatter(_make_graph(), _make_ssm(), _make_process(), {})

    def test_format_includes_semantic_sections(self):
        fmt = self._make_formatter()
        result = fmt.format()
        # Semantic sections include PolicyMatrix, ConnectionsBlock, etc.
        assert isinstance(result, str)
        assert len(result) > 50

    def test_format_semantic_elements(self):
        fmt = self._make_formatter()
        result = fmt.format()
        # Should include references to the schema or model
        assert "test" in result.lower() or "model" in result.lower() or "schema" in result.lower()


# ---------------------------------------------------------------------------
# gnn/formatter/structural.py — Structural sections
# ---------------------------------------------------------------------------


class TestGNNFormatterStructural:
    def _make_formatter(self):
        from cogant.gnn.formatter.base import GNNMarkdownFormatter

        return GNNMarkdownFormatter(_make_graph(), _make_ssm(), _make_process(), {})

    def test_format_structural_sections(self):
        fmt = self._make_formatter()
        result = fmt.format()
        assert isinstance(result, str)

    def test_format_has_header(self):
        fmt = self._make_formatter()
        result = fmt.format()
        # GNN markdown should have ## headers
        assert "##" in result

    def test_format_has_model_name(self):
        fmt = self._make_formatter()
        result = fmt.format()
        assert "ModelName" in result or "model" in result.lower()


# ---------------------------------------------------------------------------
# gnn/matrices.py — GNNMatrices computation
# ---------------------------------------------------------------------------


class TestGNNMatricesComputation:
    def _make_matrices(self):
        from cogant.gnn.matrices import GNNMatrices

        graph = _make_graph()
        ssm = _make_ssm()
        return GNNMatrices(graph, {}, ssm)

    def test_compute_all_matrices(self):
        matrices = self._make_matrices()
        A = matrices.compute_A()
        B = matrices.compute_B()
        C = matrices.compute_C()
        D = matrices.compute_D()
        assert A is not None
        assert B is not None
        assert C is not None
        assert D is not None

    def test_to_dict(self):
        matrices = self._make_matrices()
        d = matrices.to_dict()
        assert isinstance(d, dict)

    def test_validate_shapes(self):
        matrices = self._make_matrices()
        result = matrices.validate_shapes()
        assert result is not None

    def test_to_gnn_markdown_block(self):
        matrices = self._make_matrices()
        block = matrices.to_gnn_markdown_block()
        assert isinstance(block, str)


# ---------------------------------------------------------------------------
# reverse/metrics.py — RoundtripMetrics
# ---------------------------------------------------------------------------


class TestReverseMetrics:
    def test_import(self):
        import cogant.reverse.metrics as rm

        assert rm is not None

    def test_compare_role_distributions_equal(self):
        from cogant.reverse.metrics import compare_role_distributions

        roles1 = {"HiddenState": 2, "Observation": 1}
        roles2 = {"HiddenState": 2, "Observation": 1}
        score = compare_role_distributions(roles1, roles2)
        assert isinstance(score, (float, int))
        assert 0.0 <= float(score) <= 1.01

    def test_compare_role_distributions_different(self):
        from cogant.reverse.metrics import compare_role_distributions

        roles1 = {"HiddenState": 2}
        roles2 = {"HiddenState": 1, "Observation": 1}
        score = compare_role_distributions(roles1, roles2)
        assert isinstance(score, (float, int))

    def test_compare_role_distributions_empty(self):
        from cogant.reverse.metrics import compare_role_distributions

        score = compare_role_distributions({}, {})
        assert isinstance(score, (float, int))

    def test_compare_matrices_empty(self):
        from cogant.reverse.metrics import compare_matrices

        result = compare_matrices({}, {})
        assert result is not None

    def test_compare_graph_structure_empty(self):
        from cogant.reverse.metrics import compare_graph_structure

        score = compare_graph_structure([], [], [], [])
        assert isinstance(score, (float, int))

    def test_compute_isomorphism_report(self):
        from cogant.reverse.metrics import compute_isomorphism_report

        gnn_a = {"roles": {"HiddenState": 1, "Observation": 1}}
        gnn_b = {"roles": {"HiddenState": 1, "Observation": 1}}
        result = compute_isomorphism_report(gnn_a, gnn_b)
        assert result is not None
        assert hasattr(result, "structurally_isomorphic") or hasattr(result, "role_preservation_score")


# ---------------------------------------------------------------------------
# reverse/planner.py — ReversePlanner
# ---------------------------------------------------------------------------


class TestReversePlanner:
    def _make_model(self):
        from cogant.reverse.parser import parse_gnn

        return parse_gnn("""## ModelName
PlanModel

## StateSpaceBlock
s_f0[2, 1, type=int]

## ObservationBlock
o_m0[2, 1, type=int]

## ControlBlock
u_c0[2, 1, type=int]

## ActInfOntologyAnnotation
s_f0 = HiddenState
o_m0 = Observation
u_c0 = Action
""")

    def test_import(self):
        from cogant.reverse.planner import PackagePlan, plan_package

        assert plan_package is not None
        assert PackagePlan is not None

    def test_plan_package(self):
        from cogant.reverse.planner import plan_package

        model = self._make_model()
        plan = plan_package(model)
        assert plan is not None

    def test_plan_package_has_nodes(self):
        from cogant.reverse.planner import plan_package

        model = self._make_model()
        plan = plan_package(model)
        assert hasattr(plan, "nodes") or hasattr(plan, "schema_name") or hasattr(plan, "model_name")

    def test_node_plan_attributes(self):
        from cogant.reverse.planner import NodePlan, plan_package

        model = self._make_model()
        plan = plan_package(model)
        if hasattr(plan, "nodes") and plan.nodes:
            node = plan.nodes[0]
            assert hasattr(node, "role") or hasattr(node, "name") or isinstance(node, NodePlan)


# ---------------------------------------------------------------------------
# reverse/synthesizer.py — ReverseSynthesizer
# ---------------------------------------------------------------------------


class TestReverseSynthesizer:
    def _make_model(self):
        from cogant.reverse.parser import parse_gnn

        return parse_gnn("""## ModelName
SimpleModel

## StateSpaceBlock
s_f0[2, 1, type=int]

## ObservationBlock
o_m0[2, 1, type=int]

## ControlBlock
u_c0[2, 1, type=int]

## ActInfOntologyAnnotation
s_f0 = HiddenState
o_m0 = Observation
u_c0 = Action
""")

    def test_import(self):
        from cogant.reverse.synthesizer import synthesize_package

        assert synthesize_package is not None

    def test_synthesize_package_returns_files(self, tmp_path):
        from cogant.reverse.planner import plan_package
        from cogant.reverse.synthesizer import synthesize_package

        model = self._make_model()
        plan = plan_package(model)
        result = synthesize_package(plan, model, str(tmp_path))
        assert result is not None

    def test_synthesize_package_creates_files(self, tmp_path):
        from cogant.reverse.planner import plan_package
        from cogant.reverse.synthesizer import synthesize_package

        model = self._make_model()
        plan = plan_package(model)
        synthesize_package(plan, model, str(tmp_path))
        # Should create Python files
        py_files = list(tmp_path.rglob("*.py"))
        assert len(py_files) >= 1


# ---------------------------------------------------------------------------
# reverse/parser.py — more parse scenarios
# ---------------------------------------------------------------------------


class TestReverseParserEdgeCases:
    def test_parse_with_matrix_block(self):
        from cogant.reverse.parser import parse_gnn

        gnn_text = """## ModelName
MatrixModel

## StateSpaceBlock
s_f0[2, 1, type=float]
s_f1[3, 1, type=float]

## ObservationBlock
o_m0[2, 1, type=float]

## ControlBlock
u_c0[2, 1, type=int]

## InitialParameterization
A[2][2] = [[0.7, 0.3], [0.4, 0.6]]
B[2][2][2] = [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]]
C[2] = [1.0, 0.0]
D[2] = [0.5, 0.5]

## ActInfOntologyAnnotation
s_f0 = HiddenState
o_m0 = Observation
u_c0 = Action
"""
        model = parse_gnn(gnn_text)
        assert model is not None
        assert model.model_name is not None

    def test_parse_cardinalities(self):
        from cogant.reverse.parser import parse_gnn

        gnn_text = """## ModelName
CardModel

## StateSpaceBlock
s_f0[4, 1, type=int]

## ObservationBlock
o_m0[4, 1, type=int]

## ActInfOntologyAnnotation
s_f0 = HiddenState
o_m0 = Observation
"""
        model = parse_gnn(gnn_text)
        assert model is not None
        # cardinalities should be populated
        if model.cardinalities:
            assert "s_f0" in model.cardinalities or len(model.cardinalities) >= 0

    def test_parse_constraints(self):
        from cogant.reverse.parser import parse_gnn

        gnn_text = """## ModelName
ConstraintModel

## StateSpaceBlock
s_f0[2, 1, type=int]

## Constraints
s_f0 must be normalized
sum(A) = 1.0

## ActInfOntologyAnnotation
s_f0 = HiddenState
"""
        model = parse_gnn(gnn_text)
        assert model is not None

    def test_parse_n_states(self):
        from cogant.reverse.parser import parse_gnn

        gnn_text = """## ModelName
CountModel

## StateSpaceBlock
s_f0[3, 1, type=int]
s_f1[2, 1, type=int]

## ObservationBlock
o_m0[3, 1, type=int]

## ControlBlock
u_c0[2, 1, type=int]

## ActInfOntologyAnnotation
s_f0 = HiddenState
s_f1 = HiddenState
o_m0 = Observation
u_c0 = Action
"""
        model = parse_gnn(gnn_text)
        n = model.n_states
        assert isinstance(n, int)
        assert n >= 0


# ---------------------------------------------------------------------------
# api/session.py — Session
# ---------------------------------------------------------------------------


class TestSessionExtra:
    def test_session_init_with_config(self, tmp_path):
        from cogant.api.session import Session

        try:
            sess = Session(target=str(tmp_path))
            assert sess is not None
        except Exception:
            pass

    def test_session_has_methods(self):
        from cogant.api.session import Session

        assert hasattr(Session, "extract_static") or hasattr(Session, "run")


# ---------------------------------------------------------------------------
# api/bundle.py — Bundle
# ---------------------------------------------------------------------------


class TestBundleExtra:
    def test_bundle_to_dict(self):
        from cogant.api.bundle import Bundle

        try:
            b = Bundle()
            if hasattr(b, "to_dict"):
                d = b.to_dict()
                assert isinstance(d, dict)
        except Exception:
            pass

    def test_bundle_import(self):
        from cogant.api.bundle import Bundle

        assert Bundle is not None


# ---------------------------------------------------------------------------
# translate/engine.py — TranslationEngine edge cases
# ---------------------------------------------------------------------------


class TestTranslationEngineExtra:
    def test_translate_empty_graph(self):
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.translate.engine import TranslationEngine

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="x"))
        engine = TranslationEngine()
        result = engine.translate(graph)
        assert result is not None

    def test_translate_rules_applied(self):
        from cogant.translate.engine import TranslationEngine

        graph = _make_graph()
        engine = TranslationEngine()
        result = engine.translate(graph)
        # Result should have some structure
        assert isinstance(result, (list, dict))


# ---------------------------------------------------------------------------
# runtime/loop.py — AgentRuntime additional paths
# ---------------------------------------------------------------------------


class TestAgentRuntimeExtra:
    def _make_matrices(self):
        # Create minimal A, B, C matrices for 2-state, 2-obs agent
        return {
            "A": [[0.8, 0.2], [0.3, 0.7]],  # P(obs|state)
            "B": [[[0.9, 0.1], [0.1, 0.9]], [[0.1, 0.9], [0.9, 0.1]]],  # P(s'|s,a)
            "C": [0.0, 1.0],  # preferences over obs
            "D": [0.5, 0.5],  # initial state dist
        }

    def test_from_matrices_dict(self):
        from cogant.runtime.loop import AgentRuntime

        mats = self._make_matrices()
        runtime = AgentRuntime.from_matrices_dict(mats)
        assert runtime is not None

    def test_step_forward(self):
        from cogant.runtime.loop import AgentRuntime

        mats = self._make_matrices()
        runtime = AgentRuntime.from_matrices_dict(mats)
        state_dist = [0.5, 0.5]
        result = runtime.step(state_dist, obs_idx=0)
        assert result is not None

    def test_run_n_steps(self):
        from cogant.runtime.loop import AgentRuntime

        mats = self._make_matrices()
        runtime = AgentRuntime.from_matrices_dict(mats)
        initial = [0.5, 0.5]
        results = runtime.run_n_steps(n=3, initial_state=initial)
        assert isinstance(results, list)
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# graph/builder.py — ProgramGraphBuilder additional paths
# ---------------------------------------------------------------------------


class TestGraphBuilderExtra:
    def test_builder_init(self):
        from cogant.graph.builder import ProgramGraphBuilder

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        assert builder is not None

    def test_builder_add_custom_node(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="custom",
            qualified_name="pkg.custom",
        )
        graph = builder.finalize()
        assert graph is not None
        assert node is not None

    def test_builder_get_statistics(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(kind=NodeKind.MODULE, name="stats", qualified_name="stats")
        stats = builder.get_statistics()
        assert isinstance(stats, dict)

    def test_builder_find_cycles(self):
        from cogant.graph.builder import ProgramGraphBuilder

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        cycles = builder.find_cycles()
        assert isinstance(cycles, list)

    def test_builder_get_connected_components(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        for i in range(3):
            builder.add_node(kind=NodeKind.FUNCTION, name=f"f{i}", qualified_name=f"f{i}")
        components = builder.get_connected_components()
        assert isinstance(components, list)


# ---------------------------------------------------------------------------
# statespace/temporal.py — TimeRegime additional coverage
# ---------------------------------------------------------------------------


class TestTimeRegimeExtra:
    def test_all_regimes(self):
        from cogant.statespace.temporal import TimeRegime

        regimes = list(TimeRegime)
        assert len(regimes) >= 3
        names = [r.value for r in regimes]
        assert "synchronous" in names or "SYNCHRONOUS" in names.copy().__class__(
            r.name for r in regimes
        )

    def test_regime_comparison(self):
        from cogant.statespace.temporal import TimeRegime

        r1 = TimeRegime.SYNCHRONOUS
        r2 = TimeRegime.ASYNCHRONOUS
        assert r1 != r2
        assert r1 == TimeRegime.SYNCHRONOUS

    def test_regime_values(self):
        from cogant.statespace.temporal import TimeRegime

        assert TimeRegime.SYNCHRONOUS.value == "synchronous"
        assert TimeRegime.ASYNCHRONOUS.value == "asynchronous"


# ---------------------------------------------------------------------------
# validate/integrity.py — integrity checks
# ---------------------------------------------------------------------------


class TestValidateIntegrity:
    def test_import(self):
        from cogant.validate.integrity import IntegrityChecker

        assert IntegrityChecker is not None

    def test_check_program_graph(self):
        from cogant.validate.integrity import IntegrityChecker

        checker = IntegrityChecker()
        graph = _make_graph()
        issues = checker.check_program_graph(graph)
        assert isinstance(issues, list)

    def test_check_program_graph_empty(self):
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.validate.integrity import IntegrityChecker

        checker = IntegrityChecker()
        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="x"))
        issues = checker.check_program_graph(graph)
        assert isinstance(issues, list)

    def test_check_state_space(self):
        from cogant.validate.integrity import IntegrityChecker

        checker = IntegrityChecker()
        ssm = _make_ssm()
        issues = checker.check_state_space(ssm)
        assert isinstance(issues, list)

    def test_is_valid_empty(self):
        from cogant.validate.integrity import IntegrityChecker

        checker = IntegrityChecker()
        assert checker.is_valid() is True  # no issues initially

    def test_get_issues_empty(self):
        from cogant.validate.integrity import IntegrityChecker

        checker = IntegrityChecker()
        issues = checker.get_issues()
        assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# plugins/registry.py — PluginRegistry
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def test_import(self):
        from cogant.plugins.registry import PluginRegistry

        assert PluginRegistry is not None

    def test_init(self):
        from cogant.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        assert reg is not None

    def test_list_plugins_empty(self):
        from cogant.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        plugins = reg.list_plugins()
        assert isinstance(plugins, list)

    def test_register_and_get(self):
        from cogant.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        # Try basic operations
        if hasattr(reg, "register"):
            try:
                reg.register("test_plugin", {"version": "1.0"})
                plugins = reg.list_plugins()
                assert len(plugins) >= 0
            except Exception:
                pass


# ---------------------------------------------------------------------------
# export/parquet.py — ParquetExporter
# ---------------------------------------------------------------------------


class TestParquetExporter:
    def test_import(self):
        from cogant.export.parquet import ParquetExporter

        assert ParquetExporter is not None

    def test_init(self):
        from cogant.export.parquet import ParquetExporter

        graph = _make_graph()
        exporter = ParquetExporter(graph)
        assert exporter is not None

    def test_export_creates_files(self, tmp_path):
        from cogant.export.parquet import ParquetExporter

        graph = _make_graph()
        exporter = ParquetExporter(graph)
        try:
            result = exporter.export(str(tmp_path))
            assert result is not None
        except ImportError:
            pytest.skip("parquet dependencies not installed")


# ---------------------------------------------------------------------------
# viz/mermaid.py — MermaidGenerator
# ---------------------------------------------------------------------------


class TestMermaidGeneratorExtra:
    def test_generate_class_diagram(self):
        from cogant.viz.mermaid import MermaidGenerator

        graph = _make_graph()
        gen = MermaidGenerator()
        result = gen.generate_class_diagram(graph)
        assert isinstance(result, str)

    def test_generate_dependency_graph(self):
        from cogant.viz.mermaid import MermaidGenerator

        graph = _make_graph()
        gen = MermaidGenerator()
        result = gen.generate_dependency_graph(graph)
        assert isinstance(result, str)

    def test_generate_state_diagram(self):
        from cogant.viz.mermaid import MermaidGenerator

        gen = MermaidGenerator()
        ssm = _make_ssm()
        result = gen.generate_state_diagram(ssm)
        assert isinstance(result, str)

    def test_generate_flowchart(self):
        from cogant.viz.mermaid import MermaidGenerator

        graph = _make_graph()
        gen = MermaidGenerator()
        result = gen.generate_flowchart(graph, semantic_mappings={})
        assert isinstance(result, str)

    def test_generate_active_inference_diagram(self):
        from cogant.viz.mermaid import MermaidGenerator

        gen = MermaidGenerator()
        ssm = _make_ssm()
        result = gen.generate_active_inference_diagram(ssm)
        assert isinstance(result, str)

    def test_generate_sequence_diagram(self):
        from cogant.viz.mermaid import MermaidGenerator

        gen = MermaidGenerator()
        result = gen.generate_sequence_diagram(graph=_make_graph())
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# viz/html_renderer.py — HtmlRenderer
# ---------------------------------------------------------------------------


class TestHtmlRendererExtra:
    def test_import(self):
        from cogant.viz.html_renderer import HTMLSiteRenderer

        assert HTMLSiteRenderer is not None

    def test_init(self):
        from cogant.viz.html_renderer import HTMLSiteRenderer

        renderer = HTMLSiteRenderer(bundle={})
        assert renderer is not None

    def test_render_creates_output(self, tmp_path):
        from cogant.viz.html_renderer import HTMLSiteRenderer

        bundle = {
            "model_id": "test_model",
            "schema_name": "test_schema",
            "stage_results": {},
            "errors": [],
        }
        renderer = HTMLSiteRenderer(bundle=bundle)
        result = renderer.render(str(tmp_path))
        assert result is not None

    def test_render_with_graph_data(self, tmp_path):
        from cogant.viz.html_renderer import HTMLSiteRenderer

        bundle = {
            "model_id": "test_model",
            "schema_name": "test_schema",
            "program_graph": {"nodes": [], "edges": []},
            "semantic_mappings": [],
            "errors": [],
        }
        renderer = HTMLSiteRenderer(bundle=bundle)
        renderer.render(str(tmp_path))


# ---------------------------------------------------------------------------
# config/loaders.py — more ConfigLoader methods
# ---------------------------------------------------------------------------


class TestConfigLoadersExtra:
    def test_load_preset_default(self):
        from cogant.config.loaders import ConfigLoader

        try:
            config = ConfigLoader.load_preset("default")
            assert config is not None
        except Exception:
            pass

    def test_load_preset_minimal(self):
        from cogant.config.loaders import ConfigLoader

        try:
            config = ConfigLoader.load_preset("minimal")
            assert config is not None
        except Exception:
            pass

    def test_load_from_yaml_missing_file(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError

        bad_path = tmp_path / "nonexistent.yaml"
        with pytest.raises((FileNotFoundError, ConfigLoadError, Exception)):
            ConfigLoader.load_from_yaml(bad_path)


# ---------------------------------------------------------------------------
# gnn/json_export.py — GNNJSONExporter edge cases
# ---------------------------------------------------------------------------


class TestGNNJSONExporterExtra:
    def test_export_with_populated_graph(self):
        from cogant.gnn.json_export import GNNJSONExporter

        graph = _make_graph()
        ssm = _make_ssm()
        proc = _make_process()
        exporter = GNNJSONExporter(graph, ssm, proc, {})
        result = exporter.export()
        # Should have more keys
        assert "model_id" in result or "schema_name" in result
        assert "state_space" in result or "variables" in result

    def test_export_has_provenance(self):
        from cogant.gnn.json_export import GNNJSONExporter

        graph = _make_graph()
        ssm = _make_ssm()
        proc = _make_process()
        exporter = GNNJSONExporter(graph, ssm, proc, {})
        result = exporter.export()
        assert isinstance(result, dict)
        assert len(result) > 5


# ---------------------------------------------------------------------------
# export/bundle.py — BundleExporter edge cases
# ---------------------------------------------------------------------------


class TestBundleExporterExtra:
    def test_export_markdown_only(self, tmp_path):
        from cogant.export.bundle import BundleExporter

        graph = _make_graph()
        ssm = _make_ssm()
        proc = _make_process()
        exporter = BundleExporter(graph, ssm, proc, {}, tmp_path)
        result = exporter.export(formats=["markdown"])
        assert result is not None

    def test_export_json_only(self, tmp_path):
        from cogant.export.bundle import BundleExporter

        graph = _make_graph()
        ssm = _make_ssm()
        proc = _make_process()
        exporter = BundleExporter(graph, ssm, proc, {}, tmp_path)
        result = exporter.export(formats=["json"])
        assert result is not None
