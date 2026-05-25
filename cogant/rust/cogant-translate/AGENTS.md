# Agents - rust/cogant-translate

## Owner

Semantic Lead

## Scope

Rust-side rule registry and node-role translation helpers. It models mapping metadata and deterministic role assignment for supported structural cases.

## Rules

- Keep `Cargo.toml`, `README.md`, and `src/AGENTS.md` synchronized when public behavior changes.
- Add crate-local tests for Rust behavior and Python parity tests before routing package code through the FFI.
- Keep Python as the canonical fallback unless `COGANT_USE_RUST=1` explicitly forces Rust.

## Verification

From the Rust workspace root:

```bash
cargo test -p cogant-translate
cargo clippy -p cogant-translate -- -D warnings
```
