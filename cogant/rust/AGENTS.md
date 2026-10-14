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

## Toolchain

Edition 2024, Rust >= 1.89 (uuid 1.28 floor), PyO3 0.29, petgraph 0.8,
thiserror 2. Keep [`RUST_SETUP.md`](RUST_SETUP.md) and [`README.md`](README.md)
in sync with `Cargo.toml` when bumping dependencies.

## Verification

```bash
cargo fmt --check
cargo check --workspace
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cd .. && make build-rust
```
