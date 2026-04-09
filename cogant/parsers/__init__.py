"""Language parsers for COGANT."""

from parsers.python.parser import PythonLanguageParser
from parsers.typescript.parser import TypeScriptLanguageParser
from parsers.rust.parser import RustLanguageParser
from parsers.go.parser import GoLanguageParser
from parsers.javascript.parser import JavaScriptLanguageParser

try:
    from parsers.typescript.tree_sitter_parser import TypeScriptTreeSitterParser
except Exception:  # pragma: no cover - optional tree-sitter dependency
    TypeScriptTreeSitterParser = None  # type: ignore[assignment]

__all__ = [
    "PythonLanguageParser",
    "TypeScriptLanguageParser",
    "TypeScriptTreeSitterParser",
    "JavaScriptLanguageParser",
    "RustLanguageParser",
    "GoLanguageParser",
]
