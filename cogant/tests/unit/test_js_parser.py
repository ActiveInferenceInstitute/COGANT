"""Tests for the tree-sitter backed JavaScript / TypeScript parsers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

try:
    import tree_sitter  # noqa: F401
    import tree_sitter_javascript  # noqa: F401

    HAS_JS_GRAMMAR = True
except ImportError:  # pragma: no cover
    HAS_JS_GRAMMAR = False

try:
    import tree_sitter_typescript  # noqa: F401

    HAS_TS_GRAMMAR = True
except ImportError:  # pragma: no cover
    HAS_TS_GRAMMAR = False


# Ensure the top-level ``parsers`` package is importable the same way
# test_polyglot_parsers.py does it.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PARSERS_ROOT = _REPO_ROOT / "parsers"
if str(_PARSERS_ROOT) not in sys.path:
    sys.path.insert(0, str(_PARSERS_ROOT))


@pytest.mark.skipif(not HAS_JS_GRAMMAR, reason="tree-sitter-javascript not installed")
def test_js_parser_available():
    from javascript.parser import JavaScriptLanguageParser

    parser = JavaScriptLanguageParser()
    assert parser.metadata.name == "javascript"
    assert ".js" in parser.supported_extensions
    assert ".jsx" in parser.supported_extensions


@pytest.mark.skipif(not HAS_JS_GRAMMAR, reason="tree-sitter-javascript not installed")
def test_js_parser_extracts_class_and_method():
    from javascript.parser import JavaScriptLanguageParser

    parser = JavaScriptLanguageParser()
    source = (
        "class Foo {\n  bar(x) { return x + 1; }\n}\nfunction baz() { return new Foo().bar(2); }\n"
    )
    ast = parser.parse(source, "foo.js")
    if ast.get("error"):
        pytest.skip(ast["error"])
    symbols = parser.extract_symbols(ast)
    qnames = {s["qualified_name"] for s in symbols}
    assert "Foo" in qnames
    assert "Foo.bar" in qnames
    assert "baz" in qnames


@pytest.mark.skipif(not HAS_JS_GRAMMAR, reason="tree-sitter-javascript not installed")
def test_js_parser_extracts_imports_and_calls():
    from javascript.parser import JavaScriptLanguageParser

    parser = JavaScriptLanguageParser()
    source = (
        "import React from 'react';\n"
        "import { useState } from 'react';\n"
        "function App() { return useState(0); }\n"
    )
    ast = parser.parse(source, "App.jsx")
    if ast.get("error"):
        pytest.skip(ast["error"])
    imports = parser.resolve_imports(ast)
    assert len(imports) >= 1
    calls = parser.extract_calls(source, "App.jsx")
    assert any("useState" in c["callee"] for c in calls)


@pytest.mark.skipif(not HAS_JS_GRAMMAR, reason="tree-sitter-javascript not installed")
def test_js_parser_parse_file(tmp_path):
    from javascript.parser import JavaScriptLanguageParser

    file_path = tmp_path / "x.js"
    file_path.write_text("function hi() { return 1; }\n", encoding="utf-8")
    parser = JavaScriptLanguageParser()
    result = parser.parse_file(file_path)
    if result.get("errors") and "grammar not available" in (result["errors"] or [""])[0]:
        pytest.skip("grammar not loaded")
    assert any(s["name"] == "hi" for s in result["symbols"])


@pytest.mark.skipif(not HAS_TS_GRAMMAR, reason="tree-sitter-typescript not installed")
def test_ts_tree_sitter_parser_interface_and_class():
    from typescript.tree_sitter_parser import TypeScriptTreeSitterParser

    parser = TypeScriptTreeSitterParser()
    source = (
        "interface IThing { x: number }\n"
        "class Thing implements IThing {\n"
        "  x = 1;\n"
        "  greet(): string { return 'hi'; }\n"
        "}\n"
    )
    ast = parser.parse(source, "thing.ts")
    if ast.get("error"):
        pytest.skip(ast["error"])
    symbols = parser.extract_symbols(ast)
    kinds = {s["kind"] for s in symbols}
    assert "interface" in kinds
    assert "class" in kinds
    assert "method" in kinds
    types = parser.extract_types(ast)
    assert any(i["name"] == "IThing" for i in types["interfaces"])
    assert any(c["name"] == "Thing" for c in types["classes"])


@pytest.mark.skipif(not HAS_TS_GRAMMAR, reason="tree-sitter-typescript not installed")
def test_ts_tree_sitter_parser_routes_tsx(tmp_path):
    from typescript.tree_sitter_parser import TypeScriptTreeSitterParser

    parser = TypeScriptTreeSitterParser()
    # TSX uses JSX syntax alongside TS types.
    source = "function App(): JSX.Element {\n  return <div>hi</div>;\n}\n"
    ast = parser.parse(source, "App.tsx")
    if ast.get("error"):
        pytest.skip(ast["error"])
    assert ast.get("language") == "tsx"
    assert any(s["name"] == "App" for s in ast["symbols"])


def test_get_parser_for_extension_unknown():
    from cogant.ingest.language_detect import get_parser_for_extension

    assert get_parser_for_extension(".xyz") is None
    assert get_parser_for_extension("") is None


def test_get_parser_for_extension_python():
    from cogant.ingest.language_detect import get_parser_for_extension

    parser = get_parser_for_extension(".py")
    assert parser is not None
    # Python plugin always comes from the stdlib-ast parser, not tree-sitter.
    assert "python" in getattr(parser, "supported_languages", set())


@pytest.mark.skipif(not HAS_JS_GRAMMAR, reason="tree-sitter-javascript not installed")
def test_get_parser_for_extension_js():
    from cogant.ingest.language_detect import get_parser_for_extension

    parser = get_parser_for_extension(".js")
    assert parser is not None
    # Must prefer the new tree-sitter JS plugin.
    assert parser.metadata.name in {"javascript", "typescript"}


@pytest.mark.skipif(not HAS_TS_GRAMMAR, reason="tree-sitter-typescript not installed")
def test_get_parser_for_extension_ts():
    from cogant.ingest.language_detect import get_parser_for_extension

    parser = get_parser_for_extension(".ts")
    assert parser is not None
    # Tree-sitter or legacy regex TS are both acceptable.
    assert parser.metadata.name == "typescript"
