# cogant-graph - Program Graph Storage

In-memory program graph implementation with node/edge insertion, name/kind/role queries, caller/callee helpers, edge-kind filters, graph counts, and transitive callees.

## Contents

- `src/lib.rs` - public crate API and crate-local tests.

## Build

```bash
cargo test -p cogant-graph
cargo check -p cogant-graph
```

## Dependencies

- `cogant-core` - shared identifiers and enum types
- `petgraph` - graph storage and traversal
- `serde`, `serde_json` - serialization
- `uuid`, `thiserror` - ids and errors

## Scope And Status

Python graph construction remains canonical; this crate supplies parity-tested hot-path helpers and FFI-ready summaries.
