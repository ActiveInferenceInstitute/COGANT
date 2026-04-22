# cogant-gnn — GNN Formatters (Rust)

Rust-side GNN bundle formatting helpers wrapped by [`cogant-ffi`](../cogant-ffi/).

## Contents
- `src/lib.rs` — Exported functions: `format_json`, `format_markdown`

## Build

```bash
cargo build --release
cargo test
```

## Dependencies

`[dependencies]` in `Cargo.toml`:

- `cogant-core`, `cogant-graph` — Shared types and graph input
- `serde`, `serde_json` — JSON output
- `uuid`, `thiserror` — Identifier generation and error types

No `pyo3-polars`, no `numpy` dependency, and no GPU tensor export. The authoritative GNN bundle emitter lives in [`py/cogant/gnn/formatter/`](../../py/cogant/gnn/formatter/); this crate currently only provides the two format helpers above so the Rust FFI can produce the string forms of a bundle without Python re-entry.

## Scope and status

Tensor export, Arrow/Parquet interop, and numpy-facing APIs are all implemented in the Python package. Expand this crate only when there is a concrete performance reason tied to benchmarks checked into [`benchmarks/`](../../benchmarks/).
