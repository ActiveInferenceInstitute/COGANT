"""Tree-sitter based universal parser substrate.

Provides a single ``TreeSitterParser`` that wraps the ``tree-sitter``
runtime and loads whatever language grammars are installed at import
time. Missing grammars are skipped with a debug log rather than raising,
so the rest of the COGANT pipeline keeps working even when the optional
``multilang`` extras are not installed.

Design notes
------------
* The parser is **read-only** with respect to the AST — it never
  modifies or re-synthesizes source. All extraction is done via
  per-language ``_Extractor`` classes that walk the tree-sitter
  concrete syntax tree and emit ``ParsedSymbol`` dataclasses.
* Extraction targets match the Python stdlib-``ast`` path's
  information density so callers can swap the two without losing
  fidelity: top-level functions, classes, methods, imports, and
  call sites (with line numbers).
* The instance is intended to be a process-wide singleton via
  :func:`get_tree_sitter_parser`, because loading grammars is mildly
  expensive and grammar objects are re-entrant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ParsedSymbol:
    """A symbol extracted from any language via tree-sitter."""

    name: str
    kind: str  # "function", "class", "variable", "import", "method", "interface"
    line_start: int
    line_end: int
    qualified_name: str
    docstring: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedFile:
    """Result of parsing a single source file."""

    path: str
    language: str
    symbols: List[ParsedSymbol] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    calls: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TreeSitterParser:
    """Universal tree-sitter based parser.

    One instance is normally enough per process; use
    :func:`get_tree_sitter_parser` to get the shared instance. The
    constructor tries to load every grammar COGANT knows about and
    silently skips the ones that aren't installed.
    """

    _LANGUAGE_MAP: Dict[str, str] = {
        ".py": "python",
        ".pyi": "python",
        ".pyx": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".rs": "rust",
        ".go": "go",
    }

    def __init__(self) -> None:
        self._parsers: Dict[str, Any] = {}  # lang -> tree_sitter.Parser
        self._languages: Dict[str, Any] = {}  # lang -> tree_sitter.Language
        self._load_available_languages()

    # ------------------------------------------------------------------
    # Grammar loading
    # ------------------------------------------------------------------

    def _load_available_languages(self) -> None:
        """Load whatever tree-sitter languages are installed.

        Each grammar package exposes a ``language()`` callable that
        returns an opaque pointer; :class:`tree_sitter.Language` wraps
        it and :class:`tree_sitter.Parser` takes the wrapped language
        as its single constructor argument.

        TypeScript ships two grammars in one package —
        ``language_typescript()`` and ``language_tsx()`` — so it gets
        special-cased.
        """
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            logger.debug("tree-sitter runtime not installed; no grammars loaded")
            return

        # Regular grammars: module exposes `language()`.
        regular = [
            ("python", "tree_sitter_python", "language"),
            ("javascript", "tree_sitter_javascript", "language"),
            ("rust", "tree_sitter_rust", "language"),
            ("go", "tree_sitter_go", "language"),
        ]

        for lang_name, module_name, fn_name in regular:
            self._try_load(lang_name, module_name, fn_name)

        # TypeScript has two grammars in a single package.
        self._try_load("typescript", "tree_sitter_typescript", "language_typescript")
        self._try_load("tsx", "tree_sitter_typescript", "language_tsx")

    def _try_load(self, lang_name: str, module_name: str, fn_name: str) -> None:
        try:
            import importlib

            import tree_sitter

            mod = importlib.import_module(module_name)
            language_fn = getattr(mod, fn_name, None)
            if language_fn is None:
                logger.debug(
                    "tree-sitter grammar %s has no %s()", module_name, fn_name
                )
                return
            language = tree_sitter.Language(language_fn())
            parser = tree_sitter.Parser(language)
            self._parsers[lang_name] = parser
            self._languages[lang_name] = language
            logger.info("Loaded tree-sitter grammar: %s", lang_name)
        except ImportError as exc:
            logger.debug("tree-sitter grammar unavailable: %s (%s)", lang_name, exc)
        except Exception as exc:  # pragma: no cover - grammar load errors
            logger.debug("Failed to initialize grammar %s: %s", lang_name, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def available_languages(self) -> Set[str]:
        """Return the set of language names with a loaded parser."""
        return set(self._parsers.keys())

    def supported_extensions(self) -> Set[str]:
        """Return file extensions that can be parsed by a loaded grammar."""
        exts = set()
        for ext, lang in self._LANGUAGE_MAP.items():
            if lang in self._parsers:
                exts.add(ext)
        return exts

    def language_for_path(self, path: Path) -> Optional[str]:
        """Return the language name for a given file path, or None."""
        return self._LANGUAGE_MAP.get(path.suffix.lower())

    def parse_file(self, path: Path) -> Optional[ParsedFile]:
        """Parse a file and return structured symbols.

        Returns ``None`` if the file's language is not recognized or
        its grammar isn't loaded. Returns a :class:`ParsedFile` with a
        populated ``errors`` list if reading or parsing fails.
        """
        if isinstance(path, str):
            path = Path(path)
        lang = self.language_for_path(path)
        if not lang or lang not in self._parsers:
            return None

        try:
            source = path.read_bytes()
        except OSError as exc:
            return ParsedFile(path=str(path), language=lang, errors=[f"read error: {exc}"])

        try:
            parser = self._parsers[lang]
            tree = parser.parse(source)
            extractor = _get_extractor(lang)
            symbols = extractor.extract_symbols(tree, source, str(path))
            imports = extractor.extract_imports(tree, source)
            calls = extractor.extract_calls(tree, source)
            return ParsedFile(
                path=str(path),
                language=lang,
                symbols=symbols,
                imports=imports,
                calls=calls,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to parse %s: %s", path, exc)
            return ParsedFile(path=str(path), language=lang, errors=[str(exc)])

    def parse_source(
        self, source: str, language: str, path: str = ""
    ) -> Optional[ParsedFile]:
        """Parse a source string in the given language."""
        if language not in self._parsers:
            return None
        try:
            parser = self._parsers[language]
            source_bytes = source.encode("utf-8", errors="replace")
            tree = parser.parse(source_bytes)
            extractor = _get_extractor(language)
            symbols = extractor.extract_symbols(tree, source_bytes, path)
            imports = extractor.extract_imports(tree, source_bytes)
            calls = extractor.extract_calls(tree, source_bytes)
            return ParsedFile(
                path=path,
                language=language,
                symbols=symbols,
                imports=imports,
                calls=calls,
            )
        except Exception as exc:  # pragma: no cover - defensive
            return ParsedFile(path=path, language=language, errors=[str(exc)])


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------


class _BaseExtractor:
    """Shared helpers for language-specific extractors."""

    @staticmethod
    def _slice(source: bytes, node: Any) -> str:
        try:
            return source[node.start_byte:node.end_byte].decode(
                "utf-8", errors="replace"
            )
        except (AttributeError, UnicodeDecodeError):
            return ""

    def extract_symbols(
        self, tree: Any, source: bytes, path: str
    ) -> List[ParsedSymbol]:  # pragma: no cover - overridden
        return []

    def extract_imports(self, tree: Any, source: bytes) -> List[Dict[str, Any]]:  # pragma: no cover
        return []

    def extract_calls(self, tree: Any, source: bytes) -> List[Dict[str, Any]]:  # pragma: no cover
        return []


class _PythonExtractor(_BaseExtractor):
    """Extract symbols from a Python tree-sitter AST."""

    def extract_symbols(
        self, tree: Any, source: bytes, path: str
    ) -> List[ParsedSymbol]:
        symbols: List[ParsedSymbol] = []

        def visit(node: Any, scope: str = "") -> None:
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node is not None:
                    name = self._slice(source, name_node)
                    qname = f"{scope}.{name}" if scope else name
                    symbols.append(
                        ParsedSymbol(
                            name=name,
                            kind="method" if scope else "function",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            qualified_name=qname,
                        )
                    )
                    body = node.child_by_field_name("body")
                    if body is not None:
                        for child in body.children:
                            visit(child, qname)
                    return
            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node is not None:
                    name = self._slice(source, name_node)
                    qname = f"{scope}.{name}" if scope else name
                    symbols.append(
                        ParsedSymbol(
                            name=name,
                            kind="class",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            qualified_name=qname,
                        )
                    )
                    body = node.child_by_field_name("body")
                    if body is not None:
                        for child in body.children:
                            visit(child, qname)
                    return
            for child in node.children:
                visit(child, scope)

        visit(tree.root_node)
        return symbols

    def extract_imports(self, tree: Any, source: bytes) -> List[Dict[str, Any]]:
        imports: List[Dict[str, Any]] = []

        def visit(node: Any) -> None:
            if node.type in ("import_statement", "import_from_statement"):
                imports.append(
                    {
                        "raw": self._slice(source, node),
                        "line": node.start_point[0] + 1,
                    }
                )
                return
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return imports

    def extract_calls(self, tree: Any, source: bytes) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []

        def visit(node: Any) -> None:
            if node.type == "call":
                fn_node = node.child_by_field_name("function")
                if fn_node is not None:
                    calls.append(
                        {
                            "callee": self._slice(source, fn_node),
                            "line": node.start_point[0] + 1,
                        }
                    )
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return calls


class _JavaScriptExtractor(_BaseExtractor):
    """Extract symbols from a JavaScript / TypeScript tree-sitter AST."""

    _FUNCTION_TYPES = {
        "function_declaration",
        "function_expression",
        "generator_function_declaration",
        "generator_function",
        "method_definition",
        "arrow_function",
    }

    _CLASS_TYPES = {
        "class_declaration",
        "class",
    }

    _INTERFACE_TYPES = {
        "interface_declaration",
    }

    def extract_symbols(
        self, tree: Any, source: bytes, path: str
    ) -> List[ParsedSymbol]:
        symbols: List[ParsedSymbol] = []

        def name_of(node: Any) -> str:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                return self._slice(source, name_node)
            return "<anonymous>"

        def visit(node: Any, scope: str = "") -> None:
            if node.type in self._CLASS_TYPES:
                name = name_of(node)
                qname = f"{scope}.{name}" if scope else name
                symbols.append(
                    ParsedSymbol(
                        name=name,
                        kind="class",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        qualified_name=qname,
                    )
                )
                body = node.child_by_field_name("body")
                if body is not None:
                    for child in body.children:
                        visit(child, qname)
                return
            if node.type in self._INTERFACE_TYPES:
                name = name_of(node)
                qname = f"{scope}.{name}" if scope else name
                symbols.append(
                    ParsedSymbol(
                        name=name,
                        kind="interface",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        qualified_name=qname,
                    )
                )
                return
            if node.type in self._FUNCTION_TYPES:
                name = name_of(node)
                qname = f"{scope}.{name}" if scope and name != "<anonymous>" else name
                symbols.append(
                    ParsedSymbol(
                        name=name,
                        kind="method" if scope else "function",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        qualified_name=qname,
                    )
                )
                # Recurse into body for nested functions / classes
                body = node.child_by_field_name("body")
                if body is not None:
                    for child in body.children:
                        visit(child, qname if name != "<anonymous>" else scope)
                return
            for child in node.children:
                visit(child, scope)

        visit(tree.root_node)
        return symbols

    def extract_imports(self, tree: Any, source: bytes) -> List[Dict[str, Any]]:
        imports: List[Dict[str, Any]] = []

        def visit(node: Any) -> None:
            if node.type in ("import_statement", "import_clause"):
                imports.append(
                    {
                        "raw": self._slice(source, node),
                        "line": node.start_point[0] + 1,
                    }
                )
                return
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return imports

    def extract_calls(self, tree: Any, source: bytes) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []

        def visit(node: Any) -> None:
            if node.type == "call_expression":
                fn_node = node.child_by_field_name("function")
                if fn_node is not None:
                    calls.append(
                        {
                            "callee": self._slice(source, fn_node),
                            "line": node.start_point[0] + 1,
                        }
                    )
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return calls


def _get_extractor(lang: str) -> _BaseExtractor:
    if lang == "python":
        return _PythonExtractor()
    if lang in ("javascript", "typescript", "tsx"):
        return _JavaScriptExtractor()
    # Fallback: use the JS extractor shape for any C-like language we don't
    # have a dedicated extractor for yet. It won't produce great results
    # but it won't crash either.
    return _JavaScriptExtractor()


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------


_instance: Optional[TreeSitterParser] = None


def get_tree_sitter_parser() -> TreeSitterParser:
    """Return the process-wide :class:`TreeSitterParser` instance."""
    global _instance
    if _instance is None:
        _instance = TreeSitterParser()
    return _instance
