"""Benchmark: Python vs Rust program-graph building.

Measures the time to build a realistic graph of ``N_NODES`` nodes and
``N_EDGES`` random edges through three backends:

1. ``cogant.graph.builder.ProgramGraphBuilder`` (pure Python).
2. ``cogant.rust_backend.RustProgramGraphAdapter`` (Rust-backed adapter;
   keeps a Python-side shadow store so ``finalize()`` returns a Python
   ``ProgramGraph``).
3. ``cogant._rust.PyProgramGraph`` raw (Rust hot path, no Python shadow).

Run directly:

    cd projects/working/cogant/cogant
    uv run python benchmarks/bench_graph_build.py

The benchmark prints per-backend wall times and the Rust speedup factor.
The adapter measurement reflects the cost paid by pipeline code that
still needs Python-side schemas; the raw measurement shows the upper
bound speedup available from the Rust core itself.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from cogant.rust_backend import RUST_AVAILABLE, RustProgramGraphAdapter
from cogant.schemas.core import EdgeKind, NodeKind

# Tunable — keep small enough to run quickly but large enough to be
# representative of mid-sized ingests.
N_NODES = 1000
N_EDGES = 5000
SEED = 42


def _populate(builder, n_nodes: int, n_edges: int, seed: int) -> None:
    """Add ``n_nodes`` function nodes and ``n_edges`` random DEPENDS_ON edges."""
    rng = random.Random(seed)

    node_ids: list[str] = []
    for i in range(n_nodes):
        node = builder.add_node(
            kind=NodeKind.FUNCTION,
            name=f"func_{i}",
            qualified_name=f"pkg.mod.func_{i}",
            path=f"pkg/mod_{i % 16}.py",
            language="Python",
            source_range={"line_start": i, "line_end": i + 5},
        )
        node_ids.append(node.id)

    for _ in range(n_edges):
        src = rng.choice(node_ids)
        tgt = rng.choice(node_ids)
        if src == tgt:
            continue
        builder.add_edge(
            source_id=src,
            target_id=tgt,
            kind=EdgeKind.DEPENDS_ON,
            weight=rng.random(),
        )


def _time_it(factory: Callable[[], object]) -> tuple[float, int, int]:
    builder = factory()
    start = time.perf_counter()
    _populate(builder, N_NODES, N_EDGES, SEED)
    graph = builder.finalize()
    elapsed = time.perf_counter() - start
    return elapsed, graph.node_count(), graph.edge_count()


def bench_python() -> tuple[float, int, int]:
    from cogant.graph.builder import ProgramGraphBuilder

    return _time_it(lambda: ProgramGraphBuilder(repo_uri="repo://bench"))


def bench_rust() -> tuple[float, int, int]:
    return _time_it(lambda: RustProgramGraphAdapter(repo_uri="repo://bench"))


def bench_rust_raw() -> tuple[float, int, int]:
    """Time the Rust core without the Python shadow store / ID resolver."""
    from cogant._rust import PyProgramGraph

    g = PyProgramGraph()
    start = time.perf_counter()

    stable_ids: list[str] = []
    for i in range(N_NODES):
        stable_id = f"pkg.mod.func_{i}"
        g.add_node(
            "function",
            f"func_{i}",
            stable_id,
            f"pkg/mod_{i % 16}.py",
            "Python",
            i,
            i + 5,
        )
        stable_ids.append(stable_id)

    # Rust's current PyProgramGraph doesn't expose add_edge from primitives,
    # so we just time the node-ingest hot path. Edges are the dominant cost
    # in the Python builder, which is already measured above.
    _ = stable_ids  # silence linters
    elapsed = time.perf_counter() - start
    return elapsed, g.node_count(), g.edge_count()


def main() -> None:
    print(f"Benchmarking graph build: {N_NODES} nodes, {N_EDGES} edges")
    print("-" * 60)

    py_time, py_nodes, py_edges = bench_python()
    print(f"Python builder: {py_time:.4f}s  ({py_nodes} nodes, {py_edges} edges)")

    if not RUST_AVAILABLE:
        print("Rust backend: not available (skipping)")
        return

    rust_time, rust_nodes, rust_edges = bench_rust()
    print(f"Rust adapter : {rust_time:.4f}s  ({rust_nodes} nodes, {rust_edges} edges)")

    rust_raw_time, raw_nodes, _ = bench_rust_raw()
    print(f"Rust raw     : {rust_raw_time:.4f}s  ({raw_nodes} nodes, node-only path)")

    print("-" * 60)
    if rust_time > 0:
        adapter_speedup = py_time / rust_time
        print(f"Adapter speedup (nodes+edges): {adapter_speedup:.2f}x")

    if rust_raw_time > 0:
        # Compare against the Python builder's node-only hot path for a
        # fair raw comparison (edges are not yet wired on the Rust side).
        def _py_nodes_only() -> float:
            from cogant.graph.builder import ProgramGraphBuilder

            b = ProgramGraphBuilder(repo_uri="repo://bench")
            start = time.perf_counter()
            for i in range(N_NODES):
                b.add_node(
                    kind=NodeKind.FUNCTION,
                    name=f"func_{i}",
                    qualified_name=f"pkg.mod.func_{i}",
                    path=f"pkg/mod_{i % 16}.py",
                    language="Python",
                    source_range={"line_start": i, "line_end": i + 5},
                )
            return time.perf_counter() - start

        py_nodes_only = _py_nodes_only()
        raw_speedup = py_nodes_only / rust_raw_time
        print(
            f"Raw node-only speedup: {raw_speedup:.2f}x "
            f"(python {py_nodes_only:.4f}s vs rust {rust_raw_time:.4f}s)"
        )


if __name__ == "__main__":
    main()
