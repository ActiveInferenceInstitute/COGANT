"""Targeted unit tests for ``cogant.rust_backend``.

Targets the uncovered Python-fallback branches and the
``RustProgramGraphAdapter`` paths that previously had no test:

* ``get_program_graph_impl()`` — Python fallback when Rust unavailable.
* ``create_example_graph()`` — RuntimeError branch.
* ``RustProgramGraphAdapter.__init__`` — RuntimeError when unavailable.
* ``add_node`` — source_range with line_start/line_end + Rust exception
  swallow path.
* ``add_edge`` — missing target, existing-edge update branch.
* ``graph`` property — returns finalized graph.
* ``build_program_graph()`` — env var ``COGANT_USE_RUST=0``/``1`` paths.
* ``_env_prefers_rust()`` — invalid value returns None.

Uses ``monkeypatch`` to flip module-level constants for the fallback
paths — this is attribute reassignment with deterministic restoration,
not a mock of behaviour.
"""

from __future__ import annotations

import pytest

from cogant import rust_backend
from cogant.rust_backend import (
    RUST_AVAILABLE,
    RustProgramGraphAdapter,
    _env_prefers_rust,
    build_program_graph,
    create_example_graph,
    get_program_graph_impl,
    rust_version,
)
from cogant.schemas.core import EdgeKind, NodeKind

# ------------------------------------------------------------------ #
# get_program_graph_impl — fallback branch
# ------------------------------------------------------------------ #


def test_get_program_graph_impl_python_fallback(monkeypatch) -> None:
    """When Rust is unavailable, the pure-Python builder class is returned."""
    monkeypatch.setattr(rust_backend, "RUST_AVAILABLE", False)
    monkeypatch.setattr(rust_backend, "_RustGraph", None)

    impl = get_program_graph_impl()
    from cogant.graph.builder import ProgramGraphBuilder

    assert impl is ProgramGraphBuilder


def test_get_program_graph_impl_rust_when_available() -> None:
    """When Rust is available, a callable type is returned."""
    impl = get_program_graph_impl()
    # Whatever it is, should be a class/callable.
    assert isinstance(impl, type) or callable(impl)


# ------------------------------------------------------------------ #
# create_example_graph — RuntimeError branch
# ------------------------------------------------------------------ #


def test_create_example_graph_raises_when_rust_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(rust_backend, "RUST_AVAILABLE", False)
    monkeypatch.setattr(rust_backend, "_create_example_graph", None)

    with pytest.raises(RuntimeError, match="Rust backend not available"):
        create_example_graph()


# ------------------------------------------------------------------ #
# rust_version — sanity
# ------------------------------------------------------------------ #


def test_rust_version_returns_none_or_str() -> None:
    val = rust_version()
    assert val is None or isinstance(val, str)


# ------------------------------------------------------------------ #
# RustProgramGraphAdapter.__init__ — unavailable branch
# ------------------------------------------------------------------ #


def test_rust_adapter_init_raises_when_rust_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(rust_backend, "RUST_AVAILABLE", False)
    monkeypatch.setattr(rust_backend, "_RustGraph", None)

    with pytest.raises(RuntimeError, match="RustProgramGraphAdapter requires"):
        RustProgramGraphAdapter("repo://x")


# ------------------------------------------------------------------ #
# RustProgramGraphAdapter — runtime add_node / add_edge surface
# ------------------------------------------------------------------ #


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not built")
def test_rust_adapter_add_node_with_source_range_keys() -> None:
    """source_range with line_start/line_end is forwarded to Rust."""
    adapter = RustProgramGraphAdapter("repo://test")
    node = adapter.add_node(
        kind=NodeKind.FUNCTION,
        name="fn_a",
        qualified_name="pkg.fn_a",
        path="pkg/mod.py",
        language="python",
        source_range={"line_start": 1, "line_end": 10},
        metadata={"x": 1},
    )
    assert node.id in adapter._nodes
    assert adapter.node_count() == 1


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not built")
def test_rust_adapter_add_node_duplicate_returns_existing() -> None:
    adapter = RustProgramGraphAdapter("repo://test")
    n1 = adapter.add_node(
        kind=NodeKind.FUNCTION,
        name="dup",
        qualified_name="pkg.dup",
        path="pkg/mod.py",
    )
    n2 = adapter.add_node(
        kind=NodeKind.FUNCTION,
        name="dup",
        qualified_name="pkg.dup",
        path="pkg/mod.py",
    )
    assert n1 is n2
    assert adapter.node_count() == 1


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not built")
def test_rust_adapter_add_edge_missing_source_returns_none() -> None:
    adapter = RustProgramGraphAdapter("repo://test")
    edge = adapter.add_edge(
        source_id="absent_source",
        target_id="absent_target",
        kind=EdgeKind.CALLS,
    )
    assert edge is None


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not built")
def test_rust_adapter_add_edge_missing_target_returns_none() -> None:
    """Source exists, target missing → None (line 228 branch)."""
    adapter = RustProgramGraphAdapter("repo://test")
    src = adapter.add_node(
        kind=NodeKind.FUNCTION,
        name="src_fn",
        qualified_name="pkg.src_fn",
        path="pkg/mod.py",
    )
    edge = adapter.add_edge(
        source_id=src.id,
        target_id="nonexistent",
        kind=EdgeKind.CALLS,
    )
    assert edge is None


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not built")
def test_rust_adapter_add_edge_existing_updates_weight_and_evidence() -> None:
    """Adding the same edge twice raises weight + extends evidence list."""
    adapter = RustProgramGraphAdapter("repo://test")
    a = adapter.add_node(
        kind=NodeKind.FUNCTION, name="a", qualified_name="pkg.a", path="pkg/mod.py"
    )
    b = adapter.add_node(
        kind=NodeKind.FUNCTION, name="b", qualified_name="pkg.b", path="pkg/mod.py"
    )
    e1 = adapter.add_edge(
        source_id=a.id, target_id=b.id, kind=EdgeKind.CALLS, weight=0.3,
        evidence_sources=["static"],
    )
    e2 = adapter.add_edge(
        source_id=a.id, target_id=b.id, kind=EdgeKind.CALLS, weight=0.7,
        evidence_sources=["dynamic_trace", "static"],  # static is dup
    )
    assert e1 is e2  # same edge object
    assert e2.weight == 0.7  # max raised
    assert "static" in e2.evidence_sources
    assert "dynamic_trace" in e2.evidence_sources
    # 'static' should not duplicate
    assert e2.evidence_sources.count("static") == 1


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not built")
def test_rust_adapter_graph_property_returns_finalized() -> None:
    """The .graph property materialises a fresh ProgramGraph each call."""
    adapter = RustProgramGraphAdapter("repo://test")
    adapter.add_node(
        kind=NodeKind.FUNCTION, name="f", qualified_name="pkg.f", path="pkg/mod.py"
    )
    graph = adapter.graph
    from cogant.schemas.graph import ProgramGraph

    assert isinstance(graph, ProgramGraph)
    assert len(graph.nodes) == 1


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not built")
def test_rust_adapter_node_count_edge_count_zero() -> None:
    adapter = RustProgramGraphAdapter("repo://test")
    assert adapter.node_count() == 0
    assert adapter.edge_count() == 0


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not built")
def test_rust_adapter_finalize_with_edges() -> None:
    adapter = RustProgramGraphAdapter("repo://test")
    a = adapter.add_node(
        kind=NodeKind.FUNCTION, name="a", qualified_name="pkg.a", path="m.py", language="python"
    )
    b = adapter.add_node(
        kind=NodeKind.FUNCTION, name="b", qualified_name="pkg.b", path="m.py", language="python"
    )
    adapter.add_edge(source_id=a.id, target_id=b.id, kind=EdgeKind.CALLS)
    g = adapter.finalize()
    assert len(g.nodes) == 2
    assert len(g.edges) == 1
    assert "python" in g.metadata.languages


