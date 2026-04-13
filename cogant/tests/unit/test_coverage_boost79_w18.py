#!/usr/bin/env python3
"""Coverage boost batch 79 — reverse/cli.py rendering helpers,
rust_backend.py public functions, dynamic/enrichment.py extended,
static/dataflow.py and static/calls.py edge cases.

Covers:
- reverse/cli.py: _render_plan_summary, _render_roundtrip_result
  (both isomorphic and drift with shape_match, errors, package_path)
- rust_backend.py: get_program_graph_impl, rust_version, create_example_graph,
  build_program_graph (pure-Python path), _env_prefers_rust,
  RustProgramGraphAdapter.__init__ (Rust-unavailable path)
- dynamic/enrichment.py: enrich_graph with coverage/trace file found
  (_enrich_with_coverage, _enrich_with_trace inner paths), _build_function_index
- static/dataflow.py: DataFlowAnalyzer additional flow shapes
- static/calls.py: CallGraphBuilder additional call shapes
- static/parser.py: additional attribute and import patterns
"""

import os
import json
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind
    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_roundtrip_result(**kwargs):
    from cogant.reverse.idempotency import RoundtripResult
    return RoundtripResult(**kwargs)


# ---------------------------------------------------------------------------
# reverse/cli.py — _render_plan_summary and _render_roundtrip_result
# ---------------------------------------------------------------------------

class TestReverseCLIRendering:
    def test_render_plan_summary_basic(self, tmp_path):
        from cogant.reverse.cli import _render_plan_summary
        # Should run without error
        _render_plan_summary(
            gnn_path=tmp_path / "model.gnn.md",
            package_path=tmp_path / "pkg",
            state_count=2,
            obs_count=1,
            action_count=1,
            policy_count=0,
            constraint_count=0,
        )

    def test_render_plan_summary_zeros(self, tmp_path):
        from cogant.reverse.cli import _render_plan_summary
        _render_plan_summary(
            gnn_path=tmp_path / "empty.gnn.md",
            package_path=tmp_path / "out",
            state_count=0,
            obs_count=0,
            action_count=0,
            policy_count=0,
            constraint_count=0,
        )

    def test_render_roundtrip_result_isomorphic(self):
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=True,
            role_match_score=0.9,
            original_roles={"HIDDEN_STATE": 2, "OBSERVATION": 1},
            synthesized_roles={"HIDDEN_STATE": 2, "OBSERVATION": 1},
            shape_match={"n_states": True, "n_obs": True},
        )
        # Should print Rich table without error
        _render_roundtrip_result(result, threshold=0.5)

    def test_render_roundtrip_result_drift(self):
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=False,
            role_match_score=0.2,
            original_roles={"HIDDEN_STATE": 3},
            synthesized_roles={"OBSERVATION": 1},
            shape_match={"n_states": False},
            errors=["forward pipeline failed"],
        )
        _render_roundtrip_result(result, threshold=0.5)

    def test_render_roundtrip_result_with_package_path(self, tmp_path):
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=True,
            role_match_score=1.0,
            original_roles={},
            synthesized_roles={},
            package_path=tmp_path / "pkg",
        )
        _render_roundtrip_result(result, threshold=0.5)

    def test_render_roundtrip_result_empty_roles(self):
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=True,
            role_match_score=1.0,
            original_roles={},
            synthesized_roles={},
        )
        _render_roundtrip_result(result, threshold=0.0)

    def test_render_roundtrip_result_no_shape_match(self):
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=False,
            role_match_score=0.3,
            original_roles={"ACTION": 2},
            synthesized_roles={},
            shape_match={},  # empty
            errors=[],
        )
        _render_roundtrip_result(result, threshold=0.5)


# ---------------------------------------------------------------------------
# rust_backend.py — public API (Rust unavailable path)
# ---------------------------------------------------------------------------

