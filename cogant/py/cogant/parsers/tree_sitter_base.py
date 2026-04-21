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
from typing import Any

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
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedFile:
    """Result of parsing a single source file."""

    path: str
    language: str
    symbols: list[ParsedSymbol] = field(default_factory=list)
    imports: list[dict[str, Any]] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


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

    _LANGUAGE_MAP: dict[str, str] = {
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
        self._parsers: dict[str, Any] = {}  # lang -> tree_sitter.Parser
        self._languages: dict[str, Any] = {}  # lang -> tree_sitter.Language
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
            import tree_sitter  # type: ignore[import-not-found,unused-ignore]  # noqa: F401
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
                logger.debug("tree-sitter grammar %s has no %s()", module_name, fn_name)
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

    def available_languages(self) -> set[str]:
        """Return the set of language names with a loaded parser."""
        return set(self._parsers.keys())

    def supported_extensions(self) -> set[str]:
        """Return file extensions that can be parsed by a loaded grammar."""
        exts = set()
        for ext, lang in self._LANGUAGE_MAP.items():
            if lang in self._parsers:
                exts.add(ext)
        return exts

    def language_for_path(self, path: Path) -> str | None:
        """Return the language name for a given file path, or None."""
        return self._LANGUAGE_MAP.get(path.suffix.lower())

    def parse_file(self, path: Path) -> ParsedFile | None:
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

    def parse_source(self, source: str, language: str, path: str = "") -> ParsedFile | None:
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
            return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
        except (AttributeError, UnicodeDecodeError):
            return ""

    def extract_symbols(
        self, tree: Any, source: bytes, path: str
    ) -> list[ParsedSymbol]:  # pragma: no cover - overridden
        """Return parsed symbols from a tree-sitter tree (overridden by subclasses)."""
        return []

    def extract_imports(self, tree: Any, source: bytes) -> list[dict[str, Any]]:  # pragma: no cover
        """Return import records from a tree-sitter tree (overridden by subclasses)."""
        return []

    def extract_calls(self, tree: Any, source: bytes) -> list[dict[str, Any]]:  # pragma: no cover
        """Return call records from a tree-sitter tree (overridden by subclasses)."""
        return []


class _PythonExtractor(_BaseExtractor):
    """Extract symbols from a Python tree-sitter AST."""

    def extract_symbols(self, tree: Any, source: bytes, path: str) -> list[ParsedSymbol]:
        """Walk the Python tree-sitter tree and collect class/function symbols."""
        symbols: list[ParsedSymbol] = []

        def visit(node: Any, scope: str = "") -> None:
            """Recurse into ``node`` carrying the current qualified-name ``scope``."""
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

    def extract_imports(self, tree: Any, source: bytes) -> list[dict[str, Any]]:
        """Collect ``import`` and ``from ... import`` statements from a Python tree."""
        imports: list[dict[str, Any]] = []

        def visit(node: Any) -> None:
            """Recursively visit ``node`` and append any import statement records."""
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

    def extract_calls(self, tree: Any, source: bytes) -> list[dict[str, Any]]:
        """Collect function/method ``call`` nodes from a Python tree."""
        calls: list[dict[str, Any]] = []

        def visit(node: Any) -> None:
            """Recursively visit ``node`` and append any call-site records."""
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

    # Node types that can hold an arrow_function or function_expression
    # as their right-hand side, giving the symbol its lexical name.
    _VAR_DECL_TYPES = {
        "variable_declarator",
        "assignment_expression",
    }

    @staticmethod
    def _has_child_type(node: Any, child_type: str) -> bool:
        """Return True iff any direct child of ``node`` has type ``child_type``."""
        return any(c.type == child_type for c in node.children)

    def _collect_decorators(self, node: Any, source: bytes) -> list[str]:
        """Return decorator name strings attached as direct children of ``node``."""
        decorators: list[str] = []
        for child in node.children:
            if child.type == "decorator":
                # The decorator body: `@name` or `@name(args)`.
                # We slice everything after the leading `@`.
                raw = self._slice(source, child)
                # raw is e.g. "@injectable()" — trim the "@" prefix.
                decorators.append(raw.lstrip("@").strip())
        return decorators

    def _bases_of_class(self, node: Any, source: bytes) -> list[str]:
        """Return base-class name strings from a ``class_heritage`` child."""
        for child in node.children:
            if child.type == "class_heritage":
                # Collect identifiers / member_expressions after "extends"
                bases: list[str] = []
                for gc in child.children:
                    if gc.type not in ("extends", ","):
                        text = self._slice(source, gc).strip()
                        if text:
                            bases.append(text)
                return bases
        return []

    def _name_from_parent(self, node: Any, source: bytes) -> str | None:
        """Try to infer a name for ``node`` from its parent variable declarator.

        Arrow functions and anonymous function expressions assigned to a
        ``const``/``let``/``var`` binding should inherit the binding name
        so the graph stays useful.  Returns ``None`` if no parent name can
        be determined.
        """
        parent = node.parent
        if parent is None:
            return None
        if parent.type in self._VAR_DECL_TYPES:
            name_node = parent.child_by_field_name("name")
            if name_node is not None:
                return self._slice(source, name_node)
            # assignment_expression: left side
            left = parent.child_by_field_name("left")
            if left is not None:
                return self._slice(source, left)
        return None

    def _is_async(self, node: Any) -> bool:
        """Return True iff ``node`` has a direct ``async`` keyword child."""
        return self._has_child_type(node, "async")

    def _type_params_of(self, node: Any, source: bytes) -> list[str]:
        """Return TypeScript type parameter names (e.g. ``["T", "U"]``)."""
        for child in node.children:
            if child.type == "type_parameters":
                params: list[str] = []
                for gc in child.children:
                    if gc.type in ("type_parameter", "identifier"):
                        text = self._slice(source, gc).strip()
                        if text:
                            params.append(text)
                return params
        return []

    def extract_symbols(self, tree: Any, source: bytes, path: str) -> list[ParsedSymbol]:
        """Walk the JS/TS tree-sitter tree and collect class/interface/function symbols.

        Advanced patterns handled:
        * Arrow functions assigned to ``const``/``let``/``var`` → named symbol
        * ``async`` functions/arrows → ``metadata["is_async"] = True``
        * ``class … extends Base`` → ``metadata["bases"] = ["Base"]``
        * Decorators → ``metadata["decorators"] = ["injectable()"]``
        * TypeScript generic type params → ``metadata["type_params"] = ["T"]``
        * TypeScript ``interface`` declarations → ``kind="interface"``
        """
        symbols: list[ParsedSymbol] = []

        def name_of(node: Any) -> str:
            """Return the declared name of ``node`` or ``"<anonymous>"``."""
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                return self._slice(source, name_node)
            # For arrow functions / anonymous expressions try the parent binding.
            inferred = self._name_from_parent(node, source)
            if inferred:
                return inferred
            return "<anonymous>"

        def visit(node: Any, scope: str = "") -> None:
            """Recurse into ``node`` carrying the current qualified-name ``scope``."""
            if node.type in self._CLASS_TYPES:
                name = name_of(node)
                qname = f"{scope}.{name}" if scope else name
                bases = self._bases_of_class(node, source)
                decorators = self._collect_decorators(node, source)
                type_params = self._type_params_of(node, source)
                meta: dict[str, Any] = {}
                if bases:
                    meta["bases"] = bases
                if decorators:
                    meta["decorators"] = decorators
                if type_params:
                    meta["type_params"] = type_params
                symbols.append(
                    ParsedSymbol(
                        name=name,
                        kind="class",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        qualified_name=qname,
                        metadata=meta,
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
                type_params = self._type_params_of(node, source)
                meta = {}
                if type_params:
                    meta["type_params"] = type_params
                symbols.append(
                    ParsedSymbol(
                        name=name,
                        kind="interface",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        qualified_name=qname,
                        metadata=meta,
                    )
                )
                return
            if node.type in self._FUNCTION_TYPES:
                name = name_of(node)
                qname = f"{scope}.{name}" if scope and name != "<anonymous>" else name
                is_async = self._is_async(node)
                type_params = self._type_params_of(node, source)
                decorators = self._collect_decorators(node, source)
                meta = {}
                if is_async:
                    meta["is_async"] = True
                if type_params:
                    meta["type_params"] = type_params
                if decorators:
                    meta["decorators"] = decorators
                symbols.append(
                    ParsedSymbol(
                        name=name,
                        kind="method" if scope else "function",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        qualified_name=qname,
                        metadata=meta,
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

    def extract_imports(self, tree: Any, source: bytes) -> list[dict[str, Any]]:
        """Collect ES module ``import`` statements and import clauses from a JS/TS tree."""
        imports: list[dict[str, Any]] = []

        def visit(node: Any) -> None:
            """Recursively visit ``node`` and append any import statement records."""
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

    def extract_calls(self, tree: Any, source: bytes) -> list[dict[str, Any]]:
        """Collect ``call_expression`` nodes from a JS/TS tree."""
        calls: list[dict[str, Any]] = []

        def visit(node: Any) -> None:
            """Recursively visit ``node`` and append any call-site records."""
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


_instance: TreeSitterParser | None = None


def get_tree_sitter_parser() -> TreeSitterParser:
    """Return the process-wide :class:`TreeSitterParser` instance."""
    global _instance
    if _instance is None:
        _instance = TreeSitterParser()
    return _instance
