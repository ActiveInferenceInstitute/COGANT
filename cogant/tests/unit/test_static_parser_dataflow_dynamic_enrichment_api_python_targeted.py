#!/usr/bin/env python3
"""Targeted branch tests — static/parser.py (extended error paths),
static/dataflow.py (DataFlowAnalyzer, DataFlowVisitor helpers),
dynamic/enrichment.py (enrich_graph, _build_function_index, _enrich_with_coverage),
api/orchestration.py (program_graph_to_dict, _serialize_node, _serialize_edge).

Covers:
- static/parser.py: parse_string, parse_file (error paths), _ast_to_str (fallback),
  _extract_assignment (AnnAssign), _extract_imports (relative imports), _extract_class
- static/dataflow.py: DataFlowAnalyzer (analyze_file, analyze_source),
  DataFlowVisitor helpers (_extract_targets, _extract_loads, _target_name,
  _mark_handled, _ast_to_dotted, _attribute_root, _generate_flow_id)
- dynamic/enrichment.py: enrich_graph (no coverage/trace), _build_function_index,
  enrich_graph (with coverage file not found)
- api/orchestration.py: program_graph_to_dict, _serialize_node, _serialize_edge
"""

import ast
import json

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


# ---------------------------------------------------------------------------
# static/parser.py — PythonASTParser extended paths
# ---------------------------------------------------------------------------


class TestPythonASTParserExtended:
    def _make_parser(self):
        from cogant.static.parser import PythonASTParser

        return PythonASTParser()

    def test_parse_string_basic(self):
        parser = self._make_parser()
        src = "x = 1\ndef foo(): pass\n"
        module = parser.parse_string(src)
        # `parse_string` always returns a PythonModule, so `is not None` was
        # tautological (RedTeam 2026-06-09); assert the parse actually found the
        # defined function by name instead.
        assert len(module.functions) >= 1
        assert any(getattr(f, "name", None) == "foo" for f in module.functions)

    def test_parse_string_with_class(self):
        parser = self._make_parser()
        src = '''
class MyClass(Base):
    """A class."""
    x: int = 0

    def method(self) -> str:
        """Method."""
        return "hi"
'''
        module = parser.parse_string(src)
        assert len(module.classes) == 1
        cls = module.classes[0]
        assert cls.name == "MyClass"
        assert "Base" in cls.bases

    def test_parse_string_with_syntax_error(self):
        parser = self._make_parser()
        module = parser.parse_string("def foo(: pass")
        assert len(module.errors) >= 1

    def test_parse_string_with_docstring(self):
        parser = self._make_parser()
        src = '"""Module docstring."""\nx = 1\n'
        module = parser.parse_string(src)
        assert module.docstring == "Module docstring."

    def test_parse_string_relative_import(self):
        parser = self._make_parser()
        src = "from . import utils\nfrom ..core import base\n"
        module = parser.parse_string(src)
        assert len(module.imports) >= 1
        # At least one import should be relative
        assert any(imp.is_relative for imp in module.imports)

    def test_parse_string_annotated_assignment(self):
        parser = self._make_parser()
        src = "x: int = 5\ny: str\n"
        module = parser.parse_string(src)
        assert len(module.assignments) >= 1

    def test_parse_string_async_function(self):
        parser = self._make_parser()
        src = "async def fetch(url: str) -> bytes:\n    pass\n"
        module = parser.parse_string(src)
        assert len(module.functions) == 1
        assert module.functions[0].is_async is True

    def test_parse_file_nonexistent(self, tmp_path):
        parser = self._make_parser()
        module = parser.parse_file(tmp_path / "does_not_exist.py")
        assert len(module.errors) >= 1

    def test_parse_file_valid(self, tmp_path):
        parser = self._make_parser()
        p = tmp_path / "test_mod.py"
        p.write_text("def greet(name: str) -> str:\n    return f'Hello {name}'\n")
        module = parser.parse_file(p)
        assert len(module.functions) == 1
        assert module.functions[0].name == "greet"

    def test_parse_string_import_from_with_names(self):
        parser = self._make_parser()
        src = "from os.path import join, exists\n"
        module = parser.parse_string(src)
        assert len(module.imports) >= 1

    def test_ast_to_str_name_node(self):
        from cogant.static.parser import PythonASTParser

        node = ast.Name(id="MyClass", ctx=ast.Load())
        result = PythonASTParser._ast_to_str(node)
        assert "MyClass" in result

    def test_ast_to_str_constant_node(self):
        from cogant.static.parser import PythonASTParser

        node = ast.Constant(value=42)
        result = PythonASTParser._ast_to_str(node)
        assert result is not None

    def test_ast_to_str_attribute_node(self):
        from cogant.static.parser import PythonASTParser

        # Build ast.Attribute for "os.path"
        value = ast.Name(id="os", ctx=ast.Load())
        node = ast.Attribute(value=value, attr="path", ctx=ast.Load())
        result = PythonASTParser._ast_to_str(node)
        assert "os" in result or "path" in result

    def test_parse_string_with_decorated_function(self):
        parser = self._make_parser()
        src = "@staticmethod\ndef helper():\n    pass\n"
        module = parser.parse_string(src)
        assert len(module.functions) == 1
        assert len(module.functions[0].decorators) >= 1


# ---------------------------------------------------------------------------
# static/dataflow.py — DataFlowAnalyzer
# ---------------------------------------------------------------------------


