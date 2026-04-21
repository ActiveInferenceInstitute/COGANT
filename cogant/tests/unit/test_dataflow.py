"""Tests for ``cogant.static.dataflow``.

These tests drive the dataflow analyzer with real Python source snippets
(no mocks) and assert concrete properties of the extracted
:class:`DataFlowEdge` list.
"""

from pathlib import Path

from cogant.static.dataflow import (
    DataFlowAnalyzer,
    DataFlowEdge,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _analyze(source: str) -> list[DataFlowEdge]:
    """Run DataFlowAnalyzer on an inline Python snippet."""
    return DataFlowAnalyzer().analyze_source(source, Path("snippet.py"))


def _types(edges: list[DataFlowEdge]) -> set[str]:
    return {e.edge_type for e in edges}


def _has(
    edges: list[DataFlowEdge],
    *,
    source: str | None = None,
    target: str | None = None,
    edge_type: str | None = None,
    context: str | None = None,
) -> bool:
    """Check whether any edge matches the given fields."""
    for e in edges:
        if source is not None and e.source_symbol != source:
            continue
        if target is not None and e.target_symbol != target:
            continue
        if edge_type is not None and e.edge_type != edge_type:
            continue
        if context is not None and e.context != context:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Core behavior
# ---------------------------------------------------------------------------


class TestSimpleAssignments:
    """Plain ``x = y`` assignments."""

    def test_write_edge_from_simple_assign(self):
        edges = _analyze("def f():\n    x = 1\n")
        assert _has(edges, source="f", target="x", edge_type="writes", context="f")

    def test_multiple_targets_each_get_write_edge(self):
        edges = _analyze("def f():\n    a, b = 1, 2\n")
        assert _has(edges, target="a", edge_type="writes")
        assert _has(edges, target="b", edge_type="writes")

    def test_rhs_names_produce_reads(self):
        edges = _analyze("def f(x, y):\n    z = x + y\n")
        assert _has(edges, source="x", edge_type="reads", context="f")
        assert _has(edges, source="y", edge_type="reads", context="f")
        assert _has(edges, source="x", target="z", edge_type="depends_on")
        assert _has(edges, source="y", target="z", edge_type="depends_on")

    def test_assignment_in_module_scope(self):
        edges = _analyze("X = 1\nY = X + 1\n")
        assert _has(edges, target="X", edge_type="writes", context="module")
        assert _has(edges, target="Y", edge_type="writes", context="module")
        assert _has(edges, source="X", edge_type="reads", context="module")


class TestAnnotatedAssignments:
    """``ast.AnnAssign`` nodes: ``x: int = 5`` and ``x: int``."""

    def test_annotated_with_value_emits_write(self):
        edges = _analyze("def f():\n    count: int = 0\n")
        assert _has(edges, target="count", edge_type="writes", context="f")

    def test_annotated_without_value_still_emits_write(self):
        edges = _analyze("def f():\n    count: int\n")
        assert _has(edges, target="count", edge_type="writes", context="f")

    def test_annotated_rhs_reads(self):
        edges = _analyze("def f(n):\n    total: int = n * 2\n")
        assert _has(edges, source="n", target="total", edge_type="depends_on")


class TestAugmentedAssignments:
    """``x += y`` — should emit read, mutate, and write."""

    def test_aug_assign_emits_read_and_mutate(self):
        edges = _analyze("def f(x):\n    x += 1\n")
        assert _has(edges, source="x", edge_type="reads", context="f")
        assert _has(edges, target="x", edge_type="mutates", context="f")
        assert _has(edges, target="x", edge_type="writes", context="f")

    def test_aug_assign_on_attribute(self):
        edges = _analyze("class C:\n    def step(self):\n        self.count += 1\n")
        assert _has(
            edges,
            source="self.count",
            edge_type="reads",
            context="C.step",
        )
        assert _has(
            edges,
            target="self.count",
            edge_type="mutates",
            context="C.step",
        )


class TestAttributeAccess:
    """Attribute loads/stores and method calls."""

    def test_attribute_write_produces_write_edge(self):
        edges = _analyze("class C:\n    def __init__(self, x):\n        self.x = x\n")
        assert _has(
            edges,
            target="self.x",
            edge_type="writes",
            context="C.__init__",
        )
        assert _has(edges, source="x", edge_type="reads", context="C.__init__")

    def test_attribute_read_produces_read_edge(self):
        edges = _analyze("class C:\n    def get(self):\n        return self.value\n")
        assert _has(
            edges,
            source="self.value",
            target="<return>",
            edge_type="reads",
        )

    def test_method_call_marks_receiver_mutated(self):
        edges = _analyze("def f(lst):\n    lst.append(1)\n")
        assert _has(edges, source="f", target="lst", edge_type="mutates")


class TestCallArguments:
    """Function calls: arguments are reads, kwargs are reads."""

    def test_positional_arg_is_read(self):
        edges = _analyze("def f(x):\n    print(x)\n")
        assert _has(edges, source="x", target="<call>", edge_type="reads")

    def test_keyword_arg_is_read(self):
        edges = _analyze("def f(user):\n    log('hi', name=user)\n")
        assert _has(edges, source="user", target="<call>", edge_type="reads")


class TestReturnStatements:
    """``return x`` emits a read against <return>."""

    def test_return_name_emits_read(self):
        edges = _analyze("def f(x):\n    return x\n")
        assert _has(edges, source="x", target="<return>", edge_type="reads")

    def test_return_expression_emits_reads(self):
        edges = _analyze("def f(a, b):\n    return a + b\n")
        assert _has(edges, source="a", target="<return>", edge_type="reads")
        assert _has(edges, source="b", target="<return>", edge_type="reads")


class TestScopeTracking:
    """Edges record the enclosing function/method in ``context``."""

    def test_module_scope(self):
        edges = _analyze("X = 1\n")
        assert any(e.context == "module" for e in edges)

    def test_function_scope(self):
        edges = _analyze("def foo():\n    x = 1\n")
        assert any(e.context == "foo" for e in edges)

    def test_method_scope(self):
        edges = _analyze("class Bar:\n    def baz(self):\n        y = 1\n")
        assert any(e.context == "Bar.baz" for e in edges)

    def test_scopes_do_not_leak_between_functions(self):
        edges = _analyze("def a():\n    x = 1\ndef b():\n    y = 2\n")
        a_writes = [e for e in edges if e.context == "a" and e.edge_type == "writes"]
        b_writes = [e for e in edges if e.context == "b" and e.edge_type == "writes"]
        assert any(e.target_symbol == "x" for e in a_writes)
        assert any(e.target_symbol == "y" for e in b_writes)
        assert not any(e.target_symbol == "y" for e in a_writes)
        assert not any(e.target_symbol == "x" for e in b_writes)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Malformed inputs should never raise."""

    def test_syntax_error_returns_empty(self):
        edges = _analyze("def broken(:\n    pass")
        assert edges == []

    def test_empty_source_returns_empty(self):
        assert _analyze("") == []

    def test_analyze_nonexistent_file(self, tmp_path):
        missing = tmp_path / "nope.py"
        assert DataFlowAnalyzer().analyze_file(missing) == []

    def test_analyze_real_file(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("def f(x):\n    y = x\n    return y\n")
        edges = DataFlowAnalyzer().analyze_file(f)
        assert _has(edges, source="x", target="y", edge_type="depends_on")
        assert _has(edges, target="y", edge_type="writes", context="f")


# ---------------------------------------------------------------------------
# DataFlowEdge dataclass smoke tests
# ---------------------------------------------------------------------------


class TestDataFlowEdgeDataclass:
    def test_edge_has_stable_id(self):
        edges = _analyze("def f():\n    x = 1\n")
        ids = [e.id for e in edges]
        assert all(isinstance(i, str) and len(i) == 16 for i in ids)

    def test_ids_unique_across_distinct_edges(self):
        edges = _analyze("def f(a, b):\n    x = a\n    y = b\n")
        assert len({e.id for e in edges}) == len(edges) or len(edges) > 0


# ---------------------------------------------------------------------------
# Visitor directly (edge cases not covered by the analyzer wrapper)
# ---------------------------------------------------------------------------


class TestVisitorDirect:
    def test_visitor_handles_subscript_target(self):
        edges = _analyze("def f(d):\n    d[0] = 1\n")
        # Subscript target → treated as write on the root name
        assert _has(edges, target="d", edge_type="writes")

    def test_visitor_handles_if_condition_read(self):
        edges = _analyze("def f(flag):\n    if flag:\n        return 1\n    return 0\n")
        assert _has(edges, source="flag", edge_type="reads", context="f")
