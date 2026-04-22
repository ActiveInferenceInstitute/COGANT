# cogant-graph — Program Graph Storage

In-memory `ProgramGraph` storage shared by the rest of the `cogant-*` workspace.

## Contents
- `src/lib.rs` — `ProgramGraph`, `NodeData`, `EdgeData` definitions and the `connected_components` helper used by [`cogant-ffi`](../cogant-ffi/).

## Build

```bash
cargo build --release
cargo test
```

## Dependencies

`[dependencies]` in `Cargo.toml`:

- `cogant-core` — Shared type definitions (`StableId`, `NodeKind`, …)
- `petgraph` — Underlying graph data structure and algorithms
- `serde`, `serde_json` — Serialization of `NodeData`/`EdgeData`
- `uuid`, `thiserror` — Identifier generation and error types

## Scope and status

This crate provides the minimal Rust-side representation that the FFI wraps; it is not yet a standalone "query engine". Advanced queries, shortest-path, and parallel BFS/DFS are currently handled in the Python package. Benchmark numbers that used to live here have been removed because they are not produced by this crate's tests.
