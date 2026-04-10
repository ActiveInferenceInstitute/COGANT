"""Tree-sitter based multi-language static parser.

Provides a ``ProgramGraph`` extraction interface that mirrors the
stdlib-``ast`` based :class:`cogant.static.parser.PythonASTParser` but
routes through tree-sitter so JavaScript and TypeScript can share the
same node/edge vocabulary as Python.

The heavy lifting — grammar loading, walking the concrete syntax tree,
and emitting :class:`cogant.parsers.tree_sitter_base.ParsedSymbol`
records — already lives in
:mod:`cogant.parsers.tree_sitter_base`. This module is a thin adapter
that turns those language-agnostic symbols into typed
:class:`cogant.schemas.core.Node` / :class:`cogant.schemas.core.Edge`
objects on a :class:`cogant.schemas.graph.ProgramGraph`.

Language routing
----------------
* ``.py``     → ``parse_python_file``  (tree-sitter-python; ast fallback)
* ``.js``     → ``parse_js_file``
* ``.mjs``    → ``parse_js_file``
* ``.cjs``    → ``parse_js_file``
* ``.jsx``    → ``parse_js_file``
* ``.ts``     → ``parse_ts_file``
* ``.tsx``    → ``parse_ts_file``

If the ``tree-sitter`` runtime or a specific grammar is not installed
(i.e. the ``multilang`` extras are missing), ``parse_file_treesitter``
returns ``None`` for non-Python files and transparently delegates to
the stdlib-``ast`` Python parser for ``.py`` files.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Availability probe
# ---------------------------------------------------------------------------

def _treesitter_available() -> bool:
    """Return True iff the ``tree-sitter`` runtime can be imported."""
    try:
        import tree_sitter  # noqa: F401
    except ImportError:
        return False
    return True


HAS_TREESITTER: bool = _treesitter_available()


# ---------------------------------------------------------------------------
# Language → file-extension routing
# ---------------------------------------------------------------------------

_PY_EXTS = {".py", ".pyi", ".pyx"}
_JS_EXTS = {".js", ".jsx", ".mjs", ".cjs"}
_TS_EXTS = {".ts", ".tsx"}


def _detect_language(path: Path) -> str | None:
    """Return a canonical language name for ``path``'s suffix."""
    suffix = path.suffix.lower()
    if suffix in _PY_EXTS:
        return "python"
    if suffix in _JS_EXTS:
        return "javascript"
    if suffix in _TS_EXTS:
        return "typescript"
    return None


# ---------------------------------------------------------------------------
# Core adapter: ParsedFile → ProgramGraph
# ---------------------------------------------------------------------------

_KIND_MAP: dict[str, NodeKind] = {
    "function": NodeKind.FUNCTION,
    "method": NodeKind.METHOD,
    "class": NodeKind.CLASS,
    "interface": NodeKind.CLASS,  # map TS interface to class for now
}


def _graph_for_file(path: Path, language: str) -> ProgramGraph:
    """Build an empty ProgramGraph pre-seeded with the file node."""
    graph = ProgramGraph(
        metadata=GraphMetadata(
            repo_uri=str(path.parent),
            languages={language},
            evidence_sources=["static/treesitter"],
        ),
    )
    file_node = Node(
        id=f"file::{path}",
        kind=NodeKind.FILE,
        name=path.name,
        qualified_name=str(path),
        path=str(path),
        language=language,
    )
    graph.add_node(file_node)
    return graph


