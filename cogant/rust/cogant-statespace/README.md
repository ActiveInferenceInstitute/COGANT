# cogant-statespace - State-Space Types

Rust-side state variables, observations, actions, transitions, state-space models, cardinality helpers, and FFI shape summaries.

## Contents

- `src/lib.rs` - public crate API and crate-local tests.

## Build

```bash
cargo test -p cogant-statespace
cargo check -p cogant-statespace
```

## Dependencies

- `cogant-core` - shared ids and semantic roles
- `serde`, `serde_json` - serialization
- `uuid`, `thiserror` - ids and errors

## Scope And Status

Python matrix compilation remains authoritative for values. This crate owns typed state-space data structures and shape-level parity helpers.
