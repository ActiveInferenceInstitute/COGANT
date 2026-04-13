"""Universal tree-sitter parser substrate for multi-language analysis.

This sub-package exposes a single tree-sitter driven ``TreeSitterParser``
that can parse multiple languages (Python, JavaScript, TypeScript, TSX,
Rust, Go) through the same interface. Grammar packages are loaded lazily
at import time and unavailable languages degrade gracefully instead of
raising.

The older ``parsers/`` top-level plugins (``parsers/python/``,
``parsers/typescript/``, ``parsers/rust/``) remain the canonical
``LanguagePlugin`` implementations; this module provides the low-level
tree-sitter substrate they (optionally) delegate to.
"""

from cogant.parsers.tree_sitter_base import (
    ParsedFile,
    ParsedSymbol,
    TreeSitterParser,
    get_tree_sitter_parser,
)

__all__ = [
    "ParsedFile",
    "ParsedSymbol",
    "TreeSitterParser",
    "get_tree_sitter_parser",
]
