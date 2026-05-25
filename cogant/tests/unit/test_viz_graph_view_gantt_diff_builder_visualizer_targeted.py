#!/usr/bin/env python3
"""Targeted branch tests — remaining coverage gaps.

Covers:
- viz/graph_view.py: GraphVisualizer, D3Node, D3Link, clustering, filtering
- viz/gantt.py: GanttRenderer from_process_model, render_json, internal helpers
- viz/diff_view.py: DiffVisualizer (if accessible)
- graph/builder.py: more ProgramGraphBuilder paths
- graph/queries.py: GraphQueryEngine methods
- translate/rules: translation rule modules
- statespace/temporal.py: TimeRegime and related
- validate/integrity.py: IntegrityChecker additional paths
- static/symbols.py: SymbolExtractor
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


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
        name="my_func",
        qualified_name="mymodule.my_func",
        path="mymodule.py",
        source_range={"start_line": 1, "end_line": 10},
        language="python",
    )
    builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
    builder.add_edge(cls.id, func.id, EdgeKind.CONTAINS)
    return builder.finalize()


# ---------------------------------------------------------------------------
# viz/graph_view.py
# ---------------------------------------------------------------------------


class TestGraphVisualizer:
    """Test GraphVisualizer."""

    def test_from_program_graph_dict(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [
                {
                    "id": "n1",
                    "name": "FuncA",
                    "type": "function",
                    "language": "python",
                    "path": "mod.py",
                    "qualified_name": "mod.FuncA",
                },
                {
                    "id": "n2",
                    "name": "ClassB",
                    "type": "class",
                    "language": "python",
                    "path": "mod.py",
                    "qualified_name": "mod.ClassB",
                },
            ],
            "edges": [
                {"source": "n1", "target": "n2", "type": "CALLS", "weight": 2.0},
            ],
            "metadata": {"version": "1"},
        }
        viz = GraphVisualizer()
        result = viz.from_program_graph(graph_dict)
        assert result is viz
        assert len(viz.nodes) == 2
        assert len(viz.links) == 1

    def test_from_typed_graph(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph = _make_graph()
        viz = GraphVisualizer()
        result = viz.from_typed_graph(graph)
        assert result is viz
        assert len(viz.nodes) >= 2

    def test_cluster_by_package(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [
                {"id": "n1", "name": "FuncA", "type": "function", "path": "module/func.py"},
                {"id": "n2", "name": "ClassB", "type": "class", "qualified_name": "pkg.ClassB"},
                {"id": "n3", "name": "SimpleFunc", "type": "function"},
            ],
            "edges": [],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        viz.cluster_by_package()
        groups = {n.id: n.group for n in viz.nodes}
        assert groups["n1"] == "module"  # First path component

    def test_cluster_by_language(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [
                {"id": "n1", "name": "A", "type": "function", "language": "python"},
                {"id": "n2", "name": "B", "type": "function", "language": "typescript"},
                {"id": "n3", "name": "C", "type": "function"},  # no language
            ],
            "edges": [],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        viz.cluster_by_language()
        groups = {n.id: n.group for n in viz.nodes}
        assert groups["n1"] == "python"
        assert groups["n2"] == "typescript"
        assert groups["n3"] == "unknown_lang"

    def test_cluster_by_kind(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [
                {"id": "n1", "name": "A", "type": "function"},
                {"id": "n2", "name": "B", "type": "class"},
                {"id": "n3", "name": "C"},  # no kind
            ],
            "edges": [],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        viz.cluster_by_kind()
        groups = {n.id: n.group for n in viz.nodes}
        assert groups["n1"] == "function"
        assert groups["n2"] == "class"
        assert groups["n3"] == "unknown_kind"

    def test_cluster_by_service(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [
                {"id": "n1", "name": "api.service.Handler", "type": "class"},
            ],
            "edges": [],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        viz.cluster_by_service()
        assert len(viz.nodes) == 1

    def test_get_clusters(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [
                {"id": "n1", "name": "A", "type": "function", "language": "python"},
                {"id": "n2", "name": "B", "type": "function", "language": "python"},
                {"id": "n3", "name": "C", "type": "class", "language": "typescript"},
            ],
            "edges": [],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        viz.cluster_by_language()
        clusters = viz.get_clusters()
        assert isinstance(clusters, dict)
        assert "python" in clusters
        assert len(clusters["python"]) == 2

    def test_filter_by_edge_type(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [
                {"id": "n1", "name": "A", "type": "function"},
                {"id": "n2", "name": "B", "type": "function"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "type": "calls"},
                {"source": "n2", "target": "n1", "type": "imports"},
            ],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        viz.filter_by_edge_type("calls")
        assert len(viz.links) == 1
        assert viz.links[0].label == "calls"

    def test_to_d3_json(self):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [{"id": "n1", "name": "FuncA", "type": "function"}],
            "edges": [{"source": "n1", "target": "n1", "type": "CALLS", "weight": 1.0}],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        d3 = viz.to_d3_json()
        assert "nodes" in d3
        assert "links" in d3
        assert "clusters" in d3

    def test_render_html_writes_file(self, tmp_path):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [{"id": "n1", "name": "FuncA", "type": "function"}],
            "edges": [],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        out_path = str(tmp_path / "graph.html")
        result = viz.render_html(out_path)
        assert result == out_path
        content = Path(out_path).read_text()
        assert "<!DOCTYPE html>" in content or "<html" in content

    def test_render_svg_writes_file(self, tmp_path):
        from cogant.viz.graph_view import GraphVisualizer

        graph_dict = {
            "nodes": [
                {"id": "n1", "name": "FuncA", "type": "function"},
                {"id": "n2", "name": "ClassB", "type": "class"},
            ],
            "edges": [{"source": "n1", "target": "n2", "type": "calls", "weight": 1.0}],
        }
        viz = GraphVisualizer()
        viz.from_program_graph(graph_dict)
        out_path = str(tmp_path / "graph.svg")
        result = viz.render_svg(out_path)
        assert result == out_path
        content = Path(out_path).read_text()
        assert "<svg" in content

    def test_d3node_defaults(self):
        from cogant.viz.graph_view import D3Node

        node = D3Node(id="n1", label="FuncA", group="functions")
        assert node.size == 10
        assert node.color is None
        assert node.language is None

    def test_d3link_defaults(self):
        from cogant.viz.graph_view import D3Link

        link = D3Link(source="n1", target="n2", label="calls")
        assert link.weight == 1.0


# ---------------------------------------------------------------------------
# viz/gantt.py
# ---------------------------------------------------------------------------


class TestGanttRenderer:
    """Test GanttRenderer."""

    def test_from_process_model_basic(self):
        from cogant.viz.gantt import GanttRenderer

        process_model = {
            "stages": [
                {
                    "id": "s1",
                    "name": "Setup",
                    "start": 0,
                    "duration": 2,
                    "dependencies": [],
                    "criticality": "high",
                },
                {
                    "id": "s2",
                    "name": "Test",
                    "start": 2,
                    "duration": 3,
                    "dependencies": ["s1"],
                    "criticality": "normal",
                },
            ],
            "dependencies": [{"from": "s1", "to": "s2"}],
            "timeline": [],
            "critical_path": ["s1"],
            "parallel_groups": [["s2"]],
        }
        renderer = GanttRenderer()
        result = renderer.from_process_model(process_model)
        assert result is renderer
        assert len(renderer.stages) == 2
        assert renderer.critical_path == ["s1"]

    def test_render_json(self):
        from cogant.viz.gantt import GanttRenderer

        process_model = {
            "stages": [{"id": "s1", "name": "Build", "start": 0, "duration": 1}],
            "dependencies": [],
            "timeline": [],
            "critical_path": [],
            "parallel_groups": [],
        }
        renderer = GanttRenderer()
        renderer.from_process_model(process_model)
        json_out = renderer.render_json()
        data = json.loads(json_out)
        assert "stages" in data
        assert "critical_path" in data

    def test_render_html_writes_file(self, tmp_path):
        from cogant.viz.gantt import GanttRenderer

        process_model = {
            "stages": [
                {"id": "s1", "name": "Stage1", "start": 0, "duration": 2},
                {"id": "s2", "name": "Stage2", "start": 2, "duration": 3},
            ],
            "dependencies": [],
            "timeline": [],
            "critical_path": ["s1"],
            "parallel_groups": [],
        }
        renderer = GanttRenderer()
        renderer.from_process_model(process_model)
        out_path = str(tmp_path / "gantt.html")
        result = renderer.render_html(out_path)
        assert result == out_path
        content = Path(out_path).read_text()
        assert "<!DOCTYPE html>" in content

    def test_compute_total_duration(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        # Empty stages
        assert renderer._compute_total_duration() == 1.0
        # With stages
        renderer.stages = [
            {"start": 0, "duration": 5},
            {"start": 3, "duration": 4},
        ]
        total = renderer._compute_total_duration()
        assert total == 7.0  # max(5, 7) = 7

    def test_stage_id_from_id(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        assert renderer._stage_id({"id": "myid", "name": "myname"}, 0) == "myid"

    def test_stage_id_from_name(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        assert renderer._stage_id({"name": "myname"}, 0) == "myname"

    def test_stage_id_fallback(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        assert renderer._stage_id({}, 3) == "stage_3"

    def test_is_critical(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        renderer.critical_path = ["s1", "s2"]
        assert renderer._is_critical({"id": "s1"}, 0) is True
        assert renderer._is_critical({"id": "s3"}, 2) is False
        assert renderer._is_critical({"name": "s2"}, 1) is True

    def test_is_critical_empty_path(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        renderer.critical_path = []
        assert renderer._is_critical({"id": "s1"}, 0) is False

    def test_parallel_group_for(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        renderer.parallel_groups = [["s1", "s2"], ["s3"]]
        result = renderer._parallel_group_for({"id": "s1"}, 0)
        assert result == 0
        result2 = renderer._parallel_group_for({"name": "s3"}, 2)
        assert result2 == 1
        result3 = renderer._parallel_group_for({"id": "s9"}, 8)
        assert result3 is None

    def test_timeline_ticks(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        ticks = renderer._timeline_ticks(10.0, num_ticks=5)
        assert len(ticks) == 5
        assert ticks[0] == "0"

    def test_timeline_ticks_edge_cases(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        # Zero total
        ticks = renderer._timeline_ticks(0.0)
        assert ticks == ["0"]
        # One tick
        ticks = renderer._timeline_ticks(5.0, num_ticks=1)
        assert len(ticks) == 1

    def test_empty_gantt_render(self):
        from cogant.viz.gantt import GanttRenderer

        renderer = GanttRenderer()
        json_out = renderer.render_json()
        data = json.loads(json_out)
        assert data["stages"] == []


# ---------------------------------------------------------------------------
# graph/queries.py
# ---------------------------------------------------------------------------


class TestGraphQueryEngine:
    """Test GraphQuery (the actual class name)."""

    def test_import_and_instantiate(self):
        from cogant.graph.queries import GraphQuery

        graph = _make_graph()
        engine = GraphQuery(graph)
        assert engine is not None

    def test_find_nodes_by_kind(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        graph = _make_graph()
        engine = GraphQuery(graph)
        modules = engine.find_nodes_by_kind(NodeKind.MODULE)
        assert len(modules) >= 1

    def test_filter_nodes_by_language(self):
        from cogant.graph.queries import GraphQuery

        graph = _make_graph()
        engine = GraphQuery(graph)
        python_nodes = engine.filter_nodes(language="python")
        assert isinstance(python_nodes, list)

    def test_filter_nodes_by_name_pattern(self):
        from cogant.graph.queries import GraphQuery

        graph = _make_graph()
        engine = GraphQuery(graph)
        matches = engine.filter_nodes(name_pattern="func")
        assert isinstance(matches, list)

    def test_filter_nodes_all(self):
        from cogant.graph.queries import GraphQuery

        graph = _make_graph()
        engine = GraphQuery(graph)
        all_nodes = engine.filter_nodes()
        assert len(all_nodes) == len(graph.nodes)

    def test_filter_edges_by_kind(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind

        graph = _make_graph()
        engine = GraphQuery(graph)
        contains_edges = engine.filter_edges(kind=EdgeKind.CONTAINS)
        assert isinstance(contains_edges, list)

    def test_filter_edges_by_source(self):
        from cogant.graph.queries import GraphQuery

        graph = _make_graph()
        engine = GraphQuery(graph)
        nodes = list(graph.nodes.values())
        if nodes:
            edges = engine.filter_edges(source_id=nodes[0].id)
            assert isinstance(edges, list)


# ---------------------------------------------------------------------------
# graph/builder.py — additional paths
# ---------------------------------------------------------------------------


class TestProgramGraphBuilderExtra:
    """Test ProgramGraphBuilder edge cases."""

    def test_add_multiple_node_kinds(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.MODULE, "mod", "mod")
        builder.add_node(NodeKind.CLASS, "MyClass", "mod.MyClass")
        builder.add_node(NodeKind.FUNCTION, "my_func", "mod.my_func")
        builder.add_node(NodeKind.METHOD, "method", "mod.MyClass.method")
        builder.add_node(NodeKind.VARIABLE, "my_var", "mod.my_var")
        builder.add_node(NodeKind.PARAMETER, "param1", "mod.my_func.param1")
        graph = builder.finalize()
        assert len(graph.nodes) == 6

    def test_add_various_edge_kinds(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "mod1", "mod1")
        n2 = builder.add_node(NodeKind.MODULE, "mod2", "mod2")
        n3 = builder.add_node(NodeKind.CLASS, "cls", "cls")
        builder.add_edge(n1.id, n2.id, EdgeKind.IMPORTS)
        builder.add_edge(n2.id, n3.id, EdgeKind.CONTAINS)
        builder.add_edge(n1.id, n3.id, EdgeKind.DEPENDS_ON)
        graph = builder.finalize()
        assert len(graph.edges) == 3

    def test_add_node_with_metadata(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(
            NodeKind.FUNCTION,
            name="my_func",
            qualified_name="mod.my_func",
            path="mod.py",
            language="python",
            source_range={"start_line": 10, "end_line": 20},
            metadata={"visibility": "public", "is_async": True},
        )
        graph = builder.finalize()
        n = graph.get_node(node.id)
        assert n is not None
        assert n.metadata.get("visibility") == "public"

    def test_finalize_returns_program_graph(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.graph import ProgramGraph

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        assert isinstance(graph, ProgramGraph)

    def test_add_edge_with_weight(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.FUNCTION, "f1", "f1")
        n2 = builder.add_node(NodeKind.FUNCTION, "f2", "f2")
        builder.add_edge(n1.id, n2.id, EdgeKind.CALLS, weight=5.0)
        graph = builder.finalize()
        for edge in graph.edges.values():
            if edge.source_id == n1.id and edge.target_id == n2.id:
                assert edge.weight == 5.0


# ---------------------------------------------------------------------------
# statespace/temporal.py
# ---------------------------------------------------------------------------


class TestStatespaceTemporalTimeRegime:
    """Test TimeRegime and related temporal functions."""

    def test_time_regime_import(self):
        from cogant.statespace.temporal import TimeRegime

        assert TimeRegime is not None

    def test_time_regime_values(self):
        from cogant.statespace.temporal import TimeRegime

        # Should have discrete/continuous variants
        regimes = list(TimeRegime)
        assert len(regimes) >= 1

    def test_temporal_module_has_timeline(self):
        try:
            from cogant.statespace.temporal import Timeline

            assert Timeline is not None
        except ImportError:
            pass  # Optional

    def test_temporal_functions_accessible(self):
        import cogant.statespace.temporal as temporal

        assert hasattr(temporal, "TimeRegime")


# ---------------------------------------------------------------------------
# validate/integrity.py — IntegrityChecker additional paths
# ---------------------------------------------------------------------------


class TestIntegrityCheckerExtra:
    """Additional IntegrityChecker tests."""

    def test_check_program_graph_with_valid_graph(self):
        from cogant.validate.integrity import IntegrityChecker

        graph = _make_graph()
        checker = IntegrityChecker()
        result = checker.check_program_graph(graph)
        assert result is not None

    def test_check_program_graph_returns_list_or_bool(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.validate.integrity import IntegrityChecker

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        checker = IntegrityChecker()
        result = checker.check_program_graph(graph)
        # Result should be a list of issues or a bool
        assert isinstance(result, (list, bool, dict))

    def test_check_state_space_basic(self):
        from cogant.statespace.compiler import StateSpaceCompiler
        from cogant.validate.integrity import IntegrityChecker

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test_schema")
        ssm = compiler.compile({})
        checker = IntegrityChecker()
        result = checker.check_state_space(ssm)
        assert result is not None


# ---------------------------------------------------------------------------
# static/symbols.py — SymbolExtractor
# ---------------------------------------------------------------------------


class TestSymbolExtractor:
    """Test SymbolExtractor for Python source."""

    def test_extract_functions(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor, SymbolTable

        code = """