class TestRustBackend:
    def test_rust_available_is_bool(self):
        from cogant.rust_backend import RUST_AVAILABLE
        assert isinstance(RUST_AVAILABLE, bool)

    def test_rust_version_returns_none_or_str(self):
        from cogant.rust_backend import rust_version
        result = rust_version()
        assert result is None or isinstance(result, str)

    def test_get_program_graph_impl_returns_class(self):
        from cogant.rust_backend import get_program_graph_impl
        cls = get_program_graph_impl()
        assert cls is not None
        # Should be callable (a class)
        assert callable(cls)

    def test_create_example_graph_raises_when_no_rust(self):
        from cogant.rust_backend import create_example_graph, RUST_AVAILABLE
        if not RUST_AVAILABLE:
            with pytest.raises(RuntimeError):
                create_example_graph()
        else:
            # If Rust is available, it should return something
            result = create_example_graph()
            assert result is not None

    def test_rust_adapter_init_raises_when_no_rust(self):
        from cogant.rust_backend import RustProgramGraphAdapter, RUST_AVAILABLE
        if not RUST_AVAILABLE:
            with pytest.raises(RuntimeError):
                RustProgramGraphAdapter("repo://test")

    def test_build_program_graph_returns_builder(self):
        from cogant.rust_backend import build_program_graph
        builder = build_program_graph("repo://test", use_rust=False)
        assert builder is not None
        assert hasattr(builder, "add_node")
        assert hasattr(builder, "add_edge")
        assert hasattr(builder, "finalize")

    def test_build_program_graph_auto_uses_python_fallback(self):
        """When COGANT_USE_RUST=0, always gets Python builder."""
        env_backup = os.environ.get("COGANT_USE_RUST")
        try:
            os.environ["COGANT_USE_RUST"] = "0"
            from cogant.rust_backend import build_program_graph
            builder = build_program_graph("repo://test")
            assert builder is not None
        finally:
            if env_backup is None:
                os.environ.pop("COGANT_USE_RUST", None)
            else:
                os.environ["COGANT_USE_RUST"] = env_backup

    def test_env_prefers_rust_false(self):
        from cogant.rust_backend import _env_prefers_rust
        env_backup = os.environ.get("COGANT_USE_RUST")
        try:
            os.environ["COGANT_USE_RUST"] = "0"
            assert _env_prefers_rust() is False
        finally:
            if env_backup is None:
                os.environ.pop("COGANT_USE_RUST", None)
            else:
                os.environ["COGANT_USE_RUST"] = env_backup

    def test_env_prefers_rust_true(self):
        from cogant.rust_backend import _env_prefers_rust
        env_backup = os.environ.get("COGANT_USE_RUST")
        try:
            os.environ["COGANT_USE_RUST"] = "1"
            assert _env_prefers_rust() is True
        finally:
            if env_backup is None:
                os.environ.pop("COGANT_USE_RUST", None)
            else:
                os.environ["COGANT_USE_RUST"] = env_backup

    def test_env_prefers_rust_none(self):
        from cogant.rust_backend import _env_prefers_rust
        env_backup = os.environ.get("COGANT_USE_RUST")
        try:
            os.environ.pop("COGANT_USE_RUST", None)
            result = _env_prefers_rust()
            assert result is None
        finally:
            if env_backup is not None:
                os.environ["COGANT_USE_RUST"] = env_backup

    def test_env_prefers_rust_invalid_string(self):
        from cogant.rust_backend import _env_prefers_rust
        env_backup = os.environ.get("COGANT_USE_RUST")
        try:
            os.environ["COGANT_USE_RUST"] = "maybe"
            result = _env_prefers_rust()
            assert result is None
        finally:
            if env_backup is None:
                os.environ.pop("COGANT_USE_RUST", None)
            else:
                os.environ["COGANT_USE_RUST"] = env_backup

    def test_build_program_graph_full_pipeline(self):
        """Build a complete graph using pure-Python backend."""
        from cogant.rust_backend import build_program_graph
        from cogant.schemas.core import NodeKind, EdgeKind
        builder = build_program_graph("repo://test", use_rust=False)
        n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
        builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
        graph = builder.finalize()
        assert graph is not None
        assert len(graph.nodes) == 2


# ---------------------------------------------------------------------------
# dynamic/enrichment.py — enrich_graph with JSON files
# ---------------------------------------------------------------------------

