"""TypeScript and tree-sitter parser implementations."""

from .parser import ParseResult, TypeScriptLanguageParser
from .tree_sitter_parser import TypeScriptTreeSitterParser

__all__ = ["ParseResult", "TypeScriptLanguageParser", "TypeScriptTreeSitterParser"]
