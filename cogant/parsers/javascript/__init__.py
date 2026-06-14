"""JavaScript language parser package.

Exposes :class:`JavaScriptLanguageParser`, a tree-sitter backed plugin
defined in :mod:`parsers.javascript.parser`. For compatibility with the
pre-tree-sitter plugin layout, the compatibility alias pointing at
``TypeScriptLanguageParser`` is still available under
``CompatibilityJavaScriptLanguageParser``.
"""

from parsers.javascript.parser import JavaScriptLanguageParser

try:  # pragma: no cover - compat shim
    from parsers.typescript.parser import TypeScriptLanguageParser as _TS

    CompatibilityJavaScriptLanguageParser = _TS
except Exception:  # pragma: no cover
    CompatibilityJavaScriptLanguageParser = None  # type: ignore[assignment]

__all__ = ["JavaScriptLanguageParser", "CompatibilityJavaScriptLanguageParser"]
