"""Rust acceleration backend for COGANT.

This module provides a uniform, opt-in accessor for the high-performance
Rust/PyO3 implementation of the program-graph data structures. If the Rust
extension module (`cogant._rust`) is available it is used; otherwise callers
gracefully fall back to the pure-Python implementation in
`cogant.graph.builder`.

Import this module instead of reaching into `cogant._rust` directly so that
the fallback path stays explicit and callers do not need to catch
`ImportError` themselves.
"""

from __future__ import annotations

from typing import Any

try:
    from cogant._rust import PyProgramGraph as _RustGraph
    from cogant._rust import create_example_graph as _create_example_graph
    from cogant._rust import get_version as _rust_version

    RUST_AVAILABLE: bool = True
    _RUST_VERSION: str | None = _rust_version()
except (ImportError, ModuleNotFoundError):
    _RustGraph = None
    _create_example_graph = None
    _rust_version = None
    RUST_AVAILABLE = False
    _RUST_VERSION = None


def get_program_graph_impl() -> type:
    """Return the preferred `ProgramGraph` implementation.

    When the Rust extension is present this returns `PyProgramGraph` from
    `cogant._rust`; otherwise it returns the pure-Python
    `ProgramGraphBuilder`. The returned class has a compatible `add_node`
    surface area for the primitive-argument call form used by the pipeline.
    """
    if RUST_AVAILABLE and _RustGraph is not None:
        return _RustGraph
    from cogant.graph.builder import ProgramGraphBuilder

    return ProgramGraphBuilder


def rust_version() -> str | None:
    """Return the Rust backend version string, or `None` if unavailable."""
    return _RUST_VERSION


def create_example_graph() -> Any:
    """Return a small example `PyProgramGraph` for smoke-tests and demos.

    Raises `RuntimeError` when the Rust backend is not available — callers
    that need a graceful fallback should check `RUST_AVAILABLE` first.
    """
    if not RUST_AVAILABLE or _create_example_graph is None:
        raise RuntimeError(
            "Rust backend not available; install cogant-rust via "
            "`maturin develop --release` in rust/cogant-ffi/ to enable."
        )
    return _create_example_graph()


__all__ = [
    "RUST_AVAILABLE",
    "get_program_graph_impl",
    "rust_version",
    "create_example_graph",
]
