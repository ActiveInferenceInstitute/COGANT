# cogant-core/src

Rust source for shared Rust types. The crate implements StableId, NodeKind, EdgeKind, SemanticRole, confidence, and provenance primitives.

## Files

- `lib.rs` - public crate API, unit tests, and FFI-facing helpers when applicable.

## Verification

From [`../../`](../../):

```bash
cargo test -p cogant-core
cargo check -p cogant-core
```
