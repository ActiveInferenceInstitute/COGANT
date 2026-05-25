# Agents - rust/

## Owner

Infra Lead

## Scope

Optional Rust acceleration workspace. Rust improves selected graph, formatting,
store, trace, and shape-summary paths, while Python remains authoritative unless
parity is proven and the backend is selected.

## Coordination

- `cogant-ffi` is the only crate that exposes Python bindings.
- `py/cogant/rust_backend.py` owns backend selection and fallback behavior.
- Each crate owns unit tests for Rust behavior; Python parity tests own package-level routing.

## Verification

```bash
cargo fmt --check
cargo check --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings
cd .. && make build-rust
```
