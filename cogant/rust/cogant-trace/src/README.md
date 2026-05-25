# cogant-trace/src

Rust source for trace summaries. The crate implements trace event/session types and deterministic event summaries.

## Files

- `lib.rs` - public crate API, unit tests, and FFI-facing helpers when applicable.

## Verification

From [`../../`](../../):

```bash
cargo test -p cogant-trace
cargo check -p cogant-trace
```
