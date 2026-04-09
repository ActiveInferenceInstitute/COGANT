"""Tests for the Rust backend availability shim and basic functionality.

These tests cover both the always-available pure-Python import path and,
when the compiled extension is present, the PyO3 bindings themselves. Tests
that exercise Rust internals are gated on `RUST_AVAILABLE` so the suite
keeps passing on machines without a Rust toolchain.
"""

from __future__ import annotations

import pytest

from cogant.rust_backend import RUST_AVAILABLE


def test_rust_backend_importable():
    """Rust backend shim must always be importable, even without Rust."""
    from cogant import rust_backend

    assert hasattr(rust_backend, "RUST_AVAILABLE")
    assert isinstance(rust_backend.RUST_AVAILABLE, bool)
    assert hasattr(rust_backend, "get_program_graph_impl")
    assert hasattr(rust_backend, "rust_version")


def test_get_program_graph_impl_returns_callable():
    """`get_program_graph_impl` always returns a usable class."""
    from cogant.rust_backend import get_program_graph_impl

    impl = get_program_graph_impl()
    assert impl is not None
    assert callable(impl)


def test_rust_version_shape():
    """`rust_version()` returns a string when Rust is available, else None."""
    from cogant.rust_backend import rust_version

    version = rust_version()
    if RUST_AVAILABLE:
        assert isinstance(version, str)
        assert len(version) > 0
    else:
        assert version is None


def test_cogant_package_exposes_rust_flag():
    """The top-level `cogant` package re-exports the rust availability flag."""
    import cogant

    assert hasattr(cogant, "_RUST_AVAILABLE")
    assert hasattr(cogant, "__rust_version__")
    assert isinstance(cogant._RUST_AVAILABLE, bool)


@pytest.mark.requires_rust
def test_rust_graph_creation():
    """Create a graph and add a node via the Rust bindings."""
    if not RUST_AVAILABLE:
        pytest.skip("Rust bindings not compiled")
    from cogant._rust import PyProgramGraph

    g = PyProgramGraph()
    idx = g.add_node(
        "function", "my_func", "module.my_func", "module.py", "Python", 1, 10
    )
    assert idx == 0
    assert g.node_count() == 1
    assert g.edge_count() == 0


@pytest.mark.requires_rust
def test_rust_example_graph():
    """The demo graph has 3 nodes and 2 edges."""
    if not RUST_AVAILABLE:
        pytest.skip("Rust bindings not compiled")
    from cogant.rust_backend import create_example_graph

    g = create_example_graph()
    assert g.node_count() == 3
    assert g.edge_count() == 2


@pytest.mark.requires_rust
def test_rust_graph_str_repr():
    """`str(graph)` returns a compact description."""
    if not RUST_AVAILABLE:
        pytest.skip("Rust bindings not compiled")
    from cogant._rust import PyProgramGraph

    g = PyProgramGraph()
    assert "ProgramGraph" in str(g)
    assert "nodes=0" in str(g)


def test_create_example_graph_without_rust_raises():
    """`create_example_graph()` raises a clear error when Rust is missing."""
    if RUST_AVAILABLE:
        pytest.skip("Rust bindings present; fallback error path unreachable")
    from cogant.rust_backend import create_example_graph

    with pytest.raises(RuntimeError, match="Rust backend not available"):
        create_example_graph()
