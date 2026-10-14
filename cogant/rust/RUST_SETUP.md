# COGANT Rust Backend — Build & Install Guide

The COGANT Rust workspace provides a high-performance backend for program
graph construction, state-space compilation, and GNN export. It ships as a
PyO3 extension module (`cogant._rust`) built from the `cogant-ffi` crate via
[maturin](https://www.maturin.rs/).

When the Rust extension is not installed the Python package transparently
falls back to the pure-Python implementation in `cogant.graph.builder`.
Callers that want the acceleration path should use `cogant.rust_backend`
rather than importing `cogant._rust` directly.

## 1. Install the Rust toolchain

Stable Rust 1.89 or newer is required: the workspace uses edition 2024, and
`uuid` 1.28 sets the 1.89 floor (PyO3 0.29 itself needs 1.83). Install via
[rustup](https://rustup.rs):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustc --version  # should print 1.89 or newer
cargo --version
```

On macOS you additionally need the Xcode Command Line Tools for the linker:

```bash
xcode-select --install
```

Key workspace dependencies: PyO3 0.29 (CPython 3.8–3.15), petgraph 0.8,
thiserror 2, uuid 1.28, serde 1.0, serde_json 1.0. The authoritative
requirements live in [`Cargo.toml`](Cargo.toml) under `[workspace.dependencies]`.

## 2. Install maturin into the COGANT venv

From the repository root (the directory that contains `pyproject.toml`):

```bash
uv sync                                          # creates .venv with Python deps
uv pip install 'maturin>=1,<2' pytest pytest-cov  # maturin is required for the build
```

`rust/cogant-ffi/pyproject.toml` requires `maturin>=1.0,<2.0`; the PyO3 0.29
build was verified with maturin 1.15.

## 3. Build the Rust workspace

Smoke-test the workspace before touching Python — this catches Rust errors
in isolation:

```bash
cd rust
cargo build --release
```

All eight crates should compile cleanly:

- `cogant-core` — stable IDs, kinds, roles, confidence, provenance
- `cogant-graph` — `ProgramGraph` built on `petgraph` (serde via `serde-1`)
- `cogant-translate` — rules that lower IR to program graphs
- `cogant-statespace` — POMDP-style state, observations, actions
- `cogant-store` — persistence helpers
- `cogant-trace` — dynamic trace analysis
- `cogant-gnn` — JSON / Markdown GNN emitters
- `cogant-ffi` — PyO3 bindings (cdylib + rlib)

The `rust/.cargo/config.toml` sets
`PYO3_USE_STABLE_ABI_FORWARD_COMPATIBILITY=1` so that builds against a Python
newer than PyO3 supports (above 3.15 for PyO3 0.29) fall back to the stable ABI
instead of failing. Cargo reads that file relative to the current directory, so
it applies to commands run inside `rust/`, not to `--manifest-path
rust/Cargo.toml` invocations from the package root. Plain `cargo build` /
`cargo test` link `cogant-ffi` against libpython; maturin enables the
`pyo3/extension-module` feature for the wheel build.

## 4. Build and install the Python extension module

From the `rust/cogant-ffi/` directory, run `maturin develop` to build the
extension, produce a wheel, and install it into the active virtualenv as
editable:

```bash
cd rust/cogant-ffi
/path/to/cogant/.venv/bin/python -m maturin develop --release
```

`rust/cogant-ffi/pyproject.toml` configures maturin to:

- name the distribution `cogant-rust`
- install the native module at `cogant._rust` (matching the `module-name`)
- enable the `pyo3/extension-module` feature (runtime-linked Python)
- use the parent `py/` tree as the Python source so the existing
  `py/cogant/` package is not overwritten

## 5. Verify the install

```bash
cd <repo root>
.venv/bin/python -c "
import cogant
print('rust available:', cogant._RUST_AVAILABLE)
print('rust version  :', cogant.__rust_version__)

from cogant.rust_backend import get_program_graph_impl, create_example_graph
Graph = get_program_graph_impl()
g = Graph()
g.add_node('function', 'main', 'mod.main', 'mod.py', 'Python', 1, 10)
print('node count    :', g.node_count())

demo = create_example_graph()
print('demo graph    :', demo)
"
```

Expected output:

```
rust available: True
rust version  : 0.1.0
node count    : 1
demo graph    : ProgramGraph(nodes=3, edges=2)
```

## 6. Run the test suite

```bash
.venv/bin/python -m pytest tests/unit/test_rust_backend.py -v --no-cov
.venv/bin/python -m pytest tests/ --no-header --no-cov -q
```

The `@pytest.mark.requires_rust` marker is registered in the project's
`pyproject.toml` under `[tool.pytest.ini_options]` — gated tests skip
gracefully on machines without the compiled extension.

## Troubleshooting

**`the configured Python version (3.x) is newer than PyO3's maximum supported
version (3.15)`** — PyO3 0.29 supports CPython up to 3.15. For a
newer interpreter, run cargo from inside `rust/` so `rust/.cargo/config.toml`
applies, or export `PYO3_USE_STABLE_ABI_FORWARD_COMPATIBILITY=1` for
`--manifest-path` invocations (cargo walks up from CWD to find
`.cargo/config.toml`).

**`No module named 'cogant._rust'`** — the wheel was not installed into the
venv you are currently using. Re-run `maturin develop --release` from
`rust/cogant-ffi/` while the target venv is active (either via
`source .venv/bin/activate` or by invoking
`/path/to/.venv/bin/python -m maturin`).

**`uv sync` removes cogant-rust** — `uv sync` only installs packages listed
in the workspace `pyproject.toml`, and `cogant-rust` lives outside that set.
After running `uv sync` re-run `maturin develop --release` to restore the
Rust extension.