def _emit_parsed_file(path: Path, language: str, parsed) -> ProgramGraph:
    """Convert a :class:`ParsedFile` into a :class:`ProgramGraph`.

    Args:
        path: Source file path (used for the file-level node).
        language: Canonical language name ("python", "javascript", …).
        parsed: A ``ParsedFile`` from
            :func:`cogant.parsers.tree_sitter_base.TreeSitterParser.parse_file`.

    Returns:
        A populated :class:`ProgramGraph`.
    """
    graph = _graph_for_file(path, language)
    file_id = f"file::{path}"

    # Symbols → Node
    for sym in parsed.symbols:
        kind = _KIND_MAP.get(sym.kind, NodeKind.FUNCTION)
        node_id = f"{language}::{path}::{sym.qualified_name}::{sym.line_start}"
        node = Node(
            id=node_id,
            kind=kind,
            name=sym.name,
            qualified_name=sym.qualified_name,
            path=str(path),
            language=language,
            source_range={
                "start_line": sym.line_start,
                "end_line": sym.line_end,
            },
            metadata={"ts_kind": sym.kind, **sym.metadata},
        )
        graph.add_node(node)

        # file CONTAINS symbol
        contains = Edge(
            id=f"{file_id}->{node_id}::contains",
            source_id=file_id,
            target_id=node_id,
            kind=EdgeKind.CONTAINS,
            evidence_sources=["static/treesitter"],
        )
        graph.add_edge(contains)

    # Imports → synthetic module node + IMPORTS edge
    for idx, imp in enumerate(parsed.imports):
        raw = (imp.get("raw") or "").strip().replace("\n", " ")
        if not raw:
            continue
        mod_id = f"import::{path}::{idx}"
        mod_node = Node(
            id=mod_id,
            kind=NodeKind.MODULE,
            name=raw[:80],
            qualified_name=raw,
            path=str(path),
            language=language,
            source_range={"start_line": imp.get("line", 0)},
            metadata={"import_raw": raw},
        )
        graph.add_node(mod_node)
        edge = Edge(
            id=f"{file_id}->{mod_id}::imports",
            source_id=file_id,
            target_id=mod_id,
            kind=EdgeKind.IMPORTS,
            evidence_sources=["static/treesitter"],
        )
        graph.add_edge(edge)

    return graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_file_treesitter(
    path: Path, language: str = "auto"
) -> ProgramGraph | None:
    """Parse ``path`` through tree-sitter and return a :class:`ProgramGraph`.

    Args:
        path: File to parse. Must exist.
        language: Canonical language name or ``"auto"`` to infer from
            the file extension. Accepted values: ``"auto"``, ``"python"``,
            ``"javascript"``, ``"typescript"``.

    Returns:
        A populated :class:`ProgramGraph`, or ``None`` if the language
        cannot be determined or no parser is available for it. For
        ``.py`` files with tree-sitter unavailable, silently falls back
        to the stdlib-``ast`` parser and still returns a ProgramGraph.
    """
    if not isinstance(path, Path):
        path = Path(path)

    lang = language
    if lang == "auto":
        lang = _detect_language(path) or ""
    if not lang:
        return None

    if lang == "python":
        return parse_python_file(path)
    if lang == "javascript":
        return parse_js_file(path)
    if lang == "typescript":
        return parse_ts_file(path)

    logger.debug("treesitter_parser: unsupported language %r", lang)
    return None


def parse_python_file(path: Path) -> ProgramGraph | None:
    """Parse a Python file via tree-sitter (falls back to ast)."""
    if not HAS_TREESITTER:
        return _python_ast_fallback(path)

    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    if "python" not in parser.available_languages():
        return _python_ast_fallback(path)

    parsed = parser.parse_file(path)
    if parsed is None:
        return _python_ast_fallback(path)
    return _emit_parsed_file(path, "python", parsed)


def parse_js_file(path: Path) -> ProgramGraph | None:
    """Extract nodes/edges from a JavaScript file.

    Maps:
      * function declarations → :attr:`NodeKind.FUNCTION`
      * method definitions    → :attr:`NodeKind.METHOD`
      * class declarations    → :attr:`NodeKind.CLASS`
      * import statements     → synthetic module + :attr:`EdgeKind.IMPORTS`
    """
    if not HAS_TREESITTER:
        logger.debug("tree-sitter not available; cannot parse JS: %s", path)
        return None

    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    if "javascript" not in parser.available_languages():
        logger.debug("tree-sitter-javascript grammar not loaded: %s", path)
        return None

    parsed = parser.parse_file(path)
    if parsed is None:
        return None
    return _emit_parsed_file(path, "javascript", parsed)


