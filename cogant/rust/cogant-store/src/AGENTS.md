# Agents - rust/cogant-store/src

## Scope

Source for the `cogant-store` crate. Keep crate-local behavior here and cross-crate
Python exposure in `cogant-ffi` unless this crate is itself the FFI crate.

## Rules

- Keep Rust behavior parity-tested against Python before routing package code through it.
- Add unit tests in `lib.rs` or crate-local test modules for new public behavior.
- Update [`../README.md`](../README.md) and [`../AGENTS.md`](../AGENTS.md) when the public crate surface changes.

## Verification

From the Rust workspace root:

```bash
cargo test -p cogant-store
cargo clippy -p cogant-store -- -D warnings
```
