"""Completeness tests for the JS/TS tree-sitter extractor.

Verifies that advanced JS/TS patterns are correctly extracted by
``cogant.parsers.tree_sitter_base._JavaScriptExtractor``:

* Arrow functions assigned to a ``const``/``let``/``var`` binding are
  named after the binding, not ``<anonymous>``.
* ``async`` functions and arrow functions carry ``metadata["is_async"] = True``.
* Class declarations with ``extends`` carry ``metadata["bases"] = [...]``.
* Decorators are attached to the following class symbol via
  ``metadata["decorators"]``.
* TypeScript ``interface`` declarations are extracted with ``kind="interface"``.
* TypeScript generic type parameters are preserved in
  ``metadata["type_params"]`` when the TS grammar is available.

No mocks.  All tests use real source strings passed through the tree-sitter
parser (or are skipped when the required grammar is unavailable).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Availability guard
# ---------------------------------------------------------------------------

try:
    import cogant.parsers.tree_sitter_base as _base_mod

    _base_mod._instance = None  # reset singleton so changes are picked up
    _PARSER = _base_mod.get_tree_sitter_parser()
    HAS_JS = "javascript" in _PARSER.available_languages()
    HAS_TS = "typescript" in _PARSER.available_languages()
except Exception:
    HAS_JS = False
    HAS_TS = False
    _PARSER = None  # type: ignore[assignment]

_skip_no_js = pytest.mark.skipif(not HAS_JS, reason="tree-sitter-javascript not installed")
_skip_no_ts = pytest.mark.skipif(not HAS_TS, reason="tree-sitter-typescript not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(source: str, lang: str = "javascript") -> list[dict[str, Any]]:
    """Parse ``source`` and return a list of symbol dicts."""
    assert _PARSER is not None
    result = _PARSER.parse_source(source, lang)
    assert result is not None, f"parse_source returned None for lang={lang!r}"
    return [
        {
            "name": s.name,
            "kind": s.kind,
            "metadata": s.metadata,
            "line_start": s.line_start,
        }
        for s in result.symbols
    ]


def _parse_file(src: str, suffix: str = ".js") -> list[dict[str, Any]]:
    """Write ``src`` to a temp file and parse it through parse_file."""
    assert _PARSER is not None
    with tempfile.NamedTemporaryFile(suffix=suffix, mode="w", delete=False) as f:
        f.write(src)
        tmp = Path(f.name)
    try:
        result = _PARSER.parse_file(tmp)
        assert result is not None, f"parse_file returned None for {tmp}"
        return [
            {
                "name": s.name,
                "kind": s.kind,
                "metadata": s.metadata,
                "line_start": s.line_start,
            }
            for s in result.symbols
        ]
    finally:
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Arrow function naming
# ---------------------------------------------------------------------------


@_skip_no_js
def test_arrow_function_named_from_const_binding() -> None:
    """Arrow function assigned to a ``const`` binding should have the binding name."""
    src = "const fn = (x) => x + 1;"
    syms = _parse(src)
    names = [s["name"] for s in syms]
    assert "fn" in names, f"Expected 'fn' in symbols, got {names}"


@_skip_no_js
def test_arrow_function_kind_is_function() -> None:
    """Arrow function at module scope should have kind='function', not 'method'."""
    src = "const compute = (a, b) => a * b;"
    syms = _parse(src)
    arrow_syms = [s for s in syms if s["name"] == "compute"]
    assert arrow_syms, "No symbol named 'compute' found"
    assert arrow_syms[0]["kind"] == "function"


@_skip_no_js
def test_arrow_function_let_binding() -> None:
    """Arrow function assigned via ``let`` should inherit the binding name."""
    src = "let handler = (event) => event.preventDefault();"
    syms = _parse(src)
    names = [s["name"] for s in syms]
    assert "handler" in names, f"Expected 'handler', got {names}"


@_skip_no_js
def test_arrow_function_via_temp_file() -> None:
    """Arrow function naming works when parsing via a real temp file."""
    src = "const greet = (name) => `Hello, ${name}`;\n"
    syms = _parse_file(src, ".js")
    names = [s["name"] for s in syms]
    assert "greet" in names, f"Expected 'greet' in {names}"


# ---------------------------------------------------------------------------
# Async functions
# ---------------------------------------------------------------------------


@_skip_no_js
def test_async_function_declaration_marked() -> None:
    """``async function`` should have ``metadata["is_async"] = True``."""
    src = "async function fetchData() { return await Promise.resolve(1); }"
    syms = _parse(src)
    fetch_syms = [s for s in syms if s["name"] == "fetchData"]
    assert fetch_syms, "No symbol 'fetchData' found"
    assert fetch_syms[0]["metadata"].get("is_async") is True, (
        f"Expected is_async=True, got metadata={fetch_syms[0]['metadata']}"
    )


@_skip_no_js
def test_sync_function_not_marked_async() -> None:
    """Synchronous function should NOT have ``is_async`` in metadata."""
    src = "function plain() { return 1; }"
    syms = _parse(src)
    plain_syms = [s for s in syms if s["name"] == "plain"]
    assert plain_syms, "No symbol 'plain' found"
    assert not plain_syms[0]["metadata"].get("is_async"), (
        "Sync function should not be marked async"
    )


@_skip_no_js
def test_async_arrow_function_marked() -> None:
    """``const f = async (x) => x`` should carry ``is_async = True``."""
    src = "const process = async (item) => item.id;"
    syms = _parse(src)
    proc_syms = [s for s in syms if s["name"] == "process"]
    assert proc_syms, f"No symbol 'process' found in {[s['name'] for s in syms]}"
    assert proc_syms[0]["metadata"].get("is_async") is True


# ---------------------------------------------------------------------------
# Class extends / bases
# ---------------------------------------------------------------------------


@_skip_no_js
def test_class_extends_base_captured() -> None:
    """Class with ``extends`` should expose the base name in metadata."""
    src = "class Animal extends LivingThing { constructor() { super(); } }"
    syms = _parse(src)
    cls_syms = [s for s in syms if s["kind"] == "class"]
    assert cls_syms, "No class symbols found"
    animal = cls_syms[0]
    assert animal["name"] == "Animal"
    bases = animal["metadata"].get("bases", [])
    assert "LivingThing" in bases, f"Expected 'LivingThing' in bases, got {bases}"


@_skip_no_js
def test_class_no_extends_has_no_bases() -> None:
    """Class without ``extends`` should have no bases in metadata."""
    src = "class Standalone { constructor() {} }"
    syms = _parse(src)
    cls_syms = [s for s in syms if s["kind"] == "class"]
    assert cls_syms, "No class symbols found"
    bases = cls_syms[0]["metadata"].get("bases", [])
    assert bases == [], f"Expected empty bases, got {bases}"


@_skip_no_js
def test_class_constructor_is_method() -> None:
    """Constructor inside a class body should have kind='method'."""
    src = "class A extends B { constructor() { super(); } }"
    syms = _parse(src)
    method_syms = [s for s in syms if s["kind"] == "method"]
    names = [s["name"] for s in method_syms]
    assert "constructor" in names, f"Expected 'constructor' method, got {names}"


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


@_skip_no_js
def test_decorator_attached_to_class() -> None:
    """A class preceded by a decorator should carry the decorator in metadata."""
    src = "@injectable() class Service { }"
    syms = _parse(src)
    cls_syms = [s for s in syms if s["kind"] == "class"]
    assert cls_syms, "No class symbol found"
    service = cls_syms[0]
    assert service["name"] == "Service"
    decorators = service["metadata"].get("decorators", [])
    assert decorators, f"Expected decorators in metadata, got {service['metadata']}"
    # The decorator name should contain 'injectable'
    assert any("injectable" in d for d in decorators), (
        f"Expected 'injectable' in decorators, got {decorators}"
    )


@_skip_no_js
def test_plain_class_has_no_decorators() -> None:
    """A class without decorators should not have a 'decorators' metadata key."""
    src = "class Plain { constructor() {} }"
    syms = _parse(src)
    cls_syms = [s for s in syms if s["kind"] == "class"]
    assert cls_syms, "No class symbol found"
    decorators = cls_syms[0]["metadata"].get("decorators", [])
    assert decorators == [], f"Expected no decorators, got {decorators}"


# ---------------------------------------------------------------------------
# TypeScript interface (TS grammar required)
# ---------------------------------------------------------------------------


@_skip_no_ts
def test_ts_interface_extracted_as_interface_kind() -> None:
    """TypeScript ``interface`` declarations should have kind='interface'."""
    src = "interface Point { x: number; y: number; }"
    syms = _parse(src, "typescript")
    iface_syms = [s for s in syms if s["kind"] == "interface"]
    assert iface_syms, f"No interface symbols found; got {syms}"
    assert iface_syms[0]["name"] == "Point"


@_skip_no_ts
def test_ts_interface_name_correct() -> None:
    """Interface name is extracted correctly from the declaration."""
    src = "interface Serializable { serialize(): string; }"
    syms = _parse(src, "typescript")
    names = [s["name"] for s in syms if s["kind"] == "interface"]
    assert "Serializable" in names, f"Expected 'Serializable', got {names}"


@_skip_no_ts
def test_ts_interface_via_file() -> None:
    """Interface extraction works when parsing a real ``.ts`` file."""
    src = "interface Config { host: string; port: number; }\n"
    syms = _parse_file(src, ".ts")
    iface_syms = [s for s in syms if s["kind"] == "interface"]
    assert iface_syms, f"No interface symbols found in file parse; got {syms}"
    assert iface_syms[0]["name"] == "Config"


# ---------------------------------------------------------------------------
# TypeScript generics (TS grammar required)
# ---------------------------------------------------------------------------


@_skip_no_ts
def test_ts_generic_function_type_params() -> None:
    """Generic function should expose type parameters in metadata."""
    src = "function identity<T>(x: T): T { return x; }"
    syms = _parse(src, "typescript")
    fn_syms = [s for s in syms if s["name"] == "identity"]
    assert fn_syms, f"No 'identity' symbol; got {syms}"
    type_params = fn_syms[0]["metadata"].get("type_params", [])
    assert type_params, (
        f"Expected type_params in metadata, got {fn_syms[0]['metadata']}"
    )
    assert "T" in type_params, f"Expected 'T' in type_params, got {type_params}"


@_skip_no_ts
def test_ts_generic_class_type_params() -> None:
    """Generic class should expose type parameters in metadata."""
    src = "class Box<T> { value: T; }"
    syms = _parse(src, "typescript")
    cls_syms = [s for s in syms if s["kind"] == "class"]
    assert cls_syms, f"No class symbols; got {syms}"
    type_params = cls_syms[0]["metadata"].get("type_params", [])
    assert "T" in type_params, f"Expected 'T' in type_params, got {type_params}"


# ---------------------------------------------------------------------------
# JS grammar fallback: interface not available but function still parses
# ---------------------------------------------------------------------------


@_skip_no_js
def test_js_grammar_function_declaration_baseline() -> None:
    """Baseline: simple function declaration parses correctly with JS grammar."""
    src = "function add(a, b) { return a + b; }"
    syms = _parse(src, "javascript")
    fn_syms = [s for s in syms if s["name"] == "add"]
    assert fn_syms, f"No 'add' symbol found; got {syms}"
    assert fn_syms[0]["kind"] == "function"


@_skip_no_js
def test_js_grammar_class_declaration_baseline() -> None:
    """Baseline: class declaration parses correctly with JS grammar."""
    src = "class Greeter { greet(name) { return `Hello, ${name}`; } }"
    syms = _parse(src, "javascript")
    cls_syms = [s for s in syms if s["kind"] == "class"]
    assert cls_syms, f"No class symbols; got {syms}"
    assert cls_syms[0]["name"] == "Greeter"


@_skip_no_js
def test_js_parse_file_round_trip(tmp_path: Path) -> None:
    """Parsing a real ``.js`` file via ``parse_file`` yields expected symbols."""
    js_file = tmp_path / "module.js"
    js_file.write_text(
        "const double = (n) => n * 2;\n"
        "async function load() { return await fetch('/api'); }\n"
        "class Widget extends BaseWidget { render() {} }\n",
        encoding="utf-8",
    )
    result = _PARSER.parse_file(js_file)
    assert result is not None
    names = {s.name for s in result.symbols}
    assert "double" in names, f"Expected 'double', got {names}"
    assert "load" in names, f"Expected 'load', got {names}"
    assert "Widget" in names, f"Expected 'Widget', got {names}"

    # is_async on load
    load_sym = next(s for s in result.symbols if s.name == "load")
    assert load_sym.metadata.get("is_async") is True

    # bases on Widget
    widget_sym = next(s for s in result.symbols if s.name == "Widget")
    assert "BaseWidget" in widget_sym.metadata.get("bases", [])
