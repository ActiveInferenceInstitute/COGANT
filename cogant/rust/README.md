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

## Toolchain

Edition 2024, stable Rust 1.89 or newer. Key dependencies: PyO3 0.29,
petgraph 0.8, thiserror 2, uuid 1.28; maturin `>=1.0,<2.0` builds the
extension. See [`RUST_SETUP.md`](RUST_SETUP.md) for the full setup.

The release profile explicitly disables stripping. Rust's debug-information
stripping can misalign the Mach-O string pool and prevent the built extension
from loading on recent macOS releases
([Rust issue 157750](https://github.com/rust-lang/rust/issues/157750)). Keep the
installed-extension import check alongside compilation tests.

## Build And Verification

```bash
cargo fmt --check
cargo check --workspace
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```

From the package root ([`..`](../)), `make build-rust` runs
`cargo build --release`; `maturin develop --release` from `cogant-ffi/` (see
[`RUST_SETUP.md`](RUST_SETUP.md)) builds the extension and writes it under
`py/cogant/`.

## Backend Selection

- `COGANT_USE_RUST=1` forces Rust and fails loudly if `cogant._rust` is unavailable.
- `COGANT_USE_RUST=0` forces pure Python.
- Unset uses auto mode and records the selected backend in package outputs where relevant.

Keep crate README and AGENTS files synchronized with `Cargo.toml` and the Python
adapter in [`../py/cogant/rust_backend.py`](../py/cogant/rust_backend.py).
