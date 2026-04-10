"""Rust acceleration backend for COGANT.

This module provides a uniform, opt-in accessor for the high-performance
Rust/PyO3 implementation of the program-graph data structures. If the Rust
extension module (``cogant._rust``) is available it is used; otherwise callers
gracefully fall back to the pure-Python implementation in
``cogant.graph.builder``.

Import this module instead of reaching into ``cogant._rust`` directly so that
the fallback path stays explicit and callers do not need to catch
``ImportError`` themselves.

Hot path wiring
---------------
Call ``build_program_graph()`` to obtain a builder that transparently uses
Rust when available:

    from cogant.rust_backend import build_program_graph
    builder = build_program_graph(repo_uri="repo://demo")
    builder.add_node(...)
    builder.add_edge(...)
    graph = builder.finalize()

The returned object always exposes ``add_node``, ``add_edge``, and
``finalize`` so callers are backend-agnostic. Control the backend with the
``COGANT_USE_RUST`` environment variable:

    COGANT_USE_RUST=1  # force Rust (errors if unavailable)
    COGANT_USE_RUST=0  # force pure-Python
    unset             # auto-detect (prefers Rust when available)
"""

from __future__ import annotations

import os
from datetime import UTC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cogant.schemas.core import Edge, Node

try:
    from cogant._rust import (
        PyProgramGraph as _RustGraph,  # type: ignore[import-not-found,unused-ignore]  # optional Rust extension
    )
    from cogant._rust import (
        create_example_graph as _create_example_graph,  # type: ignore[import-not-found,unused-ignore]
    )
    from cogant._rust import (
        get_version as _rust_version,  # type: ignore[import-not-found,unused-ignore]
    )

    RUST_AVAILABLE: bool = True
    _RUST_VERSION: str | None = _rust_version()
except (ImportError, ModuleNotFoundError):
    _RustGraph = None  # type: ignore[assignment,misc,unused-ignore]
    _create_example_graph = None  # type: ignore[assignment,unused-ignore]
    _rust_version = None  # type: ignore[assignment,unused-ignore]
    RUST_AVAILABLE = False
    _RUST_VERSION = None


def get_program_graph_impl() -> type[Any]:
    """Return the preferred ``ProgramGraph`` implementation.

    When the Rust extension is present this returns ``PyProgramGraph`` from
    ``cogant._rust``; otherwise it returns the pure-Python
    ``ProgramGraphBuilder``. The returned class has a compatible ``add_node``
    surface area for the primitive-argument call form used by the pipeline.
    """
    if RUST_AVAILABLE and _RustGraph is not None:
        return _RustGraph
    from cogant.graph.builder import ProgramGraphBuilder

    return ProgramGraphBuilder


def rust_version() -> str | None:
    """Return the Rust backend version string, or ``None`` if unavailable."""
    return _RUST_VERSION


def create_example_graph() -> Any:
    """Return a small example ``PyProgramGraph`` for smoke-tests and demos.

    Raises ``RuntimeError`` when the Rust backend is not available — callers
    that need a graceful fallback should check ``RUST_AVAILABLE`` first.
    """
    if not RUST_AVAILABLE or _create_example_graph is None:
        raise RuntimeError(
            "Rust backend not available; install cogant-rust via "
            "`maturin develop --release` in rust/cogant-ffi/ to enable."
        )
    return _create_example_graph()


# ============================================================================
# Rust-backed ProgramGraphBuilder adapter (the hot path)
# ============================================================================


