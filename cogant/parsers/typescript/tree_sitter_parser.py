"""TypeScript language parser plugin backed by tree-sitter.

The compatibility :class:`parsers.typescript.parser.TypeScriptLanguageParser`
(regex-based) remains the default registered TS/JS parser for
existing pipelines and tests. This module
adds a parallel tree-sitter-backed implementation that prefers the
``tree_sitter_typescript`` grammar (with a ``.tsx`` variant) and falls
back gracefully when the optional ``multilang`` extras aren't
installed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PY_ROOT = Path(__file__).resolve().parent.parent.parent / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.parsers.tree_sitter_base import (  # noqa: E402
    ParsedFile,
    get_tree_sitter_parser,
)
from cogant.plugins.base import LanguagePlugin, PluginMetadata  # noqa: E402


class TypeScriptTreeSitterParser(LanguagePlugin):
    """Tree-sitter backed TypeScript / TSX parser."""

    SUPPORTED_EXTENSIONS: list[str] = [".ts", ".tsx"]

    def __init__(self) -> None:
        metadata = PluginMetadata(
            name="typescript",
            version="0.2.0",
            author="COGANT",
            description="tree-sitter backed parser for TypeScript / TSX",
        )
        super().__init__(metadata)
        self.supported_languages: set[str] = {"typescript", "tsx"}
        self.supported_extensions: set[str] = set(self.SUPPORTED_EXTENSIONS)

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: dict[str, Any]) -> None:
        get_tree_sitter_parser()

    def shutdown(self) -> None:
        """No-op — the singleton lives for the life of the process."""

    # ------------------------------------------------------------------
    # LanguagePlugin API
    # ------------------------------------------------------------------

    def parse(self, source_code: str, file_path: str = "") -> dict[str, Any]:
        """Parse TypeScript source; switches to TSX grammar for ``.tsx``."""
        language = "tsx" if file_path.lower().endswith(".tsx") else "typescript"
        parser = get_tree_sitter_parser()
        result: ParsedFile | None = parser.parse_source(source_code, language, file_path)
        if result is None:
            return {
                "symbols": [],
                "imports": [],
                "calls": [],
                "errors": [f"tree-sitter {language} grammar not available"],
                "error": f"tree-sitter {language} grammar not available",
            }
        return {
            "language": language,
            "symbols": [s.__dict__ for s in result.symbols],
            "imports": result.imports,
            "calls": result.calls,
            "errors": result.errors,
        }

    def extract_symbols(self, ast: dict[str, Any]) -> list[dict[str, Any]]:
        return list(ast.get("symbols", []))

    def extract_types(self, ast: dict[str, Any]) -> dict[str, Any]:
        """Return a lightweight type map: interfaces and class names.

        Tree-sitter does not resolve type annotations, so this is a
        best-effort structural view that keeps the shape of the
        compatibility regex parser's output.
        """
        interfaces = [s for s in ast.get("symbols", []) if s.get("kind") == "interface"]
        classes = [s for s in ast.get("symbols", []) if s.get("kind") == "class"]
        return {
            "interfaces": [
                {"name": s["name"], "qualified_name": s["qualified_name"]} for s in interfaces
            ],
            "classes": [
                {"name": s["name"], "qualified_name": s["qualified_name"]} for s in classes
            ],
        }

    def resolve_imports(self, ast: dict[str, Any]) -> list[dict[str, Any]]:
        return list(ast.get("imports", []))

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def parse_file(self, file_path: Path) -> dict[str, Any]:
        if isinstance(file_path, str):
            file_path = Path(file_path)
        parser = get_tree_sitter_parser()
        result = parser.parse_file(file_path)
        if result is None:
            return {
                "file_path": str(file_path),
                "symbols": [],
                "imports": [],
                "calls": [],
                "errors": ["tree-sitter typescript grammar not available"],
            }
        return {
            "file_path": result.path,
            "language": result.language,
            "symbols": [s.__dict__ for s in result.symbols],
            "imports": result.imports,
            "calls": result.calls,
            "errors": result.errors,
        }

    def extract_calls(self, source_code: str = "", file_path: str = "") -> list[dict[str, Any]]:
        language = "tsx" if file_path.lower().endswith(".tsx") else "typescript"
        parser = get_tree_sitter_parser()
        result = parser.parse_source(source_code, language, file_path)
        return list(result.calls) if result else []

    def get_node_kinds(self) -> set[str]:
        return {
            "ClassDeclaration",
            "InterfaceDeclaration",
            "FunctionDeclaration",
            "MethodDefinition",
            "ArrowFunction",
            "ImportStatement",
            "CallExpression",
        }
