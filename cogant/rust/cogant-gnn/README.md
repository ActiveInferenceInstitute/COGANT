# cogant-gnn - GNN Formatters

Markdown and JSON formatting helpers for Rust `ProgramGraph` values, used by `cogant-ffi` without re-entering Python.

## Contents

- `src/lib.rs` - public crate API and crate-local tests.

## Build

```bash
cargo test -p cogant-gnn
cargo check -p cogant-gnn
```

## Dependencies

- `cogant-core`, `cogant-graph` - shared types and graph input
- `serde`, `serde_json` - JSON output
- `uuid`, `thiserror` - ids and errors

## Scope And Status

The full GNN package emitter remains in Python. This crate owns Rust string-format parity helpers only.
