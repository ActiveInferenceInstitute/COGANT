# cogant-graph/src

Rust source for program graph storage. The crate implements nodes, edges, indexes, neighbor queries, and graph summaries.

## Files

- `lib.rs` - public crate API, unit tests, and FFI-facing helpers when applicable.

## Verification

From [`../../`](../../):

```bash
cargo test -p cogant-graph
cargo check -p cogant-graph
```
