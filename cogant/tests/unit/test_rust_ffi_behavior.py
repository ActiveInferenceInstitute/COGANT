"""Behavior tests for the ``cogant._rust`` PyO3 extension.

Each test pins one observable behavior of the Rust bindings, and where a
pure-Python counterpart exists, checks that the Rust result matches it.
Tests are marked ``requires_rust`` and skip when the extension is not built
(``maturin develop --release`` from ``rust/cogant-ffi``).
"""

from __future__ import annotations

import pytest

from cogant.rust_backend import RUST_AVAILABLE

pytestmark = pytest.mark.requires_rust

if not RUST_AVAILABLE:
    pytest.skip("Rust bindings not compiled", allow_module_level=True)

from cogant._rust import PyProgramGraph, create_example_graph  # noqa: E402


def _two_function_graph() -> PyProgramGraph:
    graph = PyProgramGraph()
    graph.add_node("function", "main", "pkg.main", "pkg.py", "python", 1, 5)
    graph.add_node("function", "helper", "pkg.helper", "pkg.py", "python", 6, 9)
    assert graph.add_edge("pkg.main", "pkg.helper", "calls")
    return graph


def test_get_callees_and_callers_resolve_the_stable_id_passed_to_add_node() -> None:
    graph = _two_function_graph()

    assert graph.get_callees("pkg.main") == ["helper"]
    assert graph.get_callers("pkg.helper") == ["main"]


def test_get_callees_and_callers_return_empty_for_unknown_ids() -> None:
    graph = _two_function_graph()

    assert graph.get_callees("pkg.missing") == []
    assert graph.get_callers("pkg.missing") == []


def test_example_graph_reports_its_call_edge() -> None:
    graph = create_example_graph()

    assert graph.get_callees("fn_main") == ["helper"]
    assert graph.get_callers("fn_helper") == ["main"]
