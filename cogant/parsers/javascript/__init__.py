"""JavaScript language parser package.

Exposes :class:`JavaScriptLanguageParser`, a tree-sitter backed plugin
defined in :mod:`parsers.javascript.parser`. For compatibility with the
pre-tree-sitter plugin layout, the legacy alias pointing at
``TypeScriptLanguageParser`` is still available under
``LegacyJavaScriptLanguageParser``.
"""

from parsers.javascript.parser import JavaScriptLanguageParser

try:  # pragma: no cover - compat shim
    from parsers.typescript.parser import TypeScriptLanguageParser as _TS
    LegacyJavaScriptLanguageParser = _TS
except Exception:  # pragma: no cover
    LegacyJavaScriptLanguageParser = None  # type: ignore[assignment]

__all__ = ["JavaScriptLanguageParser", "LegacyJavaScriptLanguageParser"]
