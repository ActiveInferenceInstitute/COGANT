# cogant-translate — Translation Rule Engine (Rust stub)

Rust-side translation engine used to accelerate rule evaluation for `cogant-ffi`.

## Contents
- `src/lib.rs` — Rule type, rule registry, and entry points invoked by [`cogant-ffi`](../cogant-ffi/).

## Build

```bash
cargo build --release
cargo test
```

## Dependencies

`[dependencies]` in `Cargo.toml`:

- `cogant-core`, `cogant-graph` — Shared types and in-memory graph storage
- `serde`, `serde_json` — Serialization
- `uuid`, `thiserror` — Identifier generation and error types

No `rayon` and no `regex` — the current implementation is sequential and uses structural matching against `NodeKind`/`EdgeKind`. Parallelization and pattern-based rule conditions are tracked in the Python package's roadmap.

## Scope and status

This crate provides the Rust-side counterpart of a subset of the 22 Python translation rules (structural / semantic families). The authoritative rule set lives in [`py/cogant/translate/rules/`](../../py/cogant/translate/rules/). Performance numbers are not yet published for this crate.
