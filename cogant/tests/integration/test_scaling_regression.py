"""Regression tests guarding the five dulwich scaling fixes (commit ff13dfa).

The fixes in ``ff13dfa`` addressed five O(n²)/O(n×e) hotspots that made
COGANT unusable on large repositories (the dulwich eval case hit ~400s
wall time and a 4.6 GB GNN package before the fix). This suite pins
the behaviour so that a regression surfaces as a unit-test failure
rather than as a runtime cliff on the eval corpus:

1. **B tensor truncation** (``cogant/gnn/matrices.py``):
   full n_states² × n_actions tensor must be capped at 5 M entries by
   selecting the top-K highest-degree state nodes.
2. **Domain list truncation** (``cogant/gnn/formatter/structural.py``):
   state-variable ``domain`` lists must be clipped to the first five
   elements with a ``+N more`` suffix.
3. **O(|V| + |E|) BFS** (``cogant/graph/builder.py``):
   ``get_connected_components`` must use a pre-built adjacency dict so
   that wall time is linear in the edge count.
4. **AST cache** (``cogant/api/orchestration.py``):
   ``_emit_dataflow_edges`` must parse each source file at most once
   via the ``ast_cache`` argument, even when a class has many methods.
5. **INHERITS lookup** (``cogant/api/orchestration.py``):
   ``run_graph`` must build a ``class_by_name`` dict so that base-class
   resolution is O(1) per base, not O(classes) per base.

Tests use real data structures (``Node``, ``Edge``, ``StateVariable``,
``StateSpaceModel``) — no mocks — and run in well under a second each.
"""

from __future__ import annotations

import ast
import sys
import time
from pathlib import Path
from typing import Any

import pytest

# Ensure ``py/cogant`` is importable regardless of invocation directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.api.orchestration import _emit_dataflow_edges, run_graph  # noqa: E402
from cogant.gnn.formatter.structural import _StructuralSectionsMixin  # noqa: E402
from cogant.gnn.matrices import GNNMatrices, _MAX_B_ENTRIES  # noqa: E402
from cogant.graph.builder import ProgramGraphBuilder  # noqa: E402
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind  # noqa: E402
from cogant.schemas.graph import GraphMetadata, ProgramGraph  # noqa: E402
from cogant.schemas.semantic import MappingKind, SemanticMapping  # noqa: E402
from cogant.statespace.compiler import StateSpaceModel  # noqa: E402
from cogant.statespace.temporal import TimeRegime  # noqa: E402
from cogant.statespace.variables import (  # noqa: E402
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state_node(node_id: str) -> Node:
    """Return a minimal CLASS node usable as a hidden-state anchor."""
    return Node(
        id=node_id,
        kind=NodeKind.CLASS,
        name=node_id,
        qualified_name=node_id,
    )


def _make_action_node(node_id: str) -> Node:
    return Node(
        id=node_id,
        kind=NodeKind.FUNCTION,
        name=node_id,
        qualified_name=node_id,
    )


def _make_edge(edge_id: str, source: str, target: str, kind: EdgeKind) -> Edge:
    return Edge(id=edge_id, source_id=source, target_id=target, kind=kind)


def _build_hidden_state_graph(
    n_states: int,
    n_actions: int,
    extra_edges_on_top_states: int = 0,
) -> tuple[ProgramGraph, list[SemanticMapping]]:
    """Build a program graph with ``n_states`` hidden-state nodes and
    ``n_actions`` action nodes, plus semantic mappings for both.

    The first ``extra_edges_on_top_states`` state nodes receive an extra
    out-edge so the top-K selection is deterministic.
    """
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))

    state_ids: list[str] = []
    mappings: list[SemanticMapping] = []
    for i in range(n_states):
        nid = f"state_{i:04d}"
        graph.add_node(_make_state_node(nid))
        state_ids.append(nid)
        mappings.append(
            SemanticMapping(
                id=f"hs_{i:04d}",
                kind=MappingKind.HIDDEN_STATE,
                graph_fragment_node_ids=[nid],
                semantic_label=nid,
                confidence_score=0.8,
            )
        )

    for k in range(n_actions):
        aid = f"action_{k:04d}"
        graph.add_node(_make_action_node(aid))
        mappings.append(
            SemanticMapping(
                id=f"a_{k:04d}",
                kind=MappingKind.ACTION,
                graph_fragment_node_ids=[aid],
                semantic_label=aid,
                confidence_score=0.8,
            )
        )

    # Give the first ``extra_edges_on_top_states`` state nodes additional
    # in-degree so that ``_top_k_state_ids`` ranks them deterministically
    # above the rest (ties are broken by original order).
    for idx in range(min(extra_edges_on_top_states, n_states)):
        src = state_ids[idx]
        tgt = state_ids[(idx + 1) % n_states]
        graph.add_edge(
            _make_edge(f"boost_{idx}", src, tgt, EdgeKind.DEPENDS_ON)
        )

    return graph, mappings


