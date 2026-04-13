# Rust — Performance-Critical Implementations

Performance-optimized Rust implementations with Python FFI.

## Contents
- **cogant-core/** — Core types and algorithms (graph, symbol table, cache)
- **cogant-graph/** — High-performance graph storage and queries
- **cogant-translate/** — Rule engine and graph transformations
- **cogant-statespace/** — State space compilation
- **cogant-store/** — Persistent storage and indexing
- **cogant-trace/** — Trace collection and processing
- **cogant-gnn/** — GNN tensor generation
- **cogant-ffi/** — Python bindings via PyO3
- Cargo.toml (workspace) — Workspace configuration

## Build

```bash
cd rust
cargo build --release
cargo test
```

## Dependencies
- PyO3 — Python bindings
- pyo3-polars — Apache Arrow/Parquet support
- dashmap — Concurrent hashmap
- rayon — Data parallelism