def parse_ts_file(path: Path) -> ProgramGraph | None:
    """Extract nodes/edges from a TypeScript file.

    Uses the TypeScript/TSX grammar when available. The JavaScript
    extractor is language-agnostic enough that interfaces, classes,
    and methods all round-trip; TS-specific metadata (the ``tsx``
    grammar variant) is preserved on the file-level node.
    """
    if not HAS_TREESITTER:
        logger.debug("tree-sitter not available; cannot parse TS: %s", path)
        return None

    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    # Pick the right TS grammar based on suffix
    suffix = path.suffix.lower()
    preferred = "tsx" if suffix == ".tsx" else "typescript"
    if preferred not in parser.available_languages():
        # Fall through to javascript grammar if TS isn't installed
        if "javascript" not in parser.available_languages():
            return None
        parsed = parser.parse_file(path)
    else:
        # Force the TS grammar even though the default extension map
        # already routes .ts/.tsx there.
        parsed = parser.parse_file(path)

    if parsed is None:
        return None
    return _emit_parsed_file(path, "typescript", parsed)


# ---------------------------------------------------------------------------
# Fallback: stdlib ast for Python
# ---------------------------------------------------------------------------


def _python_ast_fallback(path: Path) -> ProgramGraph | None:
    """Route a ``.py`` file through the stdlib-ast parser and adapt.

    This lets :func:`parse_file_treesitter` behave uniformly even when
    the ``multilang`` extras (``tree-sitter``) aren't installed.
    """
    try:
        from cogant.static.parser import PythonASTParser
    except ImportError:
        return None

    py_parser = PythonASTParser()
    module = py_parser.parse_file(path)
    if module.errors:
        logger.debug("python ast fallback errors for %s: %s", path, module.errors)

    graph = _graph_for_file(path, "python")
    file_id = f"file::{path}"

    for func in module.functions:
        node_id = f"python::{path}::{func.name}::{func.line_start}"
        node = Node(
            id=node_id,
            kind=NodeKind.FUNCTION,
            name=func.name,
            qualified_name=func.name,
            path=str(path),
            language="python",
            source_range={
                "start_line": func.line_start,
                "end_line": func.line_end,
            },
            metadata={"is_async": func.is_async},
        )
        graph.add_node(node)
        graph.add_edge(
            Edge(
                id=f"{file_id}->{node_id}::contains",
                source_id=file_id,
                target_id=node_id,
                kind=EdgeKind.CONTAINS,
                evidence_sources=["static/ast"],
            )
        )

    for cls in module.classes:
        node_id = f"python::{path}::{cls.name}::{cls.line_start}"
        node = Node(
            id=node_id,
            kind=NodeKind.CLASS,
            name=cls.name,
            qualified_name=cls.name,
            path=str(path),
            language="python",
            source_range={
                "start_line": cls.line_start,
                "end_line": cls.line_end,
            },
            metadata={"bases": cls.bases},
        )
        graph.add_node(node)
        graph.add_edge(
            Edge(
                id=f"{file_id}->{node_id}::contains",
                source_id=file_id,
                target_id=node_id,
                kind=EdgeKind.CONTAINS,
                evidence_sources=["static/ast"],
            )
        )

    for idx, imp in enumerate(module.imports):
        mod_id = f"import::{path}::{idx}"
        mod_node = Node(
            id=mod_id,
            kind=NodeKind.MODULE,
            name=imp.module_name or "<relative>",
            qualified_name=imp.module_name or "<relative>",
            path=str(path),
            language="python",
            source_range={"start_line": imp.line_num},
            metadata={
                "is_relative": imp.is_relative,
                "names": imp.names,
            },
        )
        graph.add_node(mod_node)
        graph.add_edge(
            Edge(
                id=f"{file_id}->{mod_id}::imports",
                source_id=file_id,
                target_id=mod_id,
                kind=EdgeKind.IMPORTS,
                evidence_sources=["static/ast"],
            )
        )

    return graph


__all__ = [
    "HAS_TREESITTER",
    "parse_file_treesitter",
    "parse_python_file",
    "parse_js_file",
    "parse_ts_file",
]