class TestEnrichGraphWithFiles:
    def test_enrich_with_valid_coverage_json(self, tmp_path):
        from cogant.dynamic.enrichment import enrich_graph
        # Build minimal coverage.json with spans
        cov_data = {
            "spans": [
                {"file": "mod.py", "start_line": 1, "end_line": 5,
                 "covered": True, "is_branch": False},
            ]
        }
        cov_path = tmp_path / "coverage.json"
        cov_path.write_text(json.dumps(cov_data))

        graph = _make_graph_with_nodes()
        result = enrich_graph(graph, coverage_path=str(cov_path))
        assert isinstance(result, dict)

    def test_enrich_with_invalid_coverage_json(self, tmp_path):
        from cogant.dynamic.enrichment import enrich_graph
        cov_path = tmp_path / "bad_cov.json"
        cov_path.write_text("not json at all {{{")
        graph = _make_graph_with_nodes()
        # Should not raise — just skip or return partial result
        result = enrich_graph(graph, coverage_path=str(cov_path))
        assert isinstance(result, dict)

    def test_enrich_with_empty_coverage_spans(self, tmp_path):
        from cogant.dynamic.enrichment import enrich_graph
        cov_data = {"spans": []}
        cov_path = tmp_path / "cov.json"
        cov_path.write_text(json.dumps(cov_data))
        graph = _make_graph_with_nodes()
        result = enrich_graph(graph, coverage_path=str(cov_path))
        assert isinstance(result, dict)

    def test_build_function_index_names(self):
        from cogant.dynamic.enrichment import _build_function_index
        graph = _make_graph_with_nodes()
        index = _build_function_index(graph)
        assert isinstance(index, dict)
        # fn should be in the index
        assert any("fn" in k for k in index)


# ---------------------------------------------------------------------------
# static/dataflow.py — DataFlowAnalyzer edge cases
# ---------------------------------------------------------------------------

class TestDataFlowEdgeCases:
    def test_analyze_source_for_loop(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer
        analyzer = DataFlowAnalyzer()
        src = "for i in range(10):\n    total = i\n"
        fp = tmp_path / "for.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_while_loop(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer
        analyzer = DataFlowAnalyzer()
        src = "n = 0\nwhile n < 10:\n    n += 1\n"
        fp = tmp_path / "while.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_import(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer
        analyzer = DataFlowAnalyzer()
        src = "import os\nfrom pathlib import Path\n"
        fp = tmp_path / "imports.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_with_walrus_operator(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer
        analyzer = DataFlowAnalyzer()
        src = "data = [1, 2, 3, 4, 5]\nif n := len(data):\n    print(n)\n"
        fp = tmp_path / "walrus.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)


# ---------------------------------------------------------------------------
# static/calls.py — CallGraphBuilder edge cases
# ---------------------------------------------------------------------------

class TestCallGraphEdgeCases:
    def test_extract_calls_from_source_comprehension(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder
        builder = CallGraphBuilder()
        src = "result = [str(x) for x in range(10)]\n"
        fp = tmp_path / "comp.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_source_async_call(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder
        builder = CallGraphBuilder()
        src = "async def main():\n    result = await fetch('url')\n"
        fp = tmp_path / "async.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_source_decorator(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder
        builder = CallGraphBuilder()
        src = "@app.route('/path')\ndef view():\n    return render()\n"
        fp = tmp_path / "dec.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_source_multiple_returns(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder
        builder = CallGraphBuilder()
        src = """
def process(x):
    if x > 0:
        return abs(x)
    return min(x, -1)
"""
        fp = tmp_path / "multi.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)


# ---------------------------------------------------------------------------
# static/parser.py — additional patterns
# ---------------------------------------------------------------------------

class TestPythonASTParserAdditional:
    def _make_parser(self):
        from cogant.static.parser import PythonASTParser
        return PythonASTParser()

    def test_parse_string_multiple_classes(self, tmp_path):
        parser = self._make_parser()
        src = """
class A:
    pass

class B(A):
    def method(self):
        pass

class C:
    x: int = 0
"""
        fp = tmp_path / "multi.py"
        module = parser.parse_string(src)
        assert len(module.classes) == 3

    def test_parse_string_nested_function(self, tmp_path):
        parser = self._make_parser()
        src = """
def outer():
    def inner():
        return 42
    return inner
"""
        fp = tmp_path / "nested.py"
        module = parser.parse_string(src)
        assert len(module.functions) >= 1

    def test_parse_string_walrus_in_while(self, tmp_path):
        parser = self._make_parser()
        src = "data = []\nwhile chunk := input():\n    data.append(chunk)\n"
        fp = tmp_path / "walrus.py"
        module = parser.parse_string(src)
        assert module is not None

    def test_parse_string_class_with_slots(self, tmp_path):
        parser = self._make_parser()
        src = """
class Point:
    __slots__ = ['x', 'y']
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
"""
        fp = tmp_path / "point.py"
        module = parser.parse_string(src)
        assert len(module.classes) == 1

    def test_parse_string_global_statement(self, tmp_path):
        parser = self._make_parser()
        src = "counter = 0\ndef inc():\n    global counter\n    counter += 1\n"
        fp = tmp_path / "global.py"
        module = parser.parse_string(src)
        assert len(module.functions) == 1
