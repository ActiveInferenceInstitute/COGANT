# cogant-graph — High-Performance Graph Storage

Fast graph storage and query engine for COGANT.

## Contents
- src/lib.rs — GraphStorage, QueryEngine, traversal algorithms

## Features
- Compressed sparse row (CSR) representation
- O(1) edge lookup by source and type
- Parallel BFS and DFS
- Shortest path (Dijkstra, A*)
- Reachability and dominance analysis

## Build

```bash
cargo build --release
cargo test
```

## Dependencies
- cogant-core — Type definitions
- rayon — Parallel iteration
- petgraph — Graph algorithms

## Performance

Graph with 100K nodes, 1M edges:
- Node/edge access: < 1μs
- BFS: < 10ms
- DFS: < 5ms
- Shortest path: < 50ms
