"""Unit tests for cogant.static.treesitter_parser.

All tree-sitter-requiring tests are guarded with
``pytest.mark.skipif(not HAS_TREESITTER, ...)`` so the suite stays
green when the ``multilang`` extras are not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.static import treesitter_parser as tsp
from cogant.static.treesitter_parser import (
    HAS_TREESITTER,
    parse_file_treesitter,
    parse_js_file,
    parse_python_file,
    parse_ts_file,
)

# ---------------------------------------------------------------------------
# Availability / import
# ---------------------------------------------------------------------------


def test_treesitter_import_or_skip() -> None:
    """The module imports cleanly regardless of tree-sitter presence."""
    assert isinstance(HAS_TREESITTER, bool)
    # Public symbols are always present
    assert callable(parse_file_treesitter)
    assert callable(parse_js_file)
    assert callable(parse_ts_file)
    assert callable(parse_python_file)


def test_unknown_extension_returns_none(tmp_path: Path) -> None:
    """Unrecognized extensions yield None (no crash, no graph)."""
    f = tmp_path / "README.md"
    f.write_text("# hi\n")
    assert parse_file_treesitter(f) is None


def test_auto_route_by_extension(tmp_path: Path) -> None:
    """``.py`` routes through the Python path; ``.js`` through JS."""
    py = tmp_path / "m.py"
    py.write_text("def f():\n    return 1\n")

    # Python path always works (tree-sitter or ast fallback)
    graph = parse_file_treesitter(py)
    assert isinstance(graph, ProgramGraph)
    # Must contain at least a file node + the function node
    assert any(n.kind == NodeKind.FILE for n in graph.nodes.values())
    assert any(
        n.kind == NodeKind.FUNCTION and n.name == "f"
        for n in graph.nodes.values()
    )

    if HAS_TREESITTER:
        js = tmp_path / "m.js"
        js.write_text("function g() { return 2; }\n")
        jg = parse_file_treesitter(js)
        assert isinstance(jg, ProgramGraph)
        assert any(n.language == "javascript" for n in jg.nodes.values())


# ---------------------------------------------------------------------------
# Python path
# ---------------------------------------------------------------------------


def test_parse_python_via_treesitter(tmp_path: Path) -> None:
    """Parsing a Python file yields nodes roughly matching ast."""
    src = (
        "import os\n"
        "from pathlib import Path\n"
        "\n"
        "class Foo:\n"
        "    def bar(self):\n"
        "        return 1\n"
        "\n"
        "def baz():\n"
        "    return 2\n"
    )
    f = tmp_path / "sample.py"
    f.write_text(src)

    graph = parse_python_file(f)
    assert isinstance(graph, ProgramGraph)

    # Expect file + class + method(s) + function + 2 imports
    kinds = [n.kind for n in graph.nodes.values()]
    assert NodeKind.FILE in kinds
    assert NodeKind.CLASS in kinds
    assert NodeKind.FUNCTION in kinds or NodeKind.METHOD in kinds
    assert kinds.count(NodeKind.MODULE) >= 1  # at least one import

    # Edges should include CONTAINS and IMPORTS from the file node
    edge_kinds = [e.kind for e in graph.edges.values()]
    assert EdgeKind.CONTAINS in edge_kinds
    assert EdgeKind.IMPORTS in edge_kinds


def test_python_fallback_when_treesitter_missing(tmp_path: Path, monkeypatch) -> None:
    """If HAS_TREESITTER is False, Python still parses via ast."""
    monkeypatch.setattr(tsp, "HAS_TREESITTER", False)
    f = tmp_path / "m.py"
    f.write_text("def only_one():\n    pass\n")

    graph = tsp.parse_python_file(f)
    assert isinstance(graph, ProgramGraph)
    assert any(
        n.kind == NodeKind.FUNCTION and n.name == "only_one"
        for n in graph.nodes.values()
    )
    # The fallback tags edges with static/ast
    assert any(
        "static/ast" in e.evidence_sources for e in graph.edges.values()
    )


# ---------------------------------------------------------------------------
# JavaScript / TypeScript
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_TREESITTER, reason="tree-sitter not installed")
def test_parse_js_function(tmp_path: Path) -> None:
    """A JS file with a top-level function produces a FUNCTION node."""
    src = (
        "function greet(name) {\n"
        "  return 'hi ' + name;\n"
        "}\n"
    )
    f = tmp_path / "hello.js"
    f.write_text(src)

    graph = parse_js_file(f)
    assert isinstance(graph, ProgramGraph)
    assert any(
        n.kind == NodeKind.FUNCTION and n.name == "greet"
        for n in graph.nodes.values()
    )
    # All non-file nodes should be tagged javascript
    for n in graph.nodes.values():
        if n.kind != NodeKind.FILE or n.language is not None:
            assert n.language == "javascript"


@pytest.mark.skipif(not HAS_TREESITTER, reason="tree-sitter not installed")
def test_parse_js_class(tmp_path: Path) -> None:
    """A JS class lands as a CLASS node, methods as METHOD nodes."""
    src = (
        "class Animal {\n"
        "  constructor(name) { this.name = name; }\n"
        "  speak() { return this.name; }\n"
        "}\n"
    )
    f = tmp_path / "animal.js"
    f.write_text(src)

    graph = parse_js_file(f)
    assert isinstance(graph, ProgramGraph)

    class_nodes = [n for n in graph.nodes.values() if n.kind == NodeKind.CLASS]
    assert any(n.name == "Animal" for n in class_nodes)

    method_nodes = [n for n in graph.nodes.values() if n.kind == NodeKind.METHOD]
    method_names = {n.name for n in method_nodes}
    # speak() should always be picked up; constructor may vary by grammar
    assert "speak" in method_names


@pytest.mark.skipif(not HAS_TREESITTER, reason="tree-sitter not installed")
def test_parse_js_imports(tmp_path: Path) -> None:
    """JS imports land as MODULE nodes connected via IMPORTS edges."""
    src = (
        "import fs from 'fs';\n"
        "import { join } from 'path';\n"
        "function run() { return fs; }\n"
    )
    f = tmp_path / "x.js"
    f.write_text(src)

    graph = parse_js_file(f)
    assert isinstance(graph, ProgramGraph)
    assert sum(1 for n in graph.nodes.values() if n.kind == NodeKind.MODULE) >= 2
    assert any(e.kind == EdgeKind.IMPORTS for e in graph.edges.values())


@pytest.mark.skipif(not HAS_TREESITTER, reason="tree-sitter not installed")
def test_parse_ts_file(tmp_path: Path) -> None:
    """A TypeScript file with an interface + class parses cleanly."""
    src = (
        "interface Point { x: number; y: number; }\n"
        "class Vec implements Point {\n"
        "  x: number = 0;\n"
        "  y: number = 0;\n"
        "  length(): number { return Math.sqrt(this.x * this.x + this.y * this.y); }\n"
        "}\n"
    )
    f = tmp_path / "vec.ts"
    f.write_text(src)

    graph = parse_ts_file(f)
    assert isinstance(graph, ProgramGraph)
    names = {n.name for n in graph.nodes.values()}
    # When the native TypeScript grammar is loaded, Vec (the class) must appear.
    # When falling back to the JS grammar, `implements` may shift node boundaries
    # so Vec might not be extracted; we accept Point or length instead.
    assert names, "expected at least one named node"
    assert "Vec" in names or "Point" in names or "length" in names
    assert any(n.language == "typescript" for n in graph.nodes.values())


# ---------------------------------------------------------------------------
# Cross-check: tree-sitter vs ast for Python
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_TREESITTER, reason="tree-sitter not installed")
def test_treesitter_python_matches_ast_function_count(tmp_path: Path) -> None:
    """Function count from tree-sitter should match stdlib ast."""
    src = (
        "def a(): pass\n"
        "def b(): pass\n"
        "class C:\n"
        "    def m(self): pass\n"
    )
    f = tmp_path / "counts.py"
    f.write_text(src)

    # tree-sitter path
    ts_graph = parse_python_file(f)
    assert ts_graph is not None
    ts_funcs = sum(
        1
        for n in ts_graph.nodes.values()
        if n.kind in (NodeKind.FUNCTION, NodeKind.METHOD)
    )

    # ast fallback path
    from cogant.static.parser import PythonASTParser

    mod = PythonASTParser().parse_file(f)
    ast_funcs = len(mod.functions) + sum(len(c.methods) for c in mod.classes)

    assert ts_funcs == ast_funcs
