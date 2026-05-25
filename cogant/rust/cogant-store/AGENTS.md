# Agents - rust/cogant-store

## Owner

Infra Lead

## Scope

File-backed Rust storage trait and implementation for bundle manifests plus atomic artifact bytes used by crate tests and FFI helper paths.

## Rules

- Keep `Cargo.toml`, `README.md`, and `src/AGENTS.md` synchronized when public behavior changes.
- Add crate-local tests for Rust behavior and Python parity tests before routing package code through the FFI.
- Keep Python as the canonical fallback unless `COGANT_USE_RUST=1` explicitly forces Rust.

## Verification

From the Rust workspace root:

```bash
cargo test -p cogant-store
cargo clippy -p cogant-store -- -D warnings
```