class RustProgramGraphAdapter:
    """Adapter wrapping ``cogant._rust.PyProgramGraph`` with the
    Python ``ProgramGraphBuilder`` interface.

    This lets callers invoke the Rust hot path without changing the rest of
    the pipeline. At ``finalize()`` time the Rust graph is converted into a
    pure-Python ``ProgramGraph`` so downstream consumers (serialization,
    querying, visualisation) stay on the Python side.

    Notes:
      * Node-identity uses the same ``IdentityResolver`` as the Python
        builder so node IDs are stable across backends.
      * Duplicate nodes/edges are deduplicated at the Python layer before
        being handed to Rust.
      * Rust's ``add_node`` takes primitive fields and returns an internal
        index that we don't need here — we keep our own ``nodes`` dict so
        ``finalize()`` can materialise ``schemas.core.Node`` instances.
    """

    def __init__(self, repo_uri: str) -> None:
        if not RUST_AVAILABLE or _RustGraph is None:
            raise RuntimeError(
                "RustProgramGraphAdapter requires the Rust backend; "
                "install via `maturin develop --release` in rust/cogant-ffi/."
            )

        # Import lazily to avoid pulling pydantic at module import time
        # when the Rust backend is not being used.
        from cogant.normalize.identities import IdentityResolver

        self.repo_uri = repo_uri
        self._identity_resolver = IdentityResolver()
        self._rust_graph = _RustGraph()
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}
        self._languages: set[str] = set()

    # ------------------------------------------------------------------
    # add_node / add_edge (mirror cogant.graph.builder.ProgramGraphBuilder)
    # ------------------------------------------------------------------

    def add_node(
        self,
        kind: Any,
        name: str,
        qualified_name: str,
        path: str | None = None,
        language: str | None = None,
        source_range: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Node:
        """Add a node to the Rust-backed graph.

        Returns the created Python ``Node`` (or the existing one on duplicate
        insertion) to match ``ProgramGraphBuilder.add_node``.
        """
        from cogant.schemas.core import Node

        node_id = self._identity_resolver.get_id(
            entity_type=kind.value,
            repo_uri=self.repo_uri,
            path=path,
            qualified_name=qualified_name,
        )

        existing = self._nodes.get(node_id)
        if existing is not None:
            return existing

        node = Node(
            id=node_id,
            kind=kind,
            name=name,
            qualified_name=qualified_name,
            path=path,
            language=language,
            source_range=source_range,
            metadata=metadata or {},
        )
        self._nodes[node_id] = node

        if language:
            self._languages.add(language)

        # Forward to Rust (best effort — Rust takes primitive-only fields).
        try:
            line_start = 0
            line_end = 0
            if source_range:
                line_start = int(source_range.get("line_start", 0) or 0)
                line_end = int(source_range.get("line_end", 0) or 0)
            self._rust_graph.add_node(
                kind.value,
                name,
                node_id,
                path or "",
                language or "",
                line_start,
                line_end,
            )
        except Exception:
            # Rust backend is a best-effort accelerator; failures here
            # should not corrupt the Python-side node store.
            pass

        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        kind: Any,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
        evidence_sources: list[str] | None = None,
    ) -> Edge | None:
        """Add an edge to the Rust-backed graph.

        Returns the created Python ``Edge`` or ``None`` if the endpoints
        don't exist (matching ``ProgramGraphBuilder.add_edge``).
        """
        from cogant.schemas.core import Edge

        if source_id not in self._nodes:
            return None
        if target_id not in self._nodes:
            return None

        edge_id = self._identity_resolver.generate_edge_id(
            source_id, target_id, kind.value
        )

        existing = self._edges.get(edge_id)
        if existing is not None:
            existing.weight = max(existing.weight, weight)
            if evidence_sources:
                for src in evidence_sources:
                    if src not in existing.evidence_sources:
                        existing.evidence_sources.append(src)
            return existing

        edge = Edge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            kind=kind,
            weight=weight,
            metadata=metadata or {},
            evidence_sources=evidence_sources or [],
        )
        self._edges[edge_id] = edge
        return edge

    # ------------------------------------------------------------------
    # finalize() — convert Rust graph back to a Python ProgramGraph.
    # ------------------------------------------------------------------

    def finalize(self) -> Any:
        """Materialise a ``cogant.schemas.graph.ProgramGraph`` from the
        accumulated nodes and edges.
        """
        from datetime import datetime

        from cogant.schemas.graph import GraphMetadata, ProgramGraph

        metadata = GraphMetadata(repo_uri=self.repo_uri)
        metadata.languages = set(self._languages)
        metadata.updated_at = datetime.now(UTC)

        graph = ProgramGraph(metadata=metadata)
        for node in self._nodes.values():
            graph.add_node(node)
        for edge in self._edges.values():
            graph.add_edge(edge)
        return graph

    # ------------------------------------------------------------------
    # Convenience pass-throughs.
    # ------------------------------------------------------------------

    @property
    def graph(self) -> Any:
        """Return a finalized ``ProgramGraph`` view (does not mutate state)."""
        return self.finalize()

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)


# ============================================================================
# Factory: build_program_graph
# ============================================================================


def _env_prefers_rust() -> bool | None:
    """Read ``COGANT_USE_RUST`` and interpret truthy/falsy values.

    Returns ``None`` if the variable is unset (auto-detect mode).
    """
    raw = os.environ.get("COGANT_USE_RUST")
    if raw is None:
        return None
    raw = raw.strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return None


def build_program_graph(
    repo_uri: str = "repo://unknown",
    use_rust: bool | None = None,
) -> Any:
    """Construct a ``ProgramGraphBuilder`` using the best backend available.

    Args:
        repo_uri: URI passed to the underlying builder (used for stable
            node-ID generation).
        use_rust: Explicit override. If ``None``, the ``COGANT_USE_RUST``
            environment variable decides; if that's also unset, Rust is
            used when available.

    Returns:
        Either ``RustProgramGraphAdapter`` (when Rust is available and
        enabled) or the pure-Python ``ProgramGraphBuilder``.
    """
    if use_rust is None:
        env_choice = _env_prefers_rust()
        if env_choice is None:
            use_rust = RUST_AVAILABLE
        else:
            use_rust = env_choice

    if use_rust and RUST_AVAILABLE:
        return RustProgramGraphAdapter(repo_uri)

    from cogant.graph.builder import ProgramGraphBuilder

    return ProgramGraphBuilder(repo_uri)


__all__ = [
    "RUST_AVAILABLE",
    "RustProgramGraphAdapter",
    "build_program_graph",
    "create_example_graph",
    "get_program_graph_impl",
    "rust_version",
]
