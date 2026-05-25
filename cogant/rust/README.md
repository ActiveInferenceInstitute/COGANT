# Rust - Optional Acceleration Workspace

PyO3-based Rust workspace for measured COGANT acceleration. Python remains the
canonical implementation; Rust paths are selected only when the extension is
installed and `COGANT_USE_RUST` permits it.

## Workspace Members

- `cogant-core/` - shared Rust types (`StableId`, node/edge kinds, semantic roles, confidence, provenance).
- `cogant-graph/` - in-memory program graph, edge insertion, neighbor queries, summaries, and connected components.
- `cogant-translate/` - rule registry, node-role translation helpers, and mapping metadata types.
- `cogant-statespace/` - state variables, actions, observations, transitions, and state-space shape helpers.
- `cogant-store/` - file-backed bundle/artifact store used by Rust tests and storage helpers.
- `cogant-trace/` - trace event/session types and deterministic trace summaries.
- `cogant-gnn/` - Markdown and JSON formatting helpers for Rust graph values.
- `cogant-ffi/` - PyO3 module exported to Python as `cogant._rust`.

## Build And Verification

```bash
cargo fmt --check
cargo check --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings
```

From the package root ([`..`](../)), `make build-rust` invokes `maturin develop`
for `cogant-ffi` and writes the extension under `py/cogant/`.

## Backend Selection

- `COGANT_USE_RUST=1` forces Rust and fails loudly if `cogant._rust` is unavailable.
- `COGANT_USE_RUST=0` forces pure Python.
- Unset uses auto mode and records the selected backend in package outputs where relevant.

Keep crate README and AGENTS files synchronized with `Cargo.toml` and the Python
adapter in [`../py/cogant/rust_backend.py`](../py/cogant/rust_backend.py).
