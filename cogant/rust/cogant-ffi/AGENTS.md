# Agents - rust/cogant-ffi

## Owner

Infra Lead

## Scope

PyO3 bindings exposing Rust graph wrappers, connected components, graph summaries, rule predicate metadata, matrix-shape summaries, GNN formatting, atomic artifact writing, and trace summaries.

## Rules

- Keep `Cargo.toml`, `README.md`, and `src/AGENTS.md` synchronized when public behavior changes.
- Add crate-local tests for Rust behavior and Python parity tests before routing package code through the FFI.
- Keep Python as the canonical fallback unless `COGANT_USE_RUST=1` explicitly forces Rust.

## Verification

From the Rust workspace root:

```bash
cargo test -p cogant-ffi
cargo clippy -p cogant-ffi -- -D warnings
```
