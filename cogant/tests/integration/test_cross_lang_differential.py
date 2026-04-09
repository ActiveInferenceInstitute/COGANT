"""Cross-language differential tests for the COGANT translation pipeline.

These tests verify that semantically equivalent Python and JavaScript
source files produce *comparable* program graphs and translation
mappings. The point isn't byte-for-byte equality — it's that the
translation engine converges on the same abstract roles for the same
behavioural patterns, regardless of source language.

We compare two fixtures:

* ``examples/control_positive/calculator/calculator.py`` — reference
  Python calculator with a state machine.
* ``examples/calculator_js/calculator.js`` — hand-ported JavaScript
  twin with identical class/method names and semantics.

Three differential invariants are checked:

1. **Name overlap** — at least 60% of the normalised method / variable
   names must be shared between the two graphs. This certifies that
   the two parsers surface the same symbols.
2. **Role coverage** — both graphs must each produce ≥1
   ``HIDDEN_STATE``, ``OBSERVATION``, and ``ACTION`` mapping. This
   certifies that the translation rules fire on both languages.
3. **Pattern stability** — a pure getter ``get_x(self): return self.x``
   must be classified as ``OBSERVATION`` in both languages. This
   certifies that the rules are pattern-driven, not language-specific.

Tests use *real* class instantiation: no mocks, no dicts. The graph
builder, JS parser, and translation engine are all invoked directly.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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

pytestmark = pytest.mark.integration

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

# Paths to the Python + JS calculator fixtures we compare.
_PY_CALCULATOR = (
    _REPO_ROOT / "examples" / "control_positive" / "calculator" / "calculator.py"
)
_JS_CALCULATOR = _REPO_ROOT / "examples" / "calculator_js" / "calculator.js"


# ---------------------------------------------------------------------------
# Helpers: normalized name overlap
# ---------------------------------------------------------------------------


def _normalize_name(name: str) -> str:
    """Lowercase and strip non-alphanumerics so ``get_x`` and ``getX`` match."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _name_overlap_score(a: Set[str], b: Set[str]) -> float:
    """Return ``|a ∩ b| / max(|a|, |b|)`` — 1.0 means perfect overlap."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = a & b
    denom = max(len(a), len(b))
    return len(intersection) / denom


def _symbol_name_set(graph: ProgramGraph) -> Set[str]:
    """Collect normalised method/function/variable/class names from a graph."""
    wanted_kinds = {
        NodeKind.METHOD,
        NodeKind.FUNCTION,
        NodeKind.VARIABLE,
        NodeKind.CLASS,
    }
    names: Set[str] = set()
    for node in graph.nodes.values():
        if node.kind not in wanted_kinds:
            continue
        # Prefer the leaf name — qualified names include the class prefix
        # which would otherwise inflate the denominator for equivalent
        # methods that live under the same class name.
        leaf = node.name
        names.add(_normalize_name(leaf))
    names.discard("")
    return names


# ---------------------------------------------------------------------------
# Helpers: translation runner shared by both languages
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
# Helpers: build a graph from a Python source file via the stdlib AST
# ---------------------------------------------------------------------------


def _build_python_graph(source_path: Path) -> ProgramGraph:
    """Walk a Python source file with stdlib ``ast`` and build a rich graph.

    The walker emits ``MODULE → CLASS → METHOD`` containment, plus
    ``WRITES`` / ``READS`` edges whenever a method touches a
    ``self.attr`` name. That's the minimum amount of dataflow needed
    for the structural rules (``MutatingSubsystemRule``,
    ``ReadOnlyInputRule``) to fire in the same way they would on the
    corresponding JavaScript graph.
    """
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

    # First pass: create class, method, and per-attribute variable nodes.
    # Dataflow is emitted both (a) from method to the enclosing class
    # (matching the reference ``_add_dataflow_edges`` helper in
    # ``examples/thin_orchestrated/_common.py``, which is what the
    # ``MutatingSubsystemRule`` scans for), and (b) from method to the
    # per-attribute variable node (so fine-grained rules see the dataflow
    # chain as well).
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

            # Scan for self.attr references.
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
                    builder.add_edge(
                        class_node.id, attr_node.id, EdgeKind.CONTAINS
                    )
                # Write vs read classification: an ast.Store context on
                # the Attribute means the method assigns to self.attr.
                if isinstance(sub.ctx, ast.Store):
                    edge_kind = EdgeKind.WRITES
                    method_writes += 1
                else:
                    edge_kind = EdgeKind.READS
                    method_reads += 1
                builder.add_edge(method_node.id, attr_nodes[key].id, edge_kind)

            # Method→class dataflow summary edges (matches the reference
            # helper in _common.py and what MutatingSubsystemRule scans).
            if method_writes > 0:
                builder.add_edge(
                    method_node.id, class_node.id, EdgeKind.WRITES
                )
            if method_reads > method_writes:
                builder.add_edge(
                    method_node.id, class_node.id, EdgeKind.READS
                )

    # Top-level functions (unlikely for calculator, but keep the walker
    # general-purpose so it can be reused by other cross-lang fixtures).
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
# Helpers: build a graph from a JavaScript source file via tree-sitter
# ---------------------------------------------------------------------------


# Matches ``this.attr`` followed by ``=`` (write) or anything else (read).
# Captures the attribute name so the builder can look up the matching
# variable node.
_THIS_WRITE_RE = re.compile(r"\bthis\.([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)")
_THIS_READ_RE = re.compile(r"\bthis\.([A-Za-z_][A-Za-z0-9_]*)")


def _build_javascript_graph(source_path: Path) -> ProgramGraph:
    """Parse a JavaScript source file with the JS plugin and build a graph.

    The JS plugin returns a flat symbol list where method qualified
    names look like ``Calculator.input_digit``. We rebuild the
    ``MODULE → CLASS → METHOD`` containment from those names and then
    scan each method body (using ``line_start`` / ``line_end``) for
    ``this.attr`` reads and writes so the structural rules see the
    same kind of dataflow they get from the Python walker.
    """
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

    kind_map = {
        "class": NodeKind.CLASS,
        "method": NodeKind.METHOD,
        "function": NodeKind.FUNCTION,
        "variable": NodeKind.VARIABLE,
    }

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

    # Second pass: methods nested under a known class.
    for sym in ast_dict["symbols"]:
        if sym.get("kind") != "method":
            continue
        qname = sym.get("qualified_name") or sym["name"]
        # JS plugin uses dotted qualified names like ``Calculator.foo``.
        if "." in qname:
            cls_name, method_name = qname.rsplit(".", 1)
        else:
            cls_name, method_name = ("", sym["name"])

        if cls_name and cls_name not in class_nodes:
            # Defensive: create a placeholder class so orphan methods
            # still appear in the graph.
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

        method_qname = f"{module_name}.{cls_name}.{method_name}" if cls_name else (
            f"{module_name}.{method_name}"
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

        # Scan body lines for this.attr references.
        line_start = int(sym.get("line_start") or 1)
        line_end = int(sym.get("line_end") or line_start)
        # line_* are 1-indexed; slice is 0-indexed / end-exclusive.
        body = "\n".join(source_lines[line_start - 1 : line_end])

        writes = {m.group(1) for m in _THIS_WRITE_RE.finditer(body)}
        all_refs = {m.group(1) for m in _THIS_READ_RE.finditer(body)}
        reads = all_refs - writes

        for attr in writes | reads:
            key = (cls_name, attr)
            if key not in attr_nodes:
                attr_qname = f"{module_name}.{cls_name}.{attr}" if cls_name else (
                    f"{module_name}.{attr}"
                )
                attr_node = builder.add_node(
                    kind=NodeKind.VARIABLE,
                    name=attr,
                    qualified_name=attr_qname,
                    path=str(source_path),
                    language="javascript",
                )
                attr_nodes[key] = attr_node
                builder.add_edge(
                    parent.id, attr_node.id, EdgeKind.CONTAINS
                )
        for attr in writes:
            builder.add_edge(
                method_node.id, attr_nodes[(cls_name, attr)].id, EdgeKind.WRITES
            )
        for attr in reads:
            builder.add_edge(
                method_node.id, attr_nodes[(cls_name, attr)].id, EdgeKind.READS
            )

        # Method→class dataflow summary edges. These mirror the helper
        # in examples/thin_orchestrated/_common.py and are what
        # ``MutatingSubsystemRule`` scans to promote a class to
        # HIDDEN_STATE.
        if cls_name and cls_name in class_nodes:
            parent_class = class_nodes[cls_name]
            if writes:
                builder.add_edge(
                    method_node.id, parent_class.id, EdgeKind.WRITES
                )
            if len(reads) > len(writes):
                builder.add_edge(
                    method_node.id, parent_class.id, EdgeKind.READS
                )

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _HAS_JS_PARSER, reason="tree-sitter-javascript not installed"
)
def test_calculator_py_js_node_overlap() -> None:
    """≥60% normalised name overlap between the Python and JS calculators."""
    py_graph = _build_python_graph(_PY_CALCULATOR)
    js_graph = _build_javascript_graph(_JS_CALCULATOR)

    py_names = _symbol_name_set(py_graph)
    js_names = _symbol_name_set(js_graph)

    assert py_names, "python graph produced no comparable symbols"
    assert js_names, "javascript graph produced no comparable symbols"

    score = _name_overlap_score(py_names, js_names)
    assert score >= 0.6, (
        f"name overlap {score:.2%} < 60% — "
        f"py_only={sorted(py_names - js_names)}, "
        f"js_only={sorted(js_names - py_names)}"
    )


@pytest.mark.skipif(
    not _HAS_JS_PARSER, reason="tree-sitter-javascript not installed"
)
def test_calculator_role_distribution_similar() -> None:
    """Both languages must produce ≥1 HIDDEN_STATE, OBSERVATION, ACTION."""
    py_graph = _build_python_graph(_PY_CALCULATOR)
    js_graph = _build_javascript_graph(_JS_CALCULATOR)

    py_counts = _role_counts(_run_translation(py_graph))
    js_counts = _role_counts(_run_translation(js_graph))

    required_roles = (
        MappingKind.HIDDEN_STATE,
        MappingKind.OBSERVATION,
        MappingKind.ACTION,
    )
    for role in required_roles:
        assert py_counts.get(role, 0) >= 1, (
            f"python calculator missing {role.value} mappings; "
            f"got {dict((k.value, v) for k, v in py_counts.items())}"
        )
        assert js_counts.get(role, 0) >= 1, (
            f"js calculator missing {role.value} mappings; "
            f"got {dict((k.value, v) for k, v in js_counts.items())}"
        )


@pytest.mark.skipif(
    not _HAS_JS_PARSER, reason="tree-sitter-javascript not installed"
)
def test_same_pattern_same_dominant_role(tmp_path: Path) -> None:
    """A pure getter ``get_x() -> self.x`` must be OBSERVATION in both langs.

    The test builds a throwaway one-class module in each language with
    nothing but a single ``get_value`` method reading a private field
    and asserts both translation passes produce an ``OBSERVATION``
    mapping that covers the method node.
    """
    py_src = tmp_path / "only_getter.py"
    py_src.write_text(
        "class OnlyGetter:\n"
        "    def __init__(self):\n"
        "        self.value = 0\n"
        "    def get_value(self):\n"
        "        return self.value\n",
        encoding="utf-8",
    )

    js_src_dir = tmp_path / "js_only_getter"
    js_src_dir.mkdir()
    js_src = js_src_dir / "only_getter.js"
    js_src.write_text(
        "class OnlyGetter {\n"
        "  constructor() {\n"
        "    this.value = 0;\n"
        "  }\n"
        "  get_value() {\n"
        "    return this.value;\n"
        "  }\n"
        "}\n"
        "module.exports = { OnlyGetter };\n",
        encoding="utf-8",
    )

    py_graph = _build_python_graph(py_src)
    js_graph = _build_javascript_graph(js_src)

    py_mappings = _run_translation(py_graph)
    js_mappings = _run_translation(js_graph)

    def _observation_method_names(
        graph: ProgramGraph, mappings: List[SemanticMapping]
    ) -> Set[str]:
        observation_node_ids = {
            nid
            for m in mappings
            if m.kind == MappingKind.OBSERVATION
            for nid in m.graph_fragment_node_ids
        }
        return {
            graph.nodes[nid].name
            for nid in observation_node_ids
            if nid in graph.nodes
            and graph.nodes[nid].kind in (NodeKind.METHOD, NodeKind.FUNCTION)
        }

    py_observation_methods = _observation_method_names(py_graph, py_mappings)
    js_observation_methods = _observation_method_names(js_graph, js_mappings)

    assert "get_value" in py_observation_methods, (
        f"python get_value not classified as OBSERVATION; "
        f"observed methods: {sorted(py_observation_methods)}"
    )
    assert "get_value" in js_observation_methods, (
        f"javascript get_value not classified as OBSERVATION; "
        f"observed methods: {sorted(js_observation_methods)}"
    )
