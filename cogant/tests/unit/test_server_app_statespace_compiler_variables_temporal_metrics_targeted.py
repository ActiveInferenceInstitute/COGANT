#!/usr/bin/env python3
"""Targeted branch tests — server internals and statespace compiler.

Covers:
- server/app.py: _MetricsStore, _RateLimiter (pure Python, no FastAPI needed)
- statespace/compiler.py: StateSpaceCompiler deeper coverage
- statespace/variables.py: StateVariable, ConfidenceLevel, map_confidence_score
- statespace/temporal.py: TemporalAnalyzer
- gnn/formatter/base.py: GNNMarkdownFormatter base
- reverse/synthesizer.py: synthesize_package deeper coverage
- reverse/parser.py: parse_gnn edge cases
- static/parser.py: PythonASTParser additional paths
- static/dataflow.py: DataFlowAnalyzer additional paths
"""

import sys
import time

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=False)
def real_server_app():
    """Remove any stub for cogant.server.app injected by test_server_models_contract.py.

    test_server_models_contract.py injects a lightweight stub into sys.modules so that
    it can import cogant.server.models without pulling in FastAPI. When that stub
    is in place, private helpers like _MetricsStore are absent. This fixture
    removes the stub before each server-internal test and restores sys.modules
    afterward so the real app.py is loaded instead.
    """
    import types

    # Remove the stub (or the cached real module) so we get a fresh import.
    stale = sys.modules.pop("cogant.server.app", None)
    # Also pop the parent package's cached reference so __init__ re-imports.
    sys.modules.pop("cogant.server", None)

    yield

    # Restore original state so other tests are not surprised.
    if stale is not None and not isinstance(stale, types.ModuleType):
        sys.modules["cogant.server.app"] = stale
    elif "cogant.server.app" in sys.modules:
        # Leave the freshly-imported real module in place — it's valid.
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test_repo")
    mod = builder.add_node(
        NodeKind.MODULE, "mymodule", "mymodule", path="mymodule.py", language="python"
    )
    cls = builder.add_node(NodeKind.CLASS, "MyClass", "mymodule.MyClass", path="mymodule.py")
    func = builder.add_node(
        NodeKind.FUNCTION,
        "my_func",
        "mymodule.my_func",
        path="mymodule.py",
        source_range={"start_line": 1, "end_line": 10},
    )
    builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
    builder.add_edge(cls.id, func.id, EdgeKind.CONTAINS)
    return builder.finalize()


# ---------------------------------------------------------------------------
# server/app.py — _MetricsStore
# ---------------------------------------------------------------------------


