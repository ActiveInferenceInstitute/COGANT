# cogant-ffi — Python Bindings

PyO3-based FFI bindings exposing Rust implementations to Python.

## Contents
- `src/lib.rs` — PyO3 module definitions and type wrappers

The crate compiles to a `cdylib`/`rlib` named `_rust` (see `[lib]` in `Cargo.toml`), so Python imports resolve via `cogant._rust`.

## Exposed Python API

Currently wrapped (see `src/lib.rs`):

```python
from cogant._rust import (
    PyStableId, PyConfidence, PyNodeData, PyProgramGraph,
    connected_components,   # module-level function over PyProgramGraph
    get_version, create_example_graph,
)
```

Higher-level Python classes (`RuleEngine`, `StateSpaceCompiler`, `PersistentStore`, …) live in the pure-Python package under [`py/cogant/`](../../py/cogant/) and are **not** re-exported through this crate. See [`py/cogant/rust_backend.py`](../../py/cogant/rust_backend.py) for the `COGANT_USE_RUST=1` gated callers.

## Build

```bash
cargo build --release
maturin develop       # or: pip install -e .[rust]
```

## Dependencies

`[dependencies]` in `Cargo.toml` (workspace-resolved versions):

- `cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-gnn` — sibling crates used for the wrapped types
- `pyo3` — Python bindings (extension-module feature)
- `serde`, `serde_json` — serialization helpers
- `petgraph` — used for the `connected_components` helper

Note: `cogant-store` and `cogant-trace` are **not** wired through the FFI yet.

## Testing

Integration tests that exercise the FFI live in the Python test suite (`tests/`) — enable them with the `requires_rust` pytest marker after `make build-rust` has produced `py/cogant/_rust.*.so`.
