# cogant-trace — Trace Collection (Rust stub)

Rust-side scaffolding for runtime trace collection.

## Contents
- `src/lib.rs` — Event record types and collection entry points

## Build

```bash
cargo build --release
cargo test
```

## Dependencies

`[dependencies]` in `Cargo.toml`:

- `cogant-core` — Shared types
- `serde`, `serde_json` — Event record serialization
- `uuid` — Event identifiers

No compression (`zstd`) dependency, no pytest/unittest integration shims. The authoritative trace ingest path lives in [`py/cogant/dynamic/`](../../py/cogant/dynamic/) and consumes the output of standard coverage/trace tooling (`coverage.py`, `pytest-cov`).

## Scope and status

This crate is **not** wired through [`cogant-ffi`](../cogant-ffi/); it exists to reserve a Rust-side trace API that can be added later without an API break.
