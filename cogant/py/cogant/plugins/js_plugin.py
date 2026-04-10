"""JavaScript / TypeScript language plugin (tree-sitter powered).

A minimal :class:`~cogant.plugins.base.LanguagePlugin` implementation
that routes parsing through
:mod:`cogant.static.treesitter_parser`. Its purpose is to demonstrate
the plugin contract for a non-Python language and to make the JS/TS
pipeline discoverable via the plugin registry — it is *not* a full
replacement for the tree-sitter substrate.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cogant.plugins.base import LanguagePlugin, PluginMetadata
from cogant.static import treesitter_parser as _ts

logger = logging.getLogger(__name__)


class JsLanguagePlugin(LanguagePlugin):
    """Language plugin for JavaScript and TypeScript source files."""

    supported_languages: set[str] = {"javascript", "typescript", "jsx", "tsx"}

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="cogant.plugins.js",
                version="0.1.0",
                author="COGANT Contributors",
                description="Tree-sitter JS/TS language plugin",
            )
        )
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: dict[str, Any]) -> None:
        """No-op initialization. Tree-sitter grammars load lazily."""
        self._initialized = True
        if not _ts.HAS_TREESITTER:
            logger.info(
                "JsLanguagePlugin initialized without tree-sitter runtime "
                "(install cogant[multilang] for full support)"
            )

    def shutdown(self) -> None:
        """Nothing to clean up; tree-sitter parsers are process-wide."""
        self._initialized = False

    # ------------------------------------------------------------------
    # LanguagePlugin contract
    # ------------------------------------------------------------------

    def parse(self, source_code: str) -> dict[str, Any]:
        """Parse JavaScript source code.

        The :class:`LanguagePlugin` contract asks for a generic
        ``dict`` — we return a minimal envelope with a tree-sitter
        :class:`cogant.parsers.tree_sitter_base.ParsedFile` attached as
        ``parsed`` so downstream code can access symbols / imports /
        calls without re-parsing.
        """
        if not _ts.HAS_TREESITTER:
            return {"language": "javascript", "parsed": None, "available": False}

        from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

        parser = get_tree_sitter_parser()
        parsed = parser.parse_source(source_code, language="javascript")
        return {
            "language": "javascript",
            "parsed": parsed,
            "available": parsed is not None,
        }

    def extract_symbols(self, ast: dict[str, Any]) -> list[dict[str, Any]]:
        """Return symbols (functions, classes, methods) from a parsed file."""
        parsed = ast.get("parsed") if isinstance(ast, dict) else None
        if parsed is None:
            return []
        return [
            {
                "name": s.name,
                "kind": s.kind,
                "qualified_name": s.qualified_name,
                "line_start": s.line_start,
                "line_end": s.line_end,
            }
            for s in parsed.symbols
        ]

    def extract_types(self, ast: dict[str, Any]) -> dict[str, Any]:
        """Tree-sitter alone doesn't give us a type environment.

        Returning an empty mapping keeps the plugin contract satisfied
        while making it explicit that richer TS type extraction is a
        follow-up task (tsc --emitDeclarationOnly or LSP hover).
        """
        return {}

    def resolve_imports(self, ast: dict[str, Any]) -> list[str]:
        """Return raw import strings from a parsed file."""
        parsed = ast.get("parsed") if isinstance(ast, dict) else None
        if parsed is None:
            return []
        return [imp.get("raw", "") for imp in parsed.imports if imp.get("raw")]

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def parse_path(self, path: Path) -> Any:
        """Parse a file on disk and return a :class:`ProgramGraph`.

        This is the ergonomic entry point mirroring the Python AST
        parser: give it a path, get a graph back.
        """
        return _ts.parse_file_treesitter(path, language="auto")


__all__ = ["JsLanguagePlugin"]