# ------------------------------------------------------------------ #
# build_program_graph — backend selection
# ------------------------------------------------------------------ #


def test_build_program_graph_explicit_python(monkeypatch) -> None:
    """``use_rust=False`` always returns the pure-Python builder."""
    builder = build_program_graph("repo://x", use_rust=False)
    from cogant.graph.builder import ProgramGraphBuilder

    assert isinstance(builder, ProgramGraphBuilder)


def test_build_program_graph_env_disables_rust(monkeypatch) -> None:
    """COGANT_USE_RUST=0 forces the Python builder."""
    monkeypatch.setenv("COGANT_USE_RUST", "0")
    builder = build_program_graph("repo://x")
    from cogant.graph.builder import ProgramGraphBuilder

    assert isinstance(builder, ProgramGraphBuilder)


def test_build_program_graph_env_enables_rust_when_available(monkeypatch) -> None:
    """COGANT_USE_RUST=1 returns the Rust adapter (when available)."""
    monkeypatch.setenv("COGANT_USE_RUST", "1")
    if RUST_AVAILABLE:
        builder = build_program_graph("repo://x")
        assert isinstance(builder, RustProgramGraphAdapter)
    else:
        # Even with COGANT_USE_RUST=1 the code falls back to Python when
        # the extension is not actually available.
        builder = build_program_graph("repo://x")
        from cogant.graph.builder import ProgramGraphBuilder

        assert isinstance(builder, ProgramGraphBuilder)


def test_build_program_graph_unset_env_autodetect(monkeypatch) -> None:
    monkeypatch.delenv("COGANT_USE_RUST", raising=False)
    builder = build_program_graph("repo://x")
    # When auto-detect, returns whichever backend is currently available.
    assert builder is not None
    assert hasattr(builder, "add_node")
    assert hasattr(builder, "finalize")


def test_build_program_graph_python_when_rust_unavailable(monkeypatch) -> None:
    """Forced Rust mode fails loudly when the extension is unavailable."""
    monkeypatch.setattr(rust_backend, "RUST_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="COGANT_USE_RUST=1"):
        build_program_graph("repo://x", use_rust=True)


# ------------------------------------------------------------------ #
# _env_prefers_rust — value parsing
# ------------------------------------------------------------------ #


def test_env_prefers_rust_unset(monkeypatch) -> None:
    monkeypatch.delenv("COGANT_USE_RUST", raising=False)
    assert _env_prefers_rust() is None


@pytest.mark.parametrize("val", ["1", "true", "yes", "on", "TRUE", "Yes"])
def test_env_prefers_rust_truthy(monkeypatch, val: str) -> None:
    monkeypatch.setenv("COGANT_USE_RUST", val)
    assert _env_prefers_rust() is True


@pytest.mark.parametrize("val", ["0", "false", "no", "off", "False"])
def test_env_prefers_rust_falsy(monkeypatch, val: str) -> None:
    monkeypatch.setenv("COGANT_USE_RUST", val)
    assert _env_prefers_rust() is False


def test_env_prefers_rust_invalid_value_returns_none(monkeypatch) -> None:
    """Unknown values fall through to None (auto-detect)."""
    monkeypatch.setenv("COGANT_USE_RUST", "maybe")
    assert _env_prefers_rust() is None
