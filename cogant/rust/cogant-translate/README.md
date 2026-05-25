# cogant-translate - Translation Helpers

Rust-side rule registry and node-role translation helpers. It models mapping metadata and deterministic role assignment for supported structural cases.

## Contents

- `src/lib.rs` - public crate API and crate-local tests.

## Build

```bash
cargo test -p cogant-translate
cargo check -p cogant-translate
```

## Dependencies

- `cogant-core`, `cogant-graph` - shared types and graph input
- `serde`, `serde_json` - serialization
- `uuid`, `thiserror` - ids and errors

## Scope And Status

The full Python fixpoint rule engine remains authoritative. Extend this crate only with parity tests against shipped Python rules.
