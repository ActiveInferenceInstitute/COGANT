"""JavaScript language parser (uses TypeScript parser)."""

# JavaScript is supported through the TypeScript parser
from parsers.typescript.parser import TypeScriptLanguageParser

# Alias for clarity
JavaScriptLanguageParser = TypeScriptLanguageParser

__all__ = ["JavaScriptLanguageParser"]
