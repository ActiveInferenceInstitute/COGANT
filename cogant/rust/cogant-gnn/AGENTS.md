# Agents - rust/cogant-gnn

## Owner

Infra Lead

## Scope

Markdown and JSON formatting helpers for Rust `ProgramGraph` values, used by `cogant-ffi` without re-entering Python.

## Rules

- Keep `Cargo.toml`, `README.md`, and `src/AGENTS.md` synchronized when public behavior changes.
- Add crate-local tests for Rust behavior and Python parity tests before routing package code through the FFI.
- Keep Python as the canonical fallback unless `COGANT_USE_RUST=1` explicitly forces Rust.

## Verification

From the Rust workspace root:

```bash
cargo test -p cogant-gnn
cargo clippy -p cogant-gnn -- -D warnings
```