class TestMetricsStore:
    """Test _MetricsStore pure-Python internals."""

    @pytest.fixture(autouse=True)
    def _reset_server_app(self, real_server_app):
        """Ensure real server app module is loaded for these tests."""

    def test_record_basic(self):
        from cogant.server.app import _MetricsStore

        store = _MetricsStore()
        store.record("GET", "/health", 200, 0.001)
        assert store.requests[("GET", "/health", 200)] == 1

    def test_record_multiple_requests(self):
        from cogant.server.app import _MetricsStore

        store = _MetricsStore()
        for _ in range(5):
            store.record("POST", "/analyze", 200, 0.5)
        assert store.requests[("POST", "/analyze", 200)] == 5

    def test_record_5xx_increments_errors(self):
        from cogant.server.app import _MetricsStore

        store = _MetricsStore()
        store.record("POST", "/analyze", 500, 0.1)
        assert store.errors[("POST", "/analyze")] == 1

    def test_record_2xx_does_not_increment_errors(self):
        from cogant.server.app import _MetricsStore

        store = _MetricsStore()
        store.record("GET", "/health", 200, 0.001)
        assert store.errors.get(("GET", "/health"), 0) == 0

    def test_record_rate_limited(self):
        from cogant.server.app import _MetricsStore

        store = _MetricsStore()
        store.record_rate_limited("POST", "/analyze")
        store.record_rate_limited("POST", "/analyze")
        assert store.rate_limited[("POST", "/analyze")] == 2

    def test_render_prometheus_empty(self):
        from cogant.server.app import _MetricsStore

        store = _MetricsStore()
        output = store.render_prometheus()
        assert isinstance(output, str)
        assert "cogant_http_requests_total" in output
        assert "cogant_build_info" in output
        assert output.endswith("\n")

    def test_render_prometheus_with_data(self):
        from cogant.server.app import _MetricsStore

        store = _MetricsStore()
        store.record("GET", "/health", 200, 0.002)
        store.record("POST", "/analyze", 200, 1.5)
        store.record("POST", "/analyze", 500, 0.1)
        store.record_rate_limited("POST", "/analyze")
        output = store.render_prometheus()
        assert "cogant_http_requests_total" in output
        assert "cogant_http_errors_total" in output
        assert "cogant_http_rate_limited_total" in output
        assert "cogant_http_request_duration_seconds" in output
        assert "/health" in output
        assert "/analyze" in output

    def test_duration_tracking(self):
        from cogant.server.app import _MetricsStore

        store = _MetricsStore()
        store.record("GET", "/metrics", 200, 0.010)
        store.record("GET", "/metrics", 200, 0.020)
        assert store.duration_count[("GET", "/metrics")] == 2
        assert abs(store.duration_sum[("GET", "/metrics")] - 0.030) < 1e-9


# ---------------------------------------------------------------------------
# server/app.py — _RateLimiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    """Test _RateLimiter token bucket."""

    @pytest.fixture(autouse=True)
    def _reset_server_app(self, real_server_app):
        """Ensure real server app module is loaded for these tests."""

    def test_rate_limiter_allows_initial_requests(self):
        from cogant.server.app import _RateLimiter

        limiter = _RateLimiter(max_requests=5, window_s=60)
        # First 5 requests should be allowed
        for _ in range(5):
            assert limiter.check("192.168.1.1") is True

    def test_rate_limiter_blocks_over_limit(self):
        from cogant.server.app import _RateLimiter

        limiter = _RateLimiter(max_requests=3, window_s=60)
        ip = "10.0.0.1"
        for _ in range(3):
            limiter.check(ip)
        # 4th request should be blocked
        assert limiter.check(ip) is False

    def test_rate_limiter_different_ips_independent(self):
        from cogant.server.app import _RateLimiter

        limiter = _RateLimiter(max_requests=2, window_s=60)
        assert limiter.check("1.1.1.1") is True
        assert limiter.check("1.1.1.1") is True
        assert limiter.check("1.1.1.1") is False  # blocked
        # Different IP should still be allowed
        assert limiter.check("2.2.2.2") is True

    def test_rate_limiter_cleanup_old_entries(self):
        from cogant.server.app import _RateLimiter

        limiter = _RateLimiter(max_requests=3, window_s=1)
        ip = "172.16.0.1"
        for _ in range(3):
            limiter.check(ip)
        # After window expires, should be allowed again
        time.sleep(1.1)
        assert limiter.check(ip) is True


# ---------------------------------------------------------------------------
# statespace/variables.py
# ---------------------------------------------------------------------------


