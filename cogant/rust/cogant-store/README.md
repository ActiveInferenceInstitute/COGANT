# cogant-store - Bundle And Artifact Store

File-backed Rust storage trait and implementation for bundle manifests plus atomic artifact bytes used by crate tests and FFI helper paths.

## Contents

- `src/lib.rs` - public crate API and crate-local tests.

## Build

```bash
cargo test -p cogant-store
cargo check -p cogant-store
```

## Dependencies

- `cogant-core`, `cogant-graph` - shared bundle graph types
- `serde`, `serde_json` - manifests and bundle serialization
- `uuid`, `thiserror` - ids and errors
- `tempfile` (dev) - isolated tests

## Scope And Status

The Python export pipeline remains canonical for package bundles. Keep this crate focused on deterministic file-store primitives.
