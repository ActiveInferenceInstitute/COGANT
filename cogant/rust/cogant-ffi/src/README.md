# cogant-ffi/src

Rust source for Python bindings. The crate implements PyO3 wrappers and module functions exported as cogant._rust.

## Files

- `lib.rs` - public crate API, unit tests, and FFI-facing helpers when applicable.

## Verification

From [`../../`](../../):

```bash
cargo test -p cogant-ffi
cargo check -p cogant-ffi
```
