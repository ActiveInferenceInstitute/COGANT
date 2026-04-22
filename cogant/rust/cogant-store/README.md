# cogant-store — In-Memory Graph Store (Rust stub)

Rust-side scaffolding for persistent graph storage.

## Contents
- `src/lib.rs` — Storage trait, in-memory backend, and snapshot placeholders

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
- `tempfile` (dev) — Temporary directories for tests

No RocksDB, no rusqlite, no on-disk backend. The crate provides an **in-memory** store today; persistent backends are aspirational and intentionally out of scope until usage patterns stabilize.

## Scope and status

This crate is **not** wired through [`cogant-ffi`](../cogant-ffi/); the Python pipeline writes bundles directly to disk (`py/cogant/export/`). Treat this crate as a placeholder for a future Rust persistence layer.
