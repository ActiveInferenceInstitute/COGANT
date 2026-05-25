# Agents - rust/cogant-statespace

## Owner

Infra Lead

## Scope

Rust-side state variables, observations, actions, transitions, state-space models, cardinality helpers, and FFI shape summaries.

## Rules

- Keep `Cargo.toml`, `README.md`, and `src/AGENTS.md` synchronized when public behavior changes.
- Add crate-local tests for Rust behavior and Python parity tests before routing package code through the FFI.
- Keep Python as the canonical fallback unless `COGANT_USE_RUST=1` explicitly forces Rust.

## Verification

From the Rust workspace root:

```bash
cargo test -p cogant-statespace
cargo clippy -p cogant-statespace -- -D warnings
```
