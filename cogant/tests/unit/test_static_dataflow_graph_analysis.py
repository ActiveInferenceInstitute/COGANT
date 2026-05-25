"""Targeted coverage tests for ``cogant.static.dataflow``.

Covers:
- DataFlowGraph add_edge / find_sources / find_sinks / get_taint_paths / to_dict
- DataFlowAnalyzer.analyze_file (success and missing path)
- DataFlowAnalyzer.build_flow_graph (file + source variants)
- analyze_source error branches (SyntaxError, ValueError)
- Class body analysis (default attributes, AnnAssigns)
- Class methods analysis (context = "Class.method")
- Subscript / Tuple / List unpacking targets

All tests use real Python source and real file system paths via tmp_path.
"""

import ast
from pathlib import Path

from cogant.static.dataflow import (
    DataFlowAnalyzer,
    DataFlowEdge,
    DataFlowGraph,
    DataFlowVisitor,
)

# ---------------------------------------------------------------------------
# DataFlowGraph
# ---------------------------------------------------------------------------


def _make_edge(
    source: str,
    target: str,
    edge_type: str = "depends_on",
    line: int = 1,
    file_path: Path | None = None,
) -> DataFlowEdge:
    return DataFlowEdge(
        id=f"{source}->{target}:{edge_type}:{line}",
        source_symbol=source,
        target_symbol=target,
        edge_type=edge_type,
        file_path=file_path or Path("snippet.py"),
        line_num=line,
    )


