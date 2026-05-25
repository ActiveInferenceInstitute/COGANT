# cogant-store/src

Rust source for artifact store. The crate implements file-backed bundle and artifact storage traits used by Rust-side tests and helpers.

## Files

- `lib.rs` - public crate API, unit tests, and FFI-facing helpers when applicable.

## Verification

From [`../../`](../../):

```bash
cargo test -p cogant-store
cargo check -p cogant-store
```
