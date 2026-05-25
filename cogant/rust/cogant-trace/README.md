# cogant-trace - Trace Summaries

Trace event and session types plus deterministic summaries for runtime/inference dashboards and FFI event summaries.

## Contents

- `src/lib.rs` - public crate API and crate-local tests.

## Build

```bash
cargo test -p cogant-trace
cargo check -p cogant-trace
```

## Dependencies

- `cogant-core` - shared ids
- `serde`, `serde_json` - event serialization
- `uuid` - event ids

## Scope And Status

Python dynamic enrichment remains canonical for ingesting coverage and runtime traces. This crate supplies typed summaries and low-level trace data structures.