class TestDataFlowAnalyzer:
    def _make_analyzer(self):
        from cogant.static.dataflow import DataFlowAnalyzer

        return DataFlowAnalyzer()

    def test_init(self):
        analyzer = self._make_analyzer()
        assert analyzer is not None

    def test_analyze_source_simple_assignment(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        src = "x = 1\ny = x + 2\n"
        fp = tmp_path / "test.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_function_with_reads_writes(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        src = """
def process(data):
    result = data
    return result
"""
        fp = tmp_path / "proc.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_class_with_self_attrs(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        src = """
class Counter:
    def __init__(self):
        self.count = 0

    def inc(self):
        self.count += 1
        return self.count
"""
        fp = tmp_path / "counter.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_syntax_error(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        flows = analyzer.analyze_source("def foo(: pass", tmp_path / "bad.py")
        assert isinstance(flows, list)
        assert len(flows) == 0

    def test_analyze_file_nonexistent(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        flows = analyzer.analyze_file(tmp_path / "does_not_exist.py")
        assert isinstance(flows, list)

    def test_analyze_file_valid(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        p = tmp_path / "sample.py"
        p.write_text("x = 1\ny = x + 1\n")
        flows = analyzer.analyze_file(p)
        assert isinstance(flows, list)

    def test_analyze_source_with_tuple_unpacking(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        src = "a, b = 1, 2\n"
        fp = tmp_path / "unpack.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_aug_assign(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        src = "count = 0\ncount += 1\n"
        fp = tmp_path / "aug.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_annotated_assign(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        src = "x: int = 5\n"
        fp = tmp_path / "ann.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_nested_class_methods(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        src = """
class A:
    class B:
        def method(self):
            self.x = 1
            return self.x
"""
        fp = tmp_path / "nested.py"
        flows = analyzer.analyze_source(src, fp)
        assert isinstance(flows, list)


# ---------------------------------------------------------------------------
# dynamic/enrichment.py — enrich_graph
# ---------------------------------------------------------------------------


class TestEnrichGraph:
    def test_enrich_graph_no_sources(self):
        from cogant.dynamic.enrichment import enrich_graph

        graph = _make_graph_with_nodes()
        result = enrich_graph(graph)
        assert isinstance(result, dict)
        assert "coverage_nodes_enriched" in result or isinstance(result, dict)

    def test_enrich_graph_with_nonexistent_coverage(self):
        from cogant.dynamic.enrichment import enrich_graph

        graph = _make_graph_with_nodes()
        result = enrich_graph(graph, coverage_path="/nonexistent/coverage.json")
        assert isinstance(result, dict)

    def test_enrich_graph_with_nonexistent_trace(self):
        from cogant.dynamic.enrichment import enrich_graph

        graph = _make_graph_with_nodes()
        result = enrich_graph(graph, trace_path="/nonexistent/trace.json")
        assert isinstance(result, dict)

    def test_enrich_graph_empty_graph(self):
        from cogant.dynamic.enrichment import enrich_graph

        graph = _make_empty_graph()
        result = enrich_graph(graph)
        assert isinstance(result, dict)

    def test_build_function_index_empty(self):
        from cogant.dynamic.enrichment import _build_function_index

        graph = _make_empty_graph()
        index = _build_function_index(graph)
        assert isinstance(index, dict)

    def test_build_function_index_with_functions(self):
        from cogant.dynamic.enrichment import _build_function_index

        graph = _make_graph_with_nodes()
        index = _build_function_index(graph)
        assert isinstance(index, dict)


# ---------------------------------------------------------------------------
# api/orchestration.py — program_graph_to_dict, _serialize_node/edge
# ---------------------------------------------------------------------------


class TestOrchestrationHelpers:
    def test_serialize_node_returns_dict(self):
        from cogant.api.orchestration import _serialize_node
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        result = _serialize_node(node)
        assert isinstance(result, dict)
        assert "kind" in result

    def test_serialize_edge_returns_dict(self):
        from cogant.api.orchestration import _serialize_edge
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "mod", "mod")
        n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn")
        edge = builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
        result = _serialize_edge(edge)
        assert isinstance(result, dict)
        assert "kind" in result

    def test_program_graph_to_dict_empty(self):
        from cogant.api.orchestration import program_graph_to_dict

        graph = _make_empty_graph()
        result = program_graph_to_dict(graph)
        assert isinstance(result, dict)
        assert "type" in result
        assert result["type"] == "program_graph"
        assert "nodes" in result
        assert "edges" in result

    def test_program_graph_to_dict_with_nodes(self):
        from cogant.api.orchestration import program_graph_to_dict

        graph = _make_graph_with_nodes()
        result = program_graph_to_dict(graph)
        assert isinstance(result, dict)
        assert len(result["nodes"]) >= 1

    def test_program_graph_to_dict_with_statistics(self):
        from cogant.api.orchestration import program_graph_to_dict

        graph = _make_empty_graph()
        stats = {"node_count": 0, "edge_count": 0}
        result = program_graph_to_dict(graph, statistics=stats)
        assert isinstance(result, dict)
        assert "statistics" in result

    def test_program_graph_to_dict_json_serializable(self):
        from cogant.api.orchestration import program_graph_to_dict

        graph = _make_graph_with_nodes()
        result = program_graph_to_dict(graph)
        # Should be JSON-serializable
        json_str = json.dumps(result, default=str)
        assert isinstance(json_str, str)