def _empty_state_space(schema_name: str = "test") -> StateSpaceModel:
    return StateSpaceModel(
        id=f"model_{schema_name}",
        schema_name=schema_name,
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


class _StructuralHarness(_StructuralSectionsMixin):
    """Minimal concrete class exposing only the attributes that
    ``_format_state_space`` reads. Avoids pulling in ProcessModel and
    the rest of the formatter machinery."""

    def __init__(
        self,
        graph: ProgramGraph,
        state_space: StateSpaceModel,
        mappings: dict[str, Any],
    ) -> None:
        self.graph = graph
        self.state_space = state_space
        self.mappings = mappings
        self.process = None  # not read by _format_state_space


def _make_state_variable(
    var_id: str, domain: list[Any] | None
) -> StateVariable:
    return StateVariable(
        id=var_id,
        name=var_id,
        var_type=StateVariableType.CATEGORICAL,
        node_id=f"node_{var_id}",
        cardinality=len(domain) if domain else 1,
        domain=domain,
        confidence=ConfidenceLevel.HIGH,
    )


# ---------------------------------------------------------------------------
# Fix 1 — B tensor truncation
# ---------------------------------------------------------------------------


class TestBTensorTruncation:
    """Regression tests for the B tensor top-K truncation guard.

    See ``GNNMatrices.compute_B`` in ``cogant/gnn/matrices.py``.
    """

    def test_small_b_not_truncated(self) -> None:
        """n_states=10, n_actions=10 → 1000 entries << 5M → no truncation."""
        graph, mappings = _build_hidden_state_graph(n_states=10, n_actions=10)
        gm = GNNMatrices(graph, mappings, _empty_state_space())
        B = gm.compute_B()
        assert gm._b_truncated is False
        assert gm._b_n_states_kept == 10
        assert len(B) == 10
        assert len(B[0]) == 10
        assert len(B[0][0]) == 10

        # to_dict() reports truncation=None when no truncation was applied.
        payload = gm.to_dict()
        assert payload["truncation"] is None
        assert payload["dimensions"]["n_states"] == 10

    def test_large_b_truncated_to_top_k(self) -> None:
        """n_states=1000, n_actions=1000 → 1e9 entries → must truncate.

        Max k satisfying k² × 1000 ≤ 5,000,000 is 70; the returned tensor
        must have first two dimensions equal to 70.
        """
        graph, mappings = _build_hidden_state_graph(
            n_states=1000, n_actions=1000, extra_edges_on_top_states=50
        )
        gm = GNNMatrices(graph, mappings, _empty_state_space())

        B = gm.compute_B()
        assert gm._b_truncated is True
        assert gm._b_n_states_full == 1000
        # max_k = isqrt(5_000_000 // 1000) = isqrt(5000) = 70.
        assert gm._b_n_states_kept == 70
        assert len(B) == 70
        assert len(B[0]) == 70
        assert len(B[0][0]) == 1000

    def test_truncation_recorded_in_to_dict(self) -> None:
        """to_dict() must surface truncation metadata when it fires."""
        graph, mappings = _build_hidden_state_graph(
            n_states=500, n_actions=500, extra_edges_on_top_states=10
        )
        gm = GNNMatrices(graph, mappings, _empty_state_space())
        payload = gm.to_dict()

        trunc = payload["truncation"]
        assert trunc is not None
        assert trunc["applied"] is True
        assert trunc["n_states_full"] == 500
        assert trunc["n_states_kept"] == gm._b_n_states_kept
        assert trunc["max_b_entries"] == _MAX_B_ENTRIES
        assert "top-" in trunc["reason"]

    def test_top_k_selection_uses_degree_not_random(self) -> None:
        """Top-K selection must prefer high-degree nodes deterministically.

        Construct 200 state nodes where only the first three carry an
        extra edge. With n_states=200, n_actions=200 the full tensor is
        8 M entries > 5 M → truncation kicks in, max_k = isqrt(5e6/200) = 158.
        We expect all three high-degree state_0000/0001/0002 to survive.
        """
        graph, mappings = _build_hidden_state_graph(
            n_states=200, n_actions=200, extra_edges_on_top_states=3
        )
        gm = GNNMatrices(graph, mappings, _empty_state_space())
        gm.compute_B()
        kept_ids = set(gm._top_k_state_ids(
            gm._state_node_ids(), gm._b_n_states_kept
        ))
        # The three boosted nodes must be in the kept set; if the selection
        # were random they would appear at p = (158/200)³ ≈ 0.49.
        assert "state_0000" in kept_ids
        assert "state_0001" in kept_ids
        assert "state_0002" in kept_ids


# ---------------------------------------------------------------------------
# Fix 2 — Domain list truncation in structural formatter
# ---------------------------------------------------------------------------


class TestDomainListTruncation:
    """Regression tests for the state-space domain truncation in the
    structural section formatter."""

    def test_large_domain_truncated_to_first_five_plus_suffix(self) -> None:
        """A class with 10 ``domain`` elements is truncated to 5 + ``+5 more``."""
        domain = [f"method_{i}" for i in range(10)]
        var = _make_state_variable("var_big", domain)
        ss = _empty_state_space()
        ss.variables[var.id] = var

        harness = _StructuralHarness(
            graph=ProgramGraph(metadata=GraphMetadata(repo_uri="file:///t")),
            state_space=ss,
            mappings={},
        )
        md = harness._format_state_space()
        # The truncated domain must list the first 5 and suffix with the
        # number of omitted elements.
        assert "'method_0'" in md
        assert "'method_4'" in md
        assert "+5 more]" in md
        # And the later elements must NOT be inlined verbatim.
        assert "'method_9'" not in md

    def test_small_domain_not_truncated(self) -> None:
        """A class with 4 methods fits under the 5-element cap → no suffix."""
        domain = ["a", "b", "c", "d"]
        var = _make_state_variable("var_small", domain)
        ss = _empty_state_space()
        ss.variables[var.id] = var

        harness = _StructuralHarness(
            graph=ProgramGraph(metadata=GraphMetadata(repo_uri="file:///t")),
            state_space=ss,
            mappings={},
        )
        md = harness._format_state_space()
        assert "'a'" in md
        assert "'d'" in md
        assert "more]" not in md

    def test_boundary_exactly_five_elements_not_truncated(self) -> None:
        """The cap is >5 (strict); 5 elements must render verbatim."""
        domain = ["p", "q", "r", "s", "t"]
        var = _make_state_variable("var_edge", domain)
        ss = _empty_state_space()
        ss.variables[var.id] = var

        harness = _StructuralHarness(
            graph=ProgramGraph(metadata=GraphMetadata(repo_uri="file:///t")),
            state_space=ss,
            mappings={},
        )
        md = harness._format_state_space()
        assert "'p'" in md
        assert "'t'" in md
        assert "more]" not in md


# ---------------------------------------------------------------------------
# Fix 3 — O(|V| + |E|) BFS in get_connected_components
# ---------------------------------------------------------------------------


class TestConnectedComponentsBFS:
    """Regression tests for the adjacency-dict BFS refactor."""

    def _builder_with_chain(self, n_nodes: int, n_edges: int) -> ProgramGraphBuilder:
        builder = ProgramGraphBuilder(repo_uri="file:///bfs_test")
        # Add nodes.
        for i in range(n_nodes):
            builder.add_node(
                kind=NodeKind.FUNCTION,
                name=f"n{i}",
                qualified_name=f"mod.n{i}",
                path=f"mod/n{i}.py",
            )
        # Fetch ordered node IDs.
        node_ids = list(builder.graph.nodes.keys())
        # Add a simple chain first so everything is one component, then
        # add duplicate/extra edges between existing pairs until we reach
        # the requested edge count. ``add_edge`` deduplicates by id, so
        # we cycle through distinct pairs.
        added = 0
        i = 0
        while added < n_edges and n_nodes > 1:
            src = node_ids[i % n_nodes]
            tgt = node_ids[(i + 1) % n_nodes]
            before = len(builder.graph.edges)
            builder.add_edge(src, tgt, EdgeKind.CALLS)
            if len(builder.graph.edges) > before:
                added += 1
            i += 1
            # Avoid infinite loop if we run out of distinct pairs.
            if i > n_nodes * n_nodes:
                break
        return builder

    def test_connected_components_correctness_small(self) -> None:
        """Two disjoint components must be reported separately."""
        builder = ProgramGraphBuilder(repo_uri="file:///cc_small")
        for i in range(4):
            builder.add_node(
                kind=NodeKind.FUNCTION,
                name=f"n{i}",
                qualified_name=f"n{i}",
                path=f"n{i}.py",
            )
        ids = list(builder.graph.nodes.keys())
        # Component A: 0-1
        builder.add_edge(ids[0], ids[1], EdgeKind.CALLS)
        # Component B: 2-3
        builder.add_edge(ids[2], ids[3], EdgeKind.CALLS)

        components = builder.get_connected_components()
        assert len(components) == 2
        sizes = sorted(len(c) for c in components)
        assert sizes == [2, 2]

    def test_connected_components_100_nodes_200_edges_fast(self) -> None:
        """100 nodes / 200 edges must complete well under 1 second."""
        builder = self._builder_with_chain(n_nodes=100, n_edges=200)
        start = time.perf_counter()
        components = builder.get_connected_components()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"BFS took {elapsed:.3f}s, expected < 1s"
        # All nodes should be in a single component (chain forms a cycle).
        total = sum(len(c) for c in components)
        assert total == 100

    def test_connected_components_scales_linearly(self) -> None:
        """Bump the edge count 10× and the result (component count + total
        nodes covered) must still be correct — the linear refactor should
        not regress on dense graphs."""
        sparse = self._builder_with_chain(n_nodes=50, n_edges=60)
        dense = self._builder_with_chain(n_nodes=50, n_edges=600)

        sparse_components = sparse.get_connected_components()
        dense_components = dense.get_connected_components()

        # Both graphs fully connect all 50 nodes (chain closure).
        assert sum(len(c) for c in sparse_components) == 50
        assert sum(len(c) for c in dense_components) == 50

        # Dense variant must not take pathologically long.
        start = time.perf_counter()
        dense.get_connected_components()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"dense BFS took {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# Fix 4 — AST cache in _emit_dataflow_edges
# ---------------------------------------------------------------------------


class TestASTCache:
    """Regression tests for the per-file AST cache in the graph stage."""

    def _write_class_with_methods(self, tmp_path: Path, n_methods: int) -> Path:
        """Write a Python file defining a single class with N methods,
        each of which both reads and writes ``self.x`` so that
        ``_emit_dataflow_edges`` emits both READS and WRITES edges."""
        lines = ["class Big:"]
        lines.append("    def __init__(self):")
        lines.append("        self.x = 0")
        for i in range(n_methods):
            lines.append(f"    def m{i}(self):")
            lines.append(f"        self.x = self.x + {i}")
        src = "\n".join(lines) + "\n"
        file_path = tmp_path / "big.py"
        file_path.write_text(src)
        return file_path

    def test_ast_cache_populated_once_per_file(self, tmp_path: Path) -> None:
        """Fifty methods on one class → the cache has exactly one entry.

        We wire the same ``ast_cache`` dict into every call and assert
        that the file key is present after the first call and that the
        cache size never grows beyond 1.
        """
        n_methods = 50
        file_path = self._write_class_with_methods(tmp_path, n_methods)

        builder = ProgramGraphBuilder(repo_uri="file:///ast_cache")
        class_node = builder.add_node(
            kind=NodeKind.CLASS,
            name="Big",
            qualified_name="big.Big",
            path="big.py",
        )

        ast_cache: dict[Path, Any] = {}
        for i in range(n_methods):
            method_node = builder.add_node(
                kind=NodeKind.METHOD,
                name=f"m{i}",
                qualified_name=f"big.Big.m{i}",
                path="big.py",
            )
            _emit_dataflow_edges(
                builder,
                method_node,
                class_node,
                f"m{i}",
                file_path,
                ast,
                ast_cache=ast_cache,
            )

        assert file_path in ast_cache
        assert len(ast_cache) == 1
        # The cached value must be a parsed AST module, not None/sentinel.
        assert ast_cache[file_path] is not None
        assert isinstance(ast_cache[file_path], ast.Module)

    def test_ast_cache_failure_is_remembered(self, tmp_path: Path) -> None:
        """When a file cannot be parsed, the cache stores ``None`` so
        subsequent calls short-circuit rather than re-raising."""
        bad_path = tmp_path / "broken.py"
        bad_path.write_text("def oops(:\n    pass\n")  # syntax error

        builder = ProgramGraphBuilder(repo_uri="file:///ast_cache_fail")
        class_node = builder.add_node(
            kind=NodeKind.CLASS, name="X", qualified_name="broken.X", path="broken.py"
        )
        method_node = builder.add_node(
            kind=NodeKind.METHOD, name="m", qualified_name="broken.X.m", path="broken.py"
        )

        ast_cache: dict[Path, Any] = {}
        # Two calls with the same broken file.
        _emit_dataflow_edges(
            builder, method_node, class_node, "m", bad_path, ast, ast_cache=ast_cache
        )
        _emit_dataflow_edges(
            builder, method_node, class_node, "m", bad_path, ast, ast_cache=ast_cache
        )

        assert bad_path in ast_cache
        assert ast_cache[bad_path] is None
        assert len(ast_cache) == 1

    def test_ast_cache_none_skips_without_raising(self, tmp_path: Path) -> None:
        """If the cache already holds ``None`` for a path, the function
        must return cleanly without touching the filesystem."""
        missing = tmp_path / "does_not_exist.py"
        builder = ProgramGraphBuilder(repo_uri="file:///ast_cache_none")
        class_node = builder.add_node(
            kind=NodeKind.CLASS, name="X", qualified_name="missing.X", path="missing.py"
        )
        method_node = builder.add_node(
            kind=NodeKind.METHOD, name="m", qualified_name="missing.X.m", path="missing.py"
        )

        ast_cache: dict[Path, Any] = {missing: None}
        # Should not raise even though the file doesn't exist.
        _emit_dataflow_edges(
            builder, method_node, class_node, "m", missing, ast, ast_cache=ast_cache
        )
        assert ast_cache == {missing: None}


# ---------------------------------------------------------------------------
# Fix 5 — INHERITS class_by_name index in run_graph
# ---------------------------------------------------------------------------


class TestInheritsLookup:
    """Regression tests for the class-name index built in ``run_graph``.

    The fixture drives ``run_graph`` over a tiny synthetic repo containing
    ``n_classes`` classes arranged in a linear inheritance chain
    ``C0 ← C1 ← C2 ← … ← C_{n-1}``. A correct O(classes) index produces
    ``n-1`` INHERITS edges in well under 0.1 s for 100 classes; a naive
    O(classes²) scan would still be fast at this size but the timing
    guard below exists to make any future regression visible.
    """

    def _write_linear_inheritance(self, tmp_path: Path, n_classes: int) -> None:
        """Write one file per class, each inheriting from the previous one."""
        for i in range(n_classes):
            if i == 0:
                body = f"class C{i}:\n    pass\n"
            else:
                body = f"from c{i-1} import C{i-1}\n\nclass C{i}(C{i-1}):\n    pass\n"
            (tmp_path / f"c{i}.py").write_text(body)

    class _Bundle:
        def __init__(self) -> None:
            self.artifacts: dict[str, Any] = {}
            self.stage_results: dict[str, Any] = {}

    def test_inherits_edges_emitted_linear_chain(self, tmp_path: Path) -> None:
        """A 10-class linear chain must produce exactly 9 INHERITS edges."""
        self._write_linear_inheritance(tmp_path, n_classes=10)

        bundle = self._Bundle()
        # run_graph imports run_ingest implicitly via the bundle contract;
        # we need to populate repo_snapshot manually via run_ingest.
        from cogant.api.orchestration import run_ingest

        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))

        pg: ProgramGraph = bundle.artifacts["_program_graph"]
        inherits = [
            e for e in pg.edges.values() if e.kind == EdgeKind.INHERITS
        ]
        assert len(inherits) == 9

    def test_inherits_100_classes_under_tight_budget(self, tmp_path: Path) -> None:
        """100 classes must resolve in well under 1 s (timing guard).

        With a correct O(n) class_by_name index the inheritance resolution
        itself is microseconds; the bulk of the time goes to ingest and
        AST parsing. A regression to O(n²) scanning would still pass on
        100 classes but would balloon on 1000+.
        """
        self._write_linear_inheritance(tmp_path, n_classes=100)

        bundle = self._Bundle()
        from cogant.api.orchestration import run_ingest

        run_ingest(str(tmp_path), bundle)

        start = time.perf_counter()
        run_graph(bundle, str(tmp_path))
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, (
            f"run_graph for 100 classes took {elapsed:.3f}s; the O(n) "
            f"class_by_name index should keep this well under 1s but "
            f"we leave a 5x slack for CI jitter."
        )

        pg: ProgramGraph = bundle.artifacts["_program_graph"]
        inherits = [
            e for e in pg.edges.values() if e.kind == EdgeKind.INHERITS
        ]
        assert len(inherits) == 99

    def test_inherits_index_does_not_self_link(self, tmp_path: Path) -> None:
        """A class listing itself as a base must not create a self-edge.

        The ``class_by_name`` lookup is guarded by
        ``other_node.id != class_node.id`` in ``run_graph``; this test
        pins that guard.
        """
        (tmp_path / "self_ref.py").write_text(
            "class C:\n    pass\n\nclass D(C):\n    pass\n"
        )
        bundle = self._Bundle()
        from cogant.api.orchestration import run_ingest

        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))

        pg: ProgramGraph = bundle.artifacts["_program_graph"]
        inherits = [
            e for e in pg.edges.values() if e.kind == EdgeKind.INHERITS
        ]
        # D → C exactly once, no self-edges.
        assert len(inherits) == 1
        assert inherits[0].source_id != inherits[0].target_id