class TestDataFlowGraph:
    def test_add_edge_records_both_endpoints(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        assert "a" in g.nodes
        assert "b" in g.nodes
        assert len(g.edges) == 1

    def test_find_sources_returns_no_incoming_nodes(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        g.add_edge(_make_edge("b", "c"))
        # Only "a" has no incoming edges.
        assert g.find_sources() == ["a"]

    def test_find_sinks_returns_no_outgoing_nodes(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        g.add_edge(_make_edge("b", "c"))
        assert g.find_sinks() == ["c"]

    def test_find_sources_and_sinks_with_isolated_node(self):
        g = DataFlowGraph()
        # Build a graph with an isolated node added via edge that maps to itself
        g.add_edge(_make_edge("a", "b"))
        # Add nodes via a self-loop-ish edge
        g.nodes.add("isolated")
        sources = g.find_sources()
        sinks = g.find_sinks()
        # Isolated node has neither incoming nor outgoing edges => both
        assert "isolated" in sources
        assert "isolated" in sinks

    def test_get_taint_paths_simple_chain(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        g.add_edge(_make_edge("b", "c"))
        g.add_edge(_make_edge("c", "d"))
        paths = g.get_taint_paths("a", "d")
        assert paths == [["a", "b", "c", "d"]]

    def test_get_taint_paths_multiple_paths(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        g.add_edge(_make_edge("a", "c"))
        g.add_edge(_make_edge("b", "d"))
        g.add_edge(_make_edge("c", "d"))
        paths = g.get_taint_paths("a", "d")
        # Two distinct paths a->b->d and a->c->d
        assert sorted(paths) == sorted([["a", "b", "d"], ["a", "c", "d"]])

    def test_get_taint_paths_self_target(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        # source==target — DFS records the trivial single-node path
        paths = g.get_taint_paths("a", "a")
        assert paths == [["a"]]

    def test_get_taint_paths_unknown_source(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        # Source not in graph => no paths returned
        assert g.get_taint_paths("missing", "b") == []

    def test_get_taint_paths_no_route(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        g.add_edge(_make_edge("c", "d"))
        # a and d are disconnected
        assert g.get_taint_paths("a", "d") == []

    def test_get_taint_paths_avoids_cycles(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b"))
        g.add_edge(_make_edge("b", "a"))  # cycle
        g.add_edge(_make_edge("b", "c"))
        paths = g.get_taint_paths("a", "c")
        assert paths == [["a", "b", "c"]]

    def test_to_dict_round_trip_shape(self):
        g = DataFlowGraph()
        g.add_edge(_make_edge("a", "b", edge_type="reads", line=10))
        g.add_edge(_make_edge("c", "d", edge_type="writes", line=20))
        out = g.to_dict()
        assert sorted(out["nodes"]) == ["a", "b", "c", "d"]
        assert len(out["edges"]) == 2
        first = out["edges"][0]
        assert {"id", "source", "target", "type", "file", "line", "context"} <= first.keys()


# ---------------------------------------------------------------------------
# DataFlowAnalyzer file-level paths
# ---------------------------------------------------------------------------


class TestDataFlowAnalyzerFiles:
    def test_analyze_file_reads_real_source(self, tmp_path: Path):
        f = tmp_path / "module.py"
        f.write_text("def foo(x):\n    y = x + 1\n    return y\n")
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_file(f)
        assert flows  # at least one edge
        # Edges include both write and read for ``y`` and ``x``.
        types = {e.edge_type for e in flows}
        assert {"writes", "reads", "depends_on"} <= types

    def test_analyze_file_missing_path_returns_empty(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        result = analyzer.analyze_file(tmp_path / "does_not_exist.py")
        assert result == []

    def test_build_flow_graph_from_file(self, tmp_path: Path):
        f = tmp_path / "g.py"
        f.write_text("def f(a, b):\n    c = a + b\n    return c\n")
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        graph = analyzer.build_flow_graph(f)
        assert isinstance(graph, DataFlowGraph)
        assert graph.edges
        # f should appear in nodes (writes) and a/b should appear (reads)
        assert "c" in graph.nodes
        assert "a" in graph.nodes

    def test_build_flow_graph_from_source(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        graph = analyzer.build_flow_graph_from_source(
            "def h(x):\n    z = x\n    return z\n", tmp_path / "fake.py"
        )
        assert "z" in graph.nodes
        assert any(e.edge_type == "writes" for e in graph.edges)

    def test_analyze_source_syntax_error_returns_empty(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        # Unbalanced parens => SyntaxError
        result = analyzer.analyze_source("def broken(:", tmp_path / "bad.py")
        assert result == []

    def test_analyze_source_value_error_returns_empty(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        # NUL bytes in source raise ValueError from ast.parse
        result = analyzer.analyze_source("x = 1\x00\n", tmp_path / "v.py")
        assert result == []


# ---------------------------------------------------------------------------
# Class-level analysis
# ---------------------------------------------------------------------------


class TestClassAnalysis:
    def test_class_body_attributes_emit_edges(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        src = (
            "class C:\n"
            "    x: int = 5\n"
            "    y = 'hello'\n"
            "    def m(self):\n"
            "        return self.x\n"
        )
        flows = analyzer.analyze_source(src, tmp_path / "c.py")
        contexts = {e.context for e in flows}
        # Class body emits with context == class name; method emits with C.m
        assert "C" in contexts
        assert "C.m" in contexts

    def test_method_body_context_uses_dotted_name(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        src = (
            "class K:\n"
            "    def go(self, n):\n"
            "        self.total += n\n"
            "        return self.total\n"
        )
        flows = analyzer.analyze_source(src, tmp_path / "k.py")
        assert any(e.context == "K.go" for e in flows)
        # AugAssign emits a 'mutates' edge
        assert any(e.edge_type == "mutates" for e in flows)


# ---------------------------------------------------------------------------
# Direct visitor coverage for unpacking / subscript / dotted writes
# ---------------------------------------------------------------------------


class TestVisitorEdgeCases:
    def test_tuple_unpacking_attribute_target(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        src = (
            "class M:\n"
            "    def f(self, a, b):\n"
            "        self.x, self.y = a, b\n"
            "        return self.x\n"
        )
        flows = analyzer.analyze_source(src, tmp_path / "m.py")
        targets = {e.target_symbol for e in flows if e.edge_type == "writes"}
        assert "self.x" in targets
        assert "self.y" in targets

    def test_list_unpacking_target(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_source(
            "def f(seq):\n    [x, y] = seq\n    return x\n",
            tmp_path / "l.py",
        )
        write_targets = {e.target_symbol for e in flows if e.edge_type == "writes"}
        assert "x" in write_targets
        assert "y" in write_targets

    def test_subscript_assign_target_uses_base_name(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_source(
            "def f(arr, i, v):\n    arr[i] = v\n",
            tmp_path / "s.py",
        )
        assert any(
            e.target_symbol == "arr" and e.edge_type == "writes" for e in flows
        )

    def test_attribute_root_handles_chained_attribute(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        src = (
            "class C:\n"
            "    def f(self, v):\n"
            "        self.inner.value = v\n"
        )
        flows = analyzer.analyze_source(src, tmp_path / "ch.py")
        # Dotted write captures full chain
        assert any(
            e.target_symbol == "self.inner.value" and e.edge_type == "writes"
            for e in flows
        )

    def test_attribute_root_helper_with_subscript(self):
        body = ast.parse("a[0]").body
        # _attribute_root descends past Subscript to the Name "a"
        v = DataFlowVisitor(Path("x.py"), "module", [])
        node = body[0].value  # ast.Subscript
        assert v._attribute_root(node) == "a"

    def test_target_name_returns_none_for_unhandled_kind(self):
        v = DataFlowVisitor(Path("x.py"), "module", [])
        # Pass an ast.Subscript which is not handled by _target_name
        sub = ast.parse("a[0] = 1").body[0].targets[0]
        assert v._target_name(sub) is None

    def test_extract_loads_returns_empty_for_none(self):
        assert DataFlowVisitor._extract_loads(None) == set()

    def test_ast_to_dotted_returns_none_for_unknown(self):
        v = DataFlowVisitor(Path("x.py"), "module", [])
        # A constant has no dotted form
        const = ast.parse("1").body[0].value
        assert v._ast_to_dotted(const) is None

    def test_visit_call_method_receiver_emits_mutates(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_source(
            "def f(obj):\n    obj.append(1)\n",
            tmp_path / "call.py",
        )
        assert any(
            e.edge_type == "mutates" and e.target_symbol == "obj" for e in flows
        )

    def test_visit_call_with_kwargs(self, tmp_path: Path):
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_source(
            "def f(arg):\n    helper(name=arg)\n",
            tmp_path / "kw.py",
        )
        assert any(
            e.source_symbol == "arg"
            and e.target_symbol == "<call>"
            and e.edge_type == "reads"
            for e in flows
        )
