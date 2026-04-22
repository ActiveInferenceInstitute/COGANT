# cogant-core — Core Types

Shared Rust types used by the rest of the `cogant-*` workspace and exposed to Python through [`cogant-ffi`](../cogant-ffi/).

## Contents
- `src/lib.rs` — Public re-exports
- Types: `StableId`, `NodeKind`, `EdgeKind`, `Confidence`, `Provenance`, `SemanticRole`

## Build

```bash
cargo build --release
cargo test
```

## Dependencies

`[dependencies]` in `Cargo.toml`:

- `serde`, `serde_json` — Serialization
- `uuid` — Stable identifier generation
- `thiserror` — Error types

No concurrent data structures, no async runtime, no system dependencies. The crate is intentionally lightweight and purely synchronous.

## Python FFI

Exported via [`cogant-ffi`](../cogant-ffi/) as `PyStableId`, `PyConfidence`, and embedded fields on `PyNodeData`/`PyProgramGraph`.
