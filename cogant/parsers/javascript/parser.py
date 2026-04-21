"""JavaScript language parser plugin backed by tree-sitter.

Unlike the legacy regex-based ``TypeScriptLanguageParser`` (which still
covers both JS and TS), this plugin delegates to the shared
``cogant.parsers.tree_sitter_base.TreeSitterParser`` so it can produce
proper AST-based symbol tables with nested-scope qualified names.

If the ``tree-sitter`` runtime or the ``tree_sitter_javascript`` grammar
aren't installed, the plugin falls back to an empty result with a
descriptive error message — callers can check ``result["error"]`` to
detect the degraded mode and optionally route through the legacy regex
parser.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure ``py/cogant`` is importable when this module is loaded via the
# sibling ``parsers/`` sys.path entry the rest of the plugin suite uses.
_PY_ROOT = Path(__file__).resolve().parent.parent.parent / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.parsers.tree_sitter_base import (  # noqa: E402
    ParsedFile,
    get_tree_sitter_parser,
)
from parsers._base import CogantLanguagePlugin  # noqa: E402


class JavaScriptLanguageParser(CogantLanguagePlugin):
    """Parser for JavaScript source files (tree-sitter backed)."""

    PLUGIN_NAME = "javascript"
    PLUGIN_VERSION = "0.2.0"
    PLUGIN_DESCRIPTION = "tree-sitter backed parser for JavaScript source files"
    SUPPORTED_LANGUAGES = {"javascript"}
    SUPPORTED_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: dict[str, Any]) -> None:
        """Warm up the underlying tree-sitter parser."""
        get_tree_sitter_parser()

    def shutdown(self) -> None:
        """No-op — the singleton lives for the life of the process."""

    # ------------------------------------------------------------------
    # LanguagePlugin API
    # ------------------------------------------------------------------

    def parse(self, source_code: str, file_path: str = "") -> dict[str, Any]:
        """Parse JavaScript source code into a serializable dict."""
        parser = get_tree_sitter_parser()
        result: ParsedFile | None = parser.parse_source(source_code, "javascript", file_path)
        if result is None:
            return {
                "symbols": [],
                "imports": [],
                "calls": [],
                "errors": ["tree-sitter javascript grammar not available"],
                "error": "tree-sitter javascript grammar not available",
            }
        return {
            "symbols": [s.__dict__ for s in result.symbols],
            "imports": result.imports,
            "calls": result.calls,
            "errors": result.errors,
        }

    def extract_symbols(self, ast: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract symbols from a previously produced AST dict."""
        return list(ast.get("symbols", []))

    def extract_types(self, ast: dict[str, Any]) -> dict[str, Any]:
        """JavaScript has no static type system; return empty type map."""
        return {}

    def resolve_imports(self, ast: dict[str, Any]) -> list[dict[str, Any]]:
        """Return the import descriptors from a parsed AST dict."""
        return list(ast.get("imports", []))

    # ------------------------------------------------------------------
    # Convenience helpers (consistent with PythonLanguageParser)
    # ------------------------------------------------------------------

    def parse_file(self, file_path: Path) -> dict[str, Any]:
        """Parse a JavaScript file on disk."""
        parser = get_tree_sitter_parser()
        if isinstance(file_path, str):
            file_path = Path(file_path)
        result = parser.parse_file(file_path)
        if result is None:
            return {
                "file_path": str(file_path),
                "symbols": [],
                "imports": [],
                "calls": [],
                "errors": ["tree-sitter javascript grammar not available"],
            }
        return {
            "file_path": result.path,
            "symbols": [s.__dict__ for s in result.symbols],
            "imports": result.imports,
            "calls": result.calls,
            "errors": result.errors,
        }

    def extract_calls(self, source_code: str = "", file_path: str = "") -> list[dict[str, Any]]:
        """Return call sites from a JavaScript source string."""
        parser = get_tree_sitter_parser()
        result = parser.parse_source(source_code, "javascript", file_path)
        return list(result.calls) if result else []

    def get_node_kinds(self) -> set[str]:
        """Supported NodeKind values for JavaScript."""
        return {
            "ClassDeclaration",
            "FunctionDeclaration",
            "MethodDefinition",
            "ArrowFunction",
            "ImportStatement",
            "CallExpression",
        }