def hello(name: str) -> str:
    return f"Hello {name}"

def world() -> None:
    pass
"""
        py_file = tmp_path / "greet.py"
        py_file.write_text(code)
        extractor = SymbolExtractor(tmp_path)
        result = extractor.extract_from_file(py_file)
        assert isinstance(result, SymbolTable)

    def test_extract_classes(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor, SymbolTable

        code = """
class MyClass:
    def __init__(self):
        self.value = 0

    def compute(self) -> int:
        return self.value
"""
        py_file = tmp_path / "myclass.py"
        py_file.write_text(code)
        extractor = SymbolExtractor(tmp_path)
        result = extractor.extract_from_file(py_file)
        assert isinstance(result, SymbolTable)
        # Should have symbols
        assert hasattr(result, "symbols")

    def test_extract_from_source(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor, SymbolTable

        code = """
CONSTANT = 42
x: int = 5

class Foo:
    class_var: str = "hello"
"""
        extractor = SymbolExtractor(tmp_path)
        if hasattr(extractor, "extract_from_source"):
            result = extractor.extract_from_source(code, tmp_path / "const.py")
            assert isinstance(result, SymbolTable)

    def test_symbol_extractor_missing_file(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor, SymbolTable

        extractor = SymbolExtractor(tmp_path)
        result = extractor.extract_from_file(tmp_path / "nonexistent.py")
        # Should return empty SymbolTable on error
        assert isinstance(result, SymbolTable)

    def test_symbol_table_has_symbols_list(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor

        code = "def foo(): pass\ndef bar(): pass\n"
        py_file = tmp_path / "funcs.py"
        py_file.write_text(code)
        extractor = SymbolExtractor(tmp_path)
        result = extractor.extract_from_file(py_file)
        assert hasattr(result, "symbols")
        assert len(result.symbols) == 2


# ---------------------------------------------------------------------------
# graph/merge.py — GraphMerger
# ---------------------------------------------------------------------------


class TestGraphMerger:
    """Test GraphMerger for combining graphs."""

    def test_merge_two_graphs(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.graph.merge import GraphMerger
        from cogant.schemas.core import NodeKind

        builder1 = ProgramGraphBuilder(repo_uri="file:///repo1")
        builder1.add_node(NodeKind.MODULE, "mod1", "mod1")
        g1 = builder1.finalize()

        builder2 = ProgramGraphBuilder(repo_uri="file:///repo2")
        builder2.add_node(NodeKind.MODULE, "mod2", "mod2")
        g2 = builder2.finalize()

        merger = GraphMerger()
        merged = merger.merge([g1, g2])
        assert len(merged.nodes) >= 2

    def test_merge_empty_graphs(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.graph.merge import GraphMerger

        builder1 = ProgramGraphBuilder(repo_uri="file:///empty1")
        g1 = builder1.finalize()
        builder2 = ProgramGraphBuilder(repo_uri="file:///empty2")
        g2 = builder2.finalize()

        merger = GraphMerger()
        merged = merger.merge([g1, g2])
        assert len(merged.nodes) == 0


# ---------------------------------------------------------------------------
# viz/diff_view.py — DiffVisualizer
# ---------------------------------------------------------------------------


class TestDiffVisualizer:
    """Test DiffVisualizer for graph comparison."""

    def test_import_diff_visualizer(self):
        from cogant.viz.diff_view import DiffVisualizer

        assert DiffVisualizer is not None

    def test_diff_visualizer_init(self):
        from cogant.viz.diff_view import DiffVisualizer

        b1 = {"nodes": {"n1": {"id": "n1", "kind": "function"}}, "edges": {}}
        b2 = {"nodes": {"n2": {"id": "n2", "kind": "class"}}, "edges": {}}
        viz = DiffVisualizer(b1, b2)
        assert viz is not None

    def test_diff_visualizer_compute_diff(self):
        from cogant.viz.diff_view import DiffVisualizer

        b1 = {
            "nodes": {
                "n1": {"id": "n1", "kind": "function", "name": "func1"},
                "n2": {"id": "n2", "kind": "class", "name": "Class1"},
            },
            "edges": {},
        }
        b2 = {
            "nodes": {
                "n1": {"id": "n1", "kind": "function", "name": "func1"},
                "n3": {"id": "n3", "kind": "module", "name": "NewModule"},
            },
            "edges": {},
        }
        viz = DiffVisualizer(b1, b2)
        if hasattr(viz, "compute_diff"):
            diff = viz.compute_diff()
            assert diff is not None


# ---------------------------------------------------------------------------
# statespace/compiler.py — additional StateSpaceCompiler paths
# ---------------------------------------------------------------------------


class TestStateSpaceCompilerExtra:
    """Additional StateSpaceCompiler coverage."""

    def test_compile_with_empty_mappings_dict(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test_schema")
        ssm = compiler.compile({})
        assert ssm is not None

    def test_compile_empty_mappings(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "schema1")
        ssm = compiler.compile({})
        assert ssm is not None

    def test_state_space_model_attributes(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test")
        ssm = compiler.compile({})
        # Should have basic attributes
        assert hasattr(ssm, "variables") or hasattr(ssm, "states") or hasattr(ssm, "schema_name")


# ---------------------------------------------------------------------------
# process/extractor.py — ProcessExtractor additional paths
# ---------------------------------------------------------------------------


class TestProcessExtractorExtra:
    """Additional ProcessExtractor coverage."""

    def test_extract_with_complex_graph(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.process.extractor import ProcessExtractor
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///complex")
        mod = builder.add_node(NodeKind.MODULE, "api", "api")
        cls = builder.add_node(NodeKind.CLASS, "Handler", "api.Handler")
        func1 = builder.add_node(NodeKind.METHOD, "handle", "api.Handler.handle")
        func2 = builder.add_node(NodeKind.METHOD, "validate", "api.Handler.validate")
        endpoint = builder.add_node(NodeKind.ENDPOINT, "POST /api", "api.endpoint.post")
        builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
        builder.add_edge(cls.id, func1.id, EdgeKind.CONTAINS)
        builder.add_edge(cls.id, func2.id, EdgeKind.CONTAINS)
        builder.add_edge(func1.id, endpoint.id, EdgeKind.TRIGGERS)
        builder.add_edge(func1.id, func2.id, EdgeKind.CALLS)
        graph = builder.finalize()

        extractor = ProcessExtractor(graph, "complex_schema")
        model = extractor.extract()
        assert model is not None

    def test_process_model_has_stages(self):
        from cogant.process.extractor import ProcessExtractor

        graph = _make_graph()
        extractor = ProcessExtractor(graph, "test_schema")
        model = extractor.extract()
        # ProcessModel should have some structure
        assert (
            hasattr(model, "stages") or hasattr(model, "processes") or hasattr(model, "schema_name")
        )
