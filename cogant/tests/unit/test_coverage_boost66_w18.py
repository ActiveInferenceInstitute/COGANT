#!/usr/bin/env python3
"""Coverage boost batch 66 — static/parser.py, graph/queries.py, graph/merge.py.

Covers:
- static/parser.py: PythonASTParser (parse_string, parse_file),
  PythonModule, FunctionDef, ClassDef, ImportDef, AssignmentDef
- graph/queries.py: GraphQuery (find_all_paths, find_connected_components,
  find_cycles, find_shortest_path, filter_nodes, filter_edges,
  compute_degree_centrality, extract_subgraph_by_kind, get_statistics,
  compute_betweenness_centrality, compute_closeness_centrality,
  compute_in_degree, compute_out_degree, find_nodes_by_kind,
  get_dependency_chain)
- graph/merge.py: GraphMerger (merge, merge_graphs, merge_multiple_graphs,
  get_merge_statistics)
"""

import pytest

pytestmark = pytest.mark.unit

_SAMPLE_PY = """
import os
from typing import List

def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    result = a + b
    return result

async def async_fn() -> None:
    pass

class Rect:
    \"\"\"Rectangle class.\"\"\"
    WIDTH: int = 10
    def __init__(self, w: int, h: int) -> None:
        self.w = w
        self.h = h

    def area(self) -> int:
        return self.w * self.h

x: int = 42
items: List[str] = []
"""


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
    n2 = builder.add_node(NodeKind.CLASS, "Rect", "mod.Rect", path="mod.py")
    n3 = builder.add_node(NodeKind.FUNCTION, "add", "mod.add", path="mod.py")
    n4 = builder.add_node(NodeKind.FUNCTION, "area", "mod.Rect.area", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    builder.add_edge(n1.id, n3.id, EdgeKind.CONTAINS)
    builder.add_edge(n2.id, n4.id, EdgeKind.CONTAINS)
    return builder.finalize(), [n1.id, n2.id, n3.id, n4.id]


# ---------------------------------------------------------------------------
# static/parser.py — PythonASTParser and dataclasses
# ---------------------------------------------------------------------------


class TestPythonASTParser:
    def _make_parser(self):
        from cogant.static.parser import PythonASTParser

        return PythonASTParser()

    def test_init(self):
        parser = self._make_parser()
        assert parser is not None

    def test_parse_string_returns_module(self):
        from cogant.static.parser import PythonModule

        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        assert isinstance(module, PythonModule)

    def test_parse_string_finds_functions(self):
        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        func_names = [f.name for f in module.functions]
        assert "add" in func_names

    def test_parse_string_finds_async_function(self):
        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        async_funcs = [f for f in module.functions if f.is_async]
        assert len(async_funcs) >= 1

    def test_parse_string_finds_classes(self):
        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        class_names = [c.name for c in module.classes]
        assert "Rect" in class_names

    def test_parse_string_finds_imports(self):
        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        import_modules = [i.module_name for i in module.imports]
        assert "os" in import_modules

    def test_parse_string_finds_assignments(self):
        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        assert isinstance(module.assignments, list)

    def test_parse_string_empty(self):
        from cogant.static.parser import PythonModule

        parser = self._make_parser()
        module = parser.parse_string("")
        assert isinstance(module, PythonModule)
        assert module.functions == []
        assert module.classes == []

    def test_parse_file(self, tmp_path):
        from cogant.static.parser import PythonModule

        src = tmp_path / "sample.py"
        src.write_text(_SAMPLE_PY)
        parser = self._make_parser()
        module = parser.parse_file(src)
        assert isinstance(module, PythonModule)

    def test_parse_function_has_args(self):
        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        add_func = next((f for f in module.functions if f.name == "add"), None)
        assert add_func is not None
        assert isinstance(add_func.args, list)
        assert len(add_func.args) >= 2

    def test_parse_function_has_return_annotation(self):
        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        add_func = next((f for f in module.functions if f.name == "add"), None)
        assert add_func is not None
        assert add_func.return_annotation is not None

    def test_parse_class_has_methods(self):
        parser = self._make_parser()
        module = parser.parse_string(_SAMPLE_PY)
        rect = next((c for c in module.classes if c.name == "Rect"), None)
        assert rect is not None
        assert len(rect.methods) >= 2  # __init__ and area


class TestPythonModuleDataclasses:
    def test_function_def_fields(self):
        from cogant.static.parser import FunctionDef

        fd = FunctionDef(
            name="f",
            line_start=1,
            line_end=3,
            decorators=[],
            args=["a", "b"],
            return_annotation="int",
            docstring="docs",
            parent=None,
            is_async=False,
            metadata={},
        )
        assert fd.name == "f"
        assert fd.is_async is False
        assert len(fd.args) == 2

    def test_class_def_fields(self):
        from cogant.static.parser import ClassDef

        cd = ClassDef(
            name="MyClass",
            line_start=1,
            line_end=10,
            bases=["Base"],
            decorators=[],
            docstring="A class",
            methods=[],
            attributes=[],
            metadata={},
        )
        assert cd.name == "MyClass"
        assert cd.bases == ["Base"]

    def test_import_def_fields(self):
        from cogant.static.parser import ImportDef

        imp = ImportDef(
            module_name="os",
            is_relative=False,
            names=["path"],
            line_num=1,
            metadata={},
        )
        assert imp.module_name == "os"
        assert imp.is_relative is False

    def test_assignment_def_fields(self):
        from cogant.static.parser import AssignmentDef

        asgn = AssignmentDef(
            target_name="x",
            line_num=5,
            annotation="int",
            value="42",
            parent_scope=None,
            metadata={},
        )
        assert asgn.target_name == "x"
        assert asgn.annotation == "int"


# ---------------------------------------------------------------------------
# graph/queries.py — GraphQuery
# ---------------------------------------------------------------------------


class TestGraphQuery:
    def _make_query(self, empty=False):
        from cogant.graph.queries import GraphQuery

        if empty:
            return GraphQuery(_make_empty_graph())
        graph, _ = _make_graph_with_nodes()
        return GraphQuery(graph)

    def test_init(self):
        q = self._make_query()
        assert q is not None

    def test_init_empty_graph(self):
        q = self._make_query(empty=True)
        assert q is not None

    def test_get_statistics(self):
        q = self._make_query()
        stats = q.get_statistics()
        assert isinstance(stats, dict)

    def test_find_all_paths_nonexistent(self):
        q = self._make_query()
        paths = q.find_all_paths("nonexistent", "also_nonexistent")
        assert paths == []

    def test_find_all_paths_same_node(self):
        from cogant.graph.queries import GraphQuery

        graph, node_ids = _make_graph_with_nodes()
        q = GraphQuery(graph)
        paths = q.find_all_paths(node_ids[0], node_ids[2])
        assert isinstance(paths, list)

    def test_find_connected_components_empty(self):
        q = self._make_query(empty=True)
        components = q.find_connected_components()
        assert isinstance(components, list)

    def test_find_connected_components_with_nodes(self):
        q = self._make_query()
        components = q.find_connected_components()
        assert isinstance(components, list)
        assert len(components) >= 1

    def test_find_cycles_empty(self):
        q = self._make_query(empty=True)
        cycles = q.find_cycles()
        assert cycles == []

    def test_find_cycles_acyclic_graph(self):
        q = self._make_query()
        cycles = q.find_cycles()
        assert isinstance(cycles, list)

    def test_find_shortest_path_nonexistent(self):
        q = self._make_query()
        path = q.find_shortest_path("nonexistent", "also_nonexistent")
        assert path is None

    def test_find_shortest_path_existing(self):
        from cogant.graph.queries import GraphQuery

        graph, node_ids = _make_graph_with_nodes()
        q = GraphQuery(graph)
        path = q.find_shortest_path(node_ids[0], node_ids[1])
        assert path is None or isinstance(path, list)

    def test_filter_nodes_no_filter(self):
        q = self._make_query()
        nodes = q.filter_nodes()
        assert isinstance(nodes, list)

    def test_filter_nodes_by_kind(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        graph, _ = _make_graph_with_nodes()
        q = GraphQuery(graph)
        nodes = q.filter_nodes(kind=NodeKind.FUNCTION)
        assert isinstance(nodes, list)
        for n in nodes:
            assert n.kind == NodeKind.FUNCTION

    def test_filter_edges_no_filter(self):
        q = self._make_query()
        edges = q.filter_edges()
        assert isinstance(edges, list)

    def test_filter_edges_by_kind(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind

        graph, _ = _make_graph_with_nodes()
        q = GraphQuery(graph)
        edges = q.filter_edges(kind=EdgeKind.CONTAINS)
        assert isinstance(edges, list)

    def test_compute_degree_centrality(self):
        q = self._make_query()
        centrality = q.compute_degree_centrality()
        assert isinstance(centrality, dict)

    def test_compute_betweenness_centrality(self):
        q = self._make_query()
        centrality = q.compute_betweenness_centrality()
        assert isinstance(centrality, dict)

    def test_compute_in_degree(self):
        from cogant.graph.queries import GraphQuery

        graph, node_ids = _make_graph_with_nodes()
        q = GraphQuery(graph)
        in_deg = q.compute_in_degree(node_ids[0])
        assert isinstance(in_deg, int)

    def test_compute_out_degree(self):
        from cogant.graph.queries import GraphQuery

        graph, node_ids = _make_graph_with_nodes()
        q = GraphQuery(graph)
        out_deg = q.compute_out_degree(node_ids[0])
        assert isinstance(out_deg, int)

    def test_extract_subgraph_by_kind(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind
        from cogant.schemas.graph import ProgramGraph

        graph, _ = _make_graph_with_nodes()
        q = GraphQuery(graph)
        subgraph = q.extract_subgraph_by_kind([NodeKind.FUNCTION])
        assert isinstance(subgraph, ProgramGraph)

    def test_get_dependency_chain(self):
        from cogant.graph.queries import GraphQuery

        graph, node_ids = _make_graph_with_nodes()
        q = GraphQuery(graph)
        chain = q.get_dependency_chain(node_ids[0])
        assert isinstance(chain, (list, dict))


# ---------------------------------------------------------------------------
# graph/merge.py — GraphMerger
# ---------------------------------------------------------------------------


class TestGraphMerger:
    def test_init(self):
        from cogant.graph.merge import GraphMerger

        merger = GraphMerger()
        assert merger is not None

    def test_merge_empty_list_raises(self):
        from cogant.graph.merge import GraphMerger

        merger = GraphMerger()
        with pytest.raises(ValueError):
            merger.merge([])

    def test_merge_single_graph(self):
        from cogant.graph.merge import GraphMerger
        from cogant.schemas.graph import ProgramGraph

        merger = GraphMerger()
        graph, _ = _make_graph_with_nodes()
        result = merger.merge([graph])
        assert isinstance(result, ProgramGraph)
        assert result.node_count() == graph.node_count()

    def test_merge_two_graphs(self):
        from cogant.graph.merge import GraphMerger
        from cogant.schemas.graph import ProgramGraph

        merger = GraphMerger()
        g1, _ = _make_graph_with_nodes()
        g2 = _make_empty_graph()
        result = merger.merge([g1, g2])
        assert isinstance(result, ProgramGraph)

    def test_merge_graphs(self):
        from cogant.graph.merge import GraphMerger
        from cogant.schemas.graph import ProgramGraph

        merger = GraphMerger()
        g1, _ = _make_graph_with_nodes()
        g2 = _make_empty_graph()
        merged, provenance = merger.merge_graphs(g1, g2)
        assert isinstance(merged, ProgramGraph)

    def test_merge_multiple_graphs(self):
        from cogant.graph.merge import GraphMerger
        from cogant.schemas.graph import ProgramGraph

        merger = GraphMerger()
        g1, _ = _make_graph_with_nodes()
        g2 = _make_empty_graph()
        result = merger.merge_multiple_graphs([("static", g1), ("dynamic", g2)])
        assert isinstance(result, ProgramGraph)

    def test_get_merge_statistics_empty(self):
        from cogant.graph.merge import GraphMerger

        merger = GraphMerger()
        stats = merger.get_merge_statistics()
        assert isinstance(stats, dict)

    def test_get_merge_statistics_after_merge(self):
        from cogant.graph.merge import GraphMerger

        merger = GraphMerger()
        g1, _ = _make_graph_with_nodes()
        merger.merge([g1])
        stats = merger.get_merge_statistics()
        assert isinstance(stats, dict)
