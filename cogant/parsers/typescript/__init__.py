"""TypeScript/JavaScript language parser package."""

from .parser import TypeScriptLanguageParser

try:
    from .tree_sitter_parser import TypeScriptTreeSitterParser
except Exception:  # pragma: no cover - optional tree-sitter dependency
    TypeScriptTreeSitterParser = None  # type: ignore[assignment]

__all__ = ["TypeScriptLanguageParser", "TypeScriptTreeSitterParser"]
