# cogant-ffi - Python Bindings

PyO3 bindings exposing Rust graph wrappers, connected components, graph summaries, rule predicate metadata, matrix-shape summaries, GNN formatting, atomic artifact writing, and trace summaries.

## Contents

- `src/lib.rs` - public crate API and crate-local tests.

## Build

```bash
cargo test -p cogant-ffi
cargo check -p cogant-ffi
```

## Dependencies

- `cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-gnn` - sibling crates used directly by the current FFI surface
- `pyo3` - Python extension bindings
- `serde`, `serde_json` - conversion helpers
- `petgraph` - connected-components helper

## Exposed Python API

The compiled `_rust` module exports graph wrapper classes plus functions for
connected components, graph summaries, rule predicate metadata, matrix-shape
summaries, GNN formatting, atomic artifact writes, and trace event summaries.
The artifact-write and trace-summary helpers are implemented in this crate;
store/trace crate parity can be wired later without changing the Python
surface.

## Scope And Status

All Python callers go through `py/cogant/rust_backend.py`, which enforces `COGANT_USE_RUST` and fallback policy.
