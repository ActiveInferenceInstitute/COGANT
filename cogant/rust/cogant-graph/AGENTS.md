# Agents - rust/cogant-graph

## Owner

Infra Lead

## Scope

In-memory program graph implementation with node/edge insertion, name/kind/role queries, caller/callee helpers, edge-kind filters, graph counts, and transitive callees.

## Rules

- Keep `Cargo.toml`, `README.md`, and `src/AGENTS.md` synchronized when public behavior changes.
- Add crate-local tests for Rust behavior and Python parity tests before routing package code through the FFI.
- Keep Python as the canonical fallback unless `COGANT_USE_RUST=1` explicitly forces Rust.

## Verification

From the Rust workspace root:

```bash
cargo test -p cogant-graph
cargo clippy -p cogant-graph -- -D warnings
```
