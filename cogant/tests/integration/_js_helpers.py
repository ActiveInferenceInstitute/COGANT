"""Shared helpers for cross-language (JavaScript) integration tests.

Both ``test_cross_lang_differential.py`` and ``test_cross_lang_roundtrip.py``
import from here.  Keeping shared code in a single module eliminates the
dual-import problem that arises when a test file imports from another test
file via a sys.path hack — pytest collects both under the package name
``tests.integration.*`` while the sys.path trick imports the same file again
as a bare module name, producing two independent module objects with
divergent global state.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import (
    ActionRule,
    ContainmentRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ObservationRule,
    PolicyRule,
    PreferenceRule,
    ReadOnlyInputRule,
)

# ---------------------------------------------------------------------------
# sys.path bootstrapping for the tree-sitter-backed JS parser plugin
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PARSERS_ROOT = _REPO_ROOT / "parsers"
if str(_PARSERS_ROOT) not in sys.path:
    sys.path.insert(0, str(_PARSERS_ROOT))

try:
    from javascript.parser import JavaScriptLanguageParser  # type: ignore  # noqa: E402

    _HAS_JS_PARSER = True
except ImportError:  # pragma: no cover
    _HAS_JS_PARSER = False

# ---------------------------------------------------------------------------
# Translation runner
# ---------------------------------------------------------------------------


def _run_translation(graph: ProgramGraph) -> List[SemanticMapping]:
    """Translate ``graph`` with the shipping structural + semantic rule set."""
    engine = TranslationEngine()
    engine.register_rule(ReadOnlyInputRule())
    engine.register_rule(MutatingSubsystemRule())
    engine.register_rule(ObservationRule())
    engine.register_rule(ActionRule())
    engine.register_rule(PolicyRule())
    engine.register_rule(PreferenceRule())
    engine.register_rule(InheritanceRule())
    engine.register_rule(ContainmentRule())
    return engine.translate(graph)


def _role_counts(mappings: List[SemanticMapping]) -> Dict[MappingKind, int]:
    """Return a histogram of ``MappingKind`` → count."""
    counts: Dict[MappingKind, int] = {}
    for m in mappings:
        counts[m.kind] = counts.get(m.kind, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Python graph builder (stdlib ast)
# ---------------------------------------------------------------------------


def _build_python_graph(source_path: Path) -> ProgramGraph:
    """Walk a Python source file with stdlib ``ast`` and build a rich graph."""
    import ast

    builder = ProgramGraphBuilder(repo_uri=f"file://{source_path}")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    module_name = source_path.stem
    module_node = builder.add_node(
        kind=NodeKind.MODULE,
        name=module_name,
        qualified_name=module_name,
        path=str(source_path),
        language="python",
    )

    class_nodes: Dict[str, Node] = {}
    method_nodes: Dict[Tuple[str, str], Node] = {}
    attr_nodes: Dict[Tuple[str, str], Node] = {}

    for stmt in tree.body:
        if not isinstance(stmt, ast.ClassDef):
            continue
        class_qname = f"{module_name}.{stmt.name}"
        class_node = builder.add_node(
            kind=NodeKind.CLASS,
            name=stmt.name,
            qualified_name=class_qname,
            path=str(source_path),
            language="python",
        )
        class_nodes[stmt.name] = class_node
        builder.add_edge(module_node.id, class_node.id, EdgeKind.CONTAINS)

        for item in stmt.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            method_qname = f"{class_qname}.{item.name}"
            method_node = builder.add_node(
                kind=NodeKind.METHOD,
                name=item.name,
                qualified_name=method_qname,
                path=str(source_path),
                language="python",
            )
            method_nodes[(stmt.name, item.name)] = method_node
            builder.add_edge(class_node.id, method_node.id, EdgeKind.CONTAINS)

            method_writes = 0
            method_reads = 0
            for sub in ast.walk(item):
                if not isinstance(sub, ast.Attribute):
                    continue
                if not isinstance(sub.value, ast.Name) or sub.value.id != "self":
                    continue
                attr = sub.attr
                key = (stmt.name, attr)
                if key not in attr_nodes:
                    attr_qname = f"{class_qname}.{attr}"
                    attr_node = builder.add_node(
                        kind=NodeKind.VARIABLE,
                        name=attr,
                        qualified_name=attr_qname,
                        path=str(source_path),
                        language="python",
                    )
                    attr_nodes[key] = attr_node
                    builder.add_edge(class_node.id, attr_node.id, EdgeKind.CONTAINS)
                if isinstance(sub.ctx, ast.Store):
                    edge_kind = EdgeKind.WRITES
                    method_writes += 1
                else:
                    edge_kind = EdgeKind.READS
                    method_reads += 1
                builder.add_edge(method_node.id, attr_nodes[key].id, edge_kind)

            if method_writes > 0:
                builder.add_edge(method_node.id, class_node.id, EdgeKind.WRITES)
            if method_reads > method_writes:
                builder.add_edge(method_node.id, class_node.id, EdgeKind.READS)

    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_qname = f"{module_name}.{stmt.name}"
            func_node = builder.add_node(
                kind=NodeKind.FUNCTION,
                name=stmt.name,
                qualified_name=func_qname,
                path=str(source_path),
                language="python",
            )
            builder.add_edge(module_node.id, func_node.id, EdgeKind.CONTAINS)

    return builder.finalize()


# ---------------------------------------------------------------------------
# JavaScript graph builder (tree-sitter via JS parser plugin)
# ---------------------------------------------------------------------------

_THIS_WRITE_RE = re.compile(r"\bthis\.([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)")
_THIS_READ_RE = re.compile(r"\bthis\.([A-Za-z_][A-Za-z0-9_]*)")


def _build_javascript_graph(source_path: Path) -> ProgramGraph:
    """Parse a JavaScript source file with the JS plugin and build a graph."""
    parser = JavaScriptLanguageParser()
    source = source_path.read_text(encoding="utf-8")
    ast_dict = parser.parse(source, str(source_path))
    if ast_dict.get("error"):
        pytest.skip(ast_dict["error"])

    source_lines = source.splitlines()
    builder = ProgramGraphBuilder(repo_uri=f"file://{source_path}")
    module_name = source_path.stem
    module_node = builder.add_node(
        kind=NodeKind.MODULE,
        name=module_name,
        qualified_name=module_name,
        path=str(source_path),
        language="javascript",
    )

    class_nodes: Dict[str, Node] = {}
    method_nodes: Dict[Tuple[str, str], Node] = {}
    attr_nodes: Dict[Tuple[str, str], Node] = {}

    # First pass: classes.
    for sym in ast_dict["symbols"]:
        if sym.get("kind") != "class":
            continue
        cls_name = sym["name"]
        cls_qname = f"{module_name}.{cls_name}"
        cls_node = builder.add_node(
            kind=NodeKind.CLASS,
            name=cls_name,
            qualified_name=cls_qname,
            path=str(source_path),
            language="javascript",
        )
        class_nodes[cls_name] = cls_node
        builder.add_edge(module_node.id, cls_node.id, EdgeKind.CONTAINS)

    # Second pass: methods.
    for sym in ast_dict["symbols"]:
        if sym.get("kind") != "method":
            continue
        qname = sym.get("qualified_name") or sym["name"]
        if "." in qname:
            cls_name, method_name = qname.rsplit(".", 1)
        else:
            cls_name, method_name = ("", sym["name"])

        if cls_name and cls_name not in class_nodes:
            placeholder_qname = f"{module_name}.{cls_name}"
            cls_node = builder.add_node(
                kind=NodeKind.CLASS,
                name=cls_name,
                qualified_name=placeholder_qname,
                path=str(source_path),
                language="javascript",
            )
            class_nodes[cls_name] = cls_node
            builder.add_edge(module_node.id, cls_node.id, EdgeKind.CONTAINS)

        method_qname = (
            f"{module_name}.{cls_name}.{method_name}"
            if cls_name
            else f"{module_name}.{method_name}"
        )
        method_node = builder.add_node(
            kind=NodeKind.METHOD,
            name=method_name,
            qualified_name=method_qname,
            path=str(source_path),
            language="javascript",
        )
        method_nodes[(cls_name, method_name)] = method_node
        parent = class_nodes.get(cls_name, module_node)
        builder.add_edge(parent.id, method_node.id, EdgeKind.CONTAINS)

        line_start = int(sym.get("line_start") or 1)
        line_end = int(sym.get("line_end") or line_start)
        body = "\n".join(source_lines[line_start - 1 : line_end])

        writes = {m.group(1) for m in _THIS_WRITE_RE.finditer(body)}
        all_refs = {m.group(1) for m in _THIS_READ_RE.finditer(body)}
        reads = all_refs - writes

        for attr in writes | reads:
            key = (cls_name, attr)
            if key not in attr_nodes:
                attr_qname = (
                    f"{module_name}.{cls_name}.{attr}"
                    if cls_name
                    else f"{module_name}.{attr}"
                )
                attr_node = builder.add_node(
                    kind=NodeKind.VARIABLE,
                    name=attr,
                    qualified_name=attr_qname,
                    path=str(source_path),
                    language="javascript",
                )
                attr_nodes[key] = attr_node
                builder.add_edge(parent.id, attr_node.id, EdgeKind.CONTAINS)
        for attr in writes:
            builder.add_edge(
                method_node.id, attr_nodes[(cls_name, attr)].id, EdgeKind.WRITES
            )
        for attr in reads:
            builder.add_edge(
                method_node.id, attr_nodes[(cls_name, attr)].id, EdgeKind.READS
            )

        if cls_name and cls_name in class_nodes:
            parent_class = class_nodes[cls_name]
            if writes:
                builder.add_edge(method_node.id, parent_class.id, EdgeKind.WRITES)
            if len(reads) > len(writes):
                builder.add_edge(method_node.id, parent_class.id, EdgeKind.READS)

    # Top-level functions.
    for sym in ast_dict["symbols"]:
        if sym.get("kind") != "function":
            continue
        func_name = sym["name"]
        func_qname = f"{module_name}.{func_name}"
        func_node = builder.add_node(
            kind=NodeKind.FUNCTION,
            name=func_name,
            qualified_name=func_qname,
            path=str(source_path),
            language="javascript",
        )
        builder.add_edge(module_node.id, func_node.id, EdgeKind.CONTAINS)

    return builder.finalize()
