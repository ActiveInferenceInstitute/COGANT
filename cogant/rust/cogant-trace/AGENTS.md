# Agents - rust/cogant-trace

## Owner

Infra Lead

## Scope

Trace event and session types plus deterministic summaries for runtime/inference dashboards and FFI event summaries.

## Rules

- Keep `Cargo.toml`, `README.md`, and `src/AGENTS.md` synchronized when public behavior changes.
- Add crate-local tests for Rust behavior and Python parity tests before routing package code through the FFI.
- Keep Python as the canonical fallback unless `COGANT_USE_RUST=1` explicitly forces Rust.

## Verification

From the Rust workspace root:

```bash
cargo test -p cogant-trace
cargo clippy -p cogant-trace -- -D warnings
```