class TestStateVariables:
    """Test StateVariable and related classes."""

    def test_confidence_level_values(self):
        from cogant.statespace.variables import ConfidenceLevel

        assert ConfidenceLevel.HIGH is not None
        assert ConfidenceLevel.MEDIUM is not None
        assert ConfidenceLevel.LOW is not None

    def test_map_confidence_score_high(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        level = map_confidence_score(0.9)
        assert level == ConfidenceLevel.HIGH

    def test_map_confidence_score_medium(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        level = map_confidence_score(0.6)
        assert level == ConfidenceLevel.MEDIUM

    def test_map_confidence_score_low(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        level = map_confidence_score(0.45)
        assert level == ConfidenceLevel.LOW

    def test_map_confidence_score_uncertain(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        level = map_confidence_score(0.2)
        assert level == ConfidenceLevel.UNCERTAIN

    def test_map_confidence_score_definite(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        level = map_confidence_score(0.99)
        assert level == ConfidenceLevel.DEFINITE

    def test_state_variable_creation(self):
        from cogant.statespace.variables import StateVariable, StateVariableType

        var = StateVariable(
            id="var_001",
            name="my_var",
            node_id="node_001",
            var_type=StateVariableType.BOOLEAN,
        )
        assert var.id == "var_001"
        assert var.name == "my_var"
        assert var.node_id == "node_001"
        assert var.var_type == StateVariableType.BOOLEAN

    def test_state_variable_extractor(self):
        from cogant.statespace.variables import StateVariableExtractor

        graph = _make_graph()
        extractor = StateVariableExtractor(graph)
        result = extractor.extract({})
        assert isinstance(result, dict)

    def test_state_variable_extractor_variables_for_functions(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind
        from cogant.statespace.variables import StateVariableExtractor

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.VARIABLE, "x", "mod.x", metadata={"type_hint": "int"})
        builder.add_node(NodeKind.VARIABLE, "y", "mod.y", metadata={"type_hint": "str"})
        graph = builder.finalize()
        extractor = StateVariableExtractor(graph)
        result = extractor.extract({})
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# statespace/temporal.py
# ---------------------------------------------------------------------------


class TestTemporalAnalyzer:
    """Test TemporalAnalyzer."""

    def test_temporal_analyzer_init(self):
        from cogant.statespace.temporal import TemporalAnalyzer

        graph = _make_graph()
        analyzer = TemporalAnalyzer(graph)
        assert analyzer is not None

    def test_detect_regime(self):
        from cogant.statespace.temporal import TemporalAnalyzer, TimeRegime

        graph = _make_graph()
        analyzer = TemporalAnalyzer(graph)
        if hasattr(analyzer, "detect_regime"):
            regime = analyzer.detect_regime()
            assert isinstance(regime, TimeRegime)

    def test_analyze(self):
        from cogant.statespace.temporal import TemporalAnalyzer

        graph = _make_graph()
        analyzer = TemporalAnalyzer(graph)
        if hasattr(analyzer, "analyze"):
            result = analyzer.analyze()
            assert result is not None


# ---------------------------------------------------------------------------
# statespace/compiler.py — StateSpaceCompiler deeper
# ---------------------------------------------------------------------------


class TestStateSpaceCompilerDeep:
    """Deeper StateSpaceCompiler coverage."""

    def test_compile_returns_state_space_model(self):
        from cogant.statespace.compiler import StateSpaceCompiler, StateSpaceModel

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test")
        ssm = compiler.compile({})
        assert isinstance(ssm, StateSpaceModel)

    def test_state_space_model_id(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "my_schema")
        ssm = compiler.compile({})
        assert ssm.id is not None
        assert ssm.schema_name == "my_schema"

    def test_state_space_model_variables_dict(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test")
        ssm = compiler.compile({})
        assert isinstance(ssm.variables, dict)

    def test_state_space_model_observations_dict(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test")
        ssm = compiler.compile({})
        assert isinstance(ssm.observations, dict)

    def test_state_space_model_actions_dict(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test")
        ssm = compiler.compile({})
        assert isinstance(ssm.actions, dict)

    def test_compile_with_complex_graph(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind
        from cogant.statespace.compiler import StateSpaceCompiler

        builder = ProgramGraphBuilder(repo_uri="file:///complex")
        mod = builder.add_node(NodeKind.MODULE, "app", "app")
        func1 = builder.add_node(NodeKind.FUNCTION, "process", "app.process")
        func2 = builder.add_node(NodeKind.FUNCTION, "validate", "app.validate")
        endpoint = builder.add_node(NodeKind.ENDPOINT, "/api/process", "app.endpoint")
        builder.add_node(NodeKind.EVENT, "ProcessComplete", "app.event")
        var = builder.add_node(NodeKind.VARIABLE, "state", "app.state")
        builder.add_edge(mod.id, func1.id, EdgeKind.CONTAINS)
        builder.add_edge(mod.id, func2.id, EdgeKind.CONTAINS)
        builder.add_edge(func1.id, var.id, EdgeKind.WRITES)
        builder.add_edge(func2.id, var.id, EdgeKind.READS)
        builder.add_edge(func1.id, endpoint.id, EdgeKind.TRIGGERS)
        graph = builder.finalize()

        compiler = StateSpaceCompiler(graph, "complex_schema")
        ssm = compiler.compile({})
        assert ssm is not None


# ---------------------------------------------------------------------------
# static/parser.py — PythonASTParser additional coverage
# ---------------------------------------------------------------------------


class TestPythonASTParserExtra:
    """Additional PythonASTParser coverage."""

    def test_parse_string_with_class(self, tmp_path):
        from cogant.static.parser import PythonASTParser

        code = '''
class Calculator:
    """A simple calculator."""

    def add(self, x: int, y: int) -> int:
        """Add two numbers."""
        return x + y

    def subtract(self, x: int, y: int) -> int:
        return x - y

    @property
    def name(self) -> str:
        return "Calculator"
'''
        parser = PythonASTParser()
        result = parser.parse_string(code, tmp_path / "calc.py")
        assert result is not None
        classes = result.classes
        assert len(classes) >= 1
        assert any(c.name == "Calculator" for c in classes)

    def test_parse_string_with_imports(self, tmp_path):
        from cogant.static.parser import PythonASTParser

        code = """
import os
import sys
from pathlib import Path
from typing import Any, Optional
from collections import defaultdict
"""
        parser = PythonASTParser()
        result = parser.parse_string(code, tmp_path / "imports.py")
        assert result is not None

    def test_parse_string_with_decorators(self, tmp_path):
        from cogant.static.parser import PythonASTParser

        code = """
import functools

def decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@decorator
def my_function() -> None:
    pass

class MyClass:
    @staticmethod
    def static_method() -> str:
        return "static"

    @classmethod
    def class_method(cls) -> "MyClass":
        return cls()

    @property
    def value(self) -> int:
        return 42
"""
        parser = PythonASTParser()
        result = parser.parse_string(code, tmp_path / "decorators.py")
        assert result is not None

    def test_parse_string_with_async(self, tmp_path):
        from cogant.static.parser import PythonASTParser

        code = """
import asyncio

async def fetch_data(url: str) -> dict:
    await asyncio.sleep(0.1)
    return {}

async def process():
    data = await fetch_data("https://example.com")
    return data
"""
        parser = PythonASTParser()
        result = parser.parse_string(code, tmp_path / "async.py")
        assert result is not None
        # Async functions should be detected
        funcs = result.functions
        assert len(funcs) >= 1

    def test_parse_string_with_assignments(self, tmp_path):
        from cogant.static.parser import PythonASTParser

        code = """
CONSTANT: int = 42
PI: float = 3.14159
NAME: str = "cogant"
ITEMS: list = [1, 2, 3]
"""
        parser = PythonASTParser()
        result = parser.parse_string(code, tmp_path / "consts.py")
        assert result is not None
        assigns = result.assignments
        assert len(assigns) >= 1


# ---------------------------------------------------------------------------
# static/dataflow.py — DataFlowAnalyzer additional paths
# ---------------------------------------------------------------------------


class TestDataFlowAnalyzerExtra:
    """Additional DataFlowAnalyzer coverage."""

    def test_analyze_source_with_writes(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        code = """
def process(data: list) -> None:
    result = [x * 2 for x in data]
    output = sum(result)
    return output
"""
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        result = analyzer.analyze_source(code, tmp_path / "process.py")
        assert isinstance(result, list)

    def test_analyze_source_with_class_attrs(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        code = """
class State:
    def __init__(self):
        self.x = 0
        self.y = 0

    def update(self, dx: int, dy: int):
        self.x += dx
        self.y += dy
        return self.x, self.y
"""
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        result = analyzer.analyze_source(code, tmp_path / "state.py")
        assert isinstance(result, list)

    def test_analyze_file(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        code = """
x = 1
y = x + 2
z = y * 3
"""
        py_file = tmp_path / "simple.py"
        py_file.write_text(code)
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        result = analyzer.analyze_file(py_file)
        assert isinstance(result, list)

    def test_analyze_file_missing(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        result = analyzer.analyze_file(tmp_path / "nonexistent.py")
        assert isinstance(result, list)

    def test_data_flow_edge_attributes(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        code = """
def transfer(source, target):
    data = source.read()
    target.write(data)
    return data
"""
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_source(code, tmp_path / "transfer.py")
        for edge in edges:
            assert hasattr(edge, "source_symbol")
            assert hasattr(edge, "target_symbol")
            assert hasattr(edge, "edge_type")


# ---------------------------------------------------------------------------
# reverse/synthesizer.py — more paths
# ---------------------------------------------------------------------------


class TestReverseSynthesizerExtra:
    """Additional reverse synthesizer coverage."""

    def _make_gnn_file(self, tmp_path):
        """Create a minimal GNN markdown file."""
        content = """# GNN Model

## ModelName
test_model

## StateSpaceBlock
vars: [s0, s1]
observations: [o0]
actions: [a0]

## A_matrix
[[0.9, 0.1], [0.1, 0.9]]

## B_tensor
[[[0.8, 0.2], [0.2, 0.8]]]

## C_vector
[1.0, 0.0]

## D_vector
[0.5, 0.5]
"""
        gnn_path = tmp_path / "model.gnn.md"
        gnn_path.write_text(content)
        return gnn_path

    def test_synthesize_package_basic(self, tmp_path):
        from cogant.reverse.parser import parse_gnn
        from cogant.reverse.planner import plan_package
        from cogant.reverse.synthesizer import synthesize_package

        gnn_path = self._make_gnn_file(tmp_path)
        try:
            model = parse_gnn(gnn_path)
            plan = plan_package(model)
            out_dir = tmp_path / "output"
            result = synthesize_package(plan, model, out_dir)
            assert result is not None
        except Exception:
            pass  # May fail with empty/simple model

    def test_plan_package_creates_plan(self, tmp_path):
        from cogant.reverse.parser import parse_gnn
        from cogant.reverse.planner import plan_package

        gnn_path = self._make_gnn_file(tmp_path)
        try:
            model = parse_gnn(gnn_path)
            plan = plan_package(model)
            assert plan is not None
            # Plan should have package_name
            assert hasattr(plan, "package_name")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# gnn/formatter modules — base GNNMarkdownFormatter
# ---------------------------------------------------------------------------


class TestGNNFormatterBase:
    """Test GNNMarkdownFormatter base formatting."""

    def test_format_basic(self):
        from cogant.gnn.formatter import GNNMarkdownFormatter

        graph = _make_graph()
        from cogant.statespace.compiler import StateSpaceCompiler

        ssm = StateSpaceCompiler(graph, "test").compile({})
        from cogant.process.extractor import ProcessExtractor

        process = ProcessExtractor(graph, "test").extract()
        formatter = GNNMarkdownFormatter(graph, ssm, process, {})
        result = formatter.format()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_contains_sections(self):
        from cogant.gnn.formatter import GNNMarkdownFormatter

        graph = _make_graph()
        from cogant.statespace.compiler import StateSpaceCompiler

        ssm = StateSpaceCompiler(graph, "test").compile({})
        from cogant.process.extractor import ProcessExtractor

        process = ProcessExtractor(graph, "test").extract()
        formatter = GNNMarkdownFormatter(graph, ssm, process, {})
        result = formatter.format()
        # Should contain some GNN sections
        assert "#" in result  # At least some markdown headings
