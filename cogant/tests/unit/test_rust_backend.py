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
    idx = g.add_node("function", "my_func", "module.my_func", "module.py", "Python", 1, 10)
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


def test_create_example_graph_without_rust_raises(monkeypatch):
    """`create_example_graph()` raises a clear error when Rust is missing."""
    import cogant.rust_backend as rust_backend

    monkeypatch.setattr(rust_backend, "RUST_AVAILABLE", False)
    monkeypatch.setattr(rust_backend, "_create_example_graph", None)

    with pytest.raises(RuntimeError, match="Rust backend not available"):
        rust_backend.create_example_graph()


# ----------------------- build_program_graph factory ----------------------


def test_build_program_graph_python_explicit():
    """When ``use_rust=False``, a pure-Python builder is returned."""
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.rust_backend import build_program_graph

    builder = build_program_graph(repo_uri="repo://t", use_rust=False)
    assert isinstance(builder, ProgramGraphBuilder)


def test_build_program_graph_env_override_off(monkeypatch):
    """``COGANT_USE_RUST=0`` forces the Python backend regardless of Rust."""
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.rust_backend import build_program_graph

    monkeypatch.setenv("COGANT_USE_RUST", "0")
    builder = build_program_graph(repo_uri="repo://t")
    assert isinstance(builder, ProgramGraphBuilder)


@pytest.mark.requires_rust
def test_build_program_graph_env_override_on(monkeypatch):
    """``COGANT_USE_RUST=1`` selects the Rust adapter when available."""
    if not RUST_AVAILABLE:
        pytest.skip("Rust bindings not compiled")
    from cogant.rust_backend import RustProgramGraphAdapter, build_program_graph

    monkeypatch.setenv("COGANT_USE_RUST", "1")
    builder = build_program_graph(repo_uri="repo://t")
    assert isinstance(builder, RustProgramGraphAdapter)


@pytest.mark.requires_rust
def test_rust_adapter_add_node_edge_finalize_roundtrip():
    """The adapter's add_node/add_edge/finalize path returns a ProgramGraph."""
    if not RUST_AVAILABLE:
        pytest.skip("Rust bindings not compiled")
    from cogant.rust_backend import RustProgramGraphAdapter
    from cogant.schemas.core import EdgeKind, NodeKind
    from cogant.schemas.graph import ProgramGraph

    adapter = RustProgramGraphAdapter(repo_uri="repo://t")
    n1 = adapter.add_node(NodeKind.FUNCTION, "f1", "pkg.f1", "pkg.py", "Python")
    n2 = adapter.add_node(NodeKind.FUNCTION, "f2", "pkg.f2", "pkg.py", "Python")
    edge = adapter.add_edge(n1.id, n2.id, EdgeKind.DEPENDS_ON, weight=0.7)
    assert edge is not None

    graph = adapter.finalize()
    assert isinstance(graph, ProgramGraph)
    assert graph.node_count() == 2
    assert graph.edge_count() == 1


@pytest.mark.requires_rust
def test_rust_adapter_dedupes_nodes_and_edges():
    """Duplicate nodes/edges are coalesced by stable ID."""
    if not RUST_AVAILABLE:
        pytest.skip("Rust bindings not compiled")
    from cogant.rust_backend import RustProgramGraphAdapter
    from cogant.schemas.core import EdgeKind, NodeKind

    adapter = RustProgramGraphAdapter(repo_uri="repo://t")
    a = adapter.add_node(NodeKind.FUNCTION, "f1", "pkg.f1", "pkg.py", "Python")
    a2 = adapter.add_node(NodeKind.FUNCTION, "f1", "pkg.f1", "pkg.py", "Python")
    assert a is a2  # same Python object re-returned

    b = adapter.add_node(NodeKind.FUNCTION, "f2", "pkg.f2", "pkg.py", "Python")
    e1 = adapter.add_edge(a.id, b.id, EdgeKind.DEPENDS_ON)
    e2 = adapter.add_edge(a.id, b.id, EdgeKind.DEPENDS_ON)
    assert e1 is e2
    assert adapter.node_count() == 2
    assert adapter.edge_count() == 1


@pytest.mark.requires_rust
def test_rust_adapter_add_edge_rejects_missing_endpoints():
    if not RUST_AVAILABLE:
        pytest.skip("Rust bindings not compiled")
    from cogant.rust_backend import RustProgramGraphAdapter
    from cogant.schemas.core import EdgeKind

    adapter = RustProgramGraphAdapter(repo_uri="repo://t")
    edge = adapter.add_edge("ghost_a", "ghost_b", EdgeKind.DEPENDS_ON)
    assert edge is None


def test_rust_adapter_requires_rust_backend(monkeypatch):
    """Constructing the adapter without Rust raises a clear error."""
    import cogant.rust_backend as rust_backend

    monkeypatch.setattr(rust_backend, "RUST_AVAILABLE", False)
    monkeypatch.setattr(rust_backend, "_RustGraph", None)

    with pytest.raises(RuntimeError, match="RustProgramGraphAdapter requires"):
        rust_backend.RustProgramGraphAdapter(repo_uri="repo://t")
