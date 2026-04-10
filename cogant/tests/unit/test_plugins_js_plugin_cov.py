"""Behavioral tests for cogant.plugins.js_plugin.JsLanguagePlugin.

Drives every public method of the plugin. When the tree-sitter runtime
is absent (the common case in CI), ``parse`` and ``parse_path`` exercise
their fallback branches; when it is present they run the real parser.
"""

from __future__ import annotations

from pathlib import Path

from cogant.plugins.js_plugin import JsLanguagePlugin
from cogant.static import treesitter_parser as _ts


# --------------------------- construction ------------------------------ #


def test_plugin_metadata_and_supported_languages():
    """Constructor fills metadata and registers JS/TS dialects."""
    p = JsLanguagePlugin()
    assert p.metadata.name == "cogant.plugins.js"
    assert p.metadata.version == "0.1.0"
    assert p.metadata.author == "COGANT Contributors"
    assert "javascript" in p.supported_languages
    assert "typescript" in p.supported_languages
    assert "jsx" in p.supported_languages
    assert "tsx" in p.supported_languages


# --------------------------- lifecycle ---------------------------------- #


def test_initialize_and_shutdown_toggle_internal_flag():
    """initialize() flips the internal flag; shutdown() clears it."""
    p = JsLanguagePlugin()
    assert p._initialized is False
    p.initialize({})
    assert p._initialized is True
    p.shutdown()
    assert p._initialized is False


def test_initialize_with_nontrivial_config_is_accepted():
    """Any dict config is accepted; no keys are required."""
    p = JsLanguagePlugin()
    p.initialize({"strict": True, "jsx": False})
    assert p._initialized is True


# --------------------------- parse -------------------------------------- #


def test_parse_returns_envelope_dict():
    """parse() always returns a dict with language/parsed/available keys."""
    p = JsLanguagePlugin()
    result = p.parse("const x = 1;")
    assert isinstance(result, dict)
    assert result["language"] == "javascript"
    assert "parsed" in result
    assert "available" in result


def test_parse_when_tree_sitter_missing_returns_unavailable(monkeypatch):
    """Without the tree-sitter runtime, parse() reports unavailable."""
    monkeypatch.setattr(_ts, "HAS_TREESITTER", False)
    p = JsLanguagePlugin()
    result = p.parse("function f() {}")
    assert result["available"] is False
    assert result["parsed"] is None


# --------------------------- extract_symbols --------------------------- #


def test_extract_symbols_empty_when_parsed_is_none():
    """extract_symbols() returns [] for an envelope with no parsed file."""
    p = JsLanguagePlugin()
    assert p.extract_symbols({"parsed": None}) == []


def test_extract_symbols_empty_for_non_dict_ast():
    """A non-dict argument also produces an empty list (defensive)."""
    p = JsLanguagePlugin()
    assert p.extract_symbols("not-a-dict") == []  # type: ignore[arg-type]


def test_extract_symbols_from_fake_parsed_file():
    """A parsed file with symbols yields dict entries with expected keys."""
    class _Sym:
        def __init__(self, name, kind):
            self.name = name
            self.kind = kind
            self.qualified_name = f"mod.{name}"
            self.line_start = 1
            self.line_end = 5

    class _Parsed:
        symbols = [_Sym("foo", "function"), _Sym("Bar", "class")]

    p = JsLanguagePlugin()
    out = p.extract_symbols({"parsed": _Parsed()})
    assert len(out) == 2
    assert out[0] == {
        "name": "foo",
        "kind": "function",
        "qualified_name": "mod.foo",
        "line_start": 1,
        "line_end": 5,
    }
    assert out[1]["name"] == "Bar"


# --------------------------- extract_types ------------------------------ #


def test_extract_types_returns_empty_mapping():
    """Type extraction is intentionally a no-op; always returns {}."""
    p = JsLanguagePlugin()
    assert p.extract_types({"parsed": None}) == {}
    assert p.extract_types({"parsed": "whatever"}) == {}


# --------------------------- resolve_imports --------------------------- #


def test_resolve_imports_empty_when_parsed_is_none():
    """resolve_imports() returns [] when nothing has been parsed."""
    p = JsLanguagePlugin()
    assert p.resolve_imports({"parsed": None}) == []


def test_resolve_imports_empty_for_non_dict_ast():
    """resolve_imports() tolerates non-dict input."""
    p = JsLanguagePlugin()
    assert p.resolve_imports(42) == []  # type: ignore[arg-type]


def test_resolve_imports_from_fake_parsed_file():
    """Import dicts with a 'raw' key are returned verbatim."""
    class _Parsed:
        imports = [{"raw": "import x from 'x';"}, {"raw": "import y from 'y';"}, {}]

    p = JsLanguagePlugin()
    out = p.resolve_imports({"parsed": _Parsed()})
    # The empty dict is skipped because raw is absent / falsy
    assert out == ["import x from 'x';", "import y from 'y';"]


# --------------------------- parse_path --------------------------------- #


def test_parse_path_delegates_to_tree_sitter_parser(tmp_path, monkeypatch):
    """parse_path() is a thin wrapper around treesitter_parser.parse_file_treesitter."""
    called_with: dict = {}

    def _fake(path, language):
        called_with["path"] = path
        called_with["language"] = language
        return "sentinel-graph"

    monkeypatch.setattr(_ts, "parse_file_treesitter", _fake)
    p = JsLanguagePlugin()
    src = tmp_path / "app.js"
    src.write_text("const n = 1;")
    result = p.parse_path(src)
    assert result == "sentinel-graph"
    assert called_with["path"] == src
    assert called_with["language"] == "auto"
