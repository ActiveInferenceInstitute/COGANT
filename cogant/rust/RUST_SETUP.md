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

Any recent stable Rust (>= 1.75) works. Install via [rustup](https://rustup.rs):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustc --version  # should print 1.75 or newer
cargo --version
```

On macOS you additionally need the Xcode Command Line Tools for the linker:

```bash
xcode-select --install
```

## 2. Install maturin into the COGANT venv

From the repository root (the directory that contains `pyproject.toml`):

```bash
uv sync                                   # creates .venv with Python deps
uv pip install maturin pytest pytest-cov  # maturin is required for the build
```

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

The `rust/.cargo/config.toml` sets `-undefined dynamic_lookup` on macOS and
`-Wl,--unresolved-symbols=ignore-all` on Linux so that `cargo build` can link
the `cogant-ffi` cdylib without a live Python runtime. Maturin sets the same
flags automatically; the config only affects plain `cargo build`.

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

**`Undefined symbols for architecture arm64` when running `cargo build`** —
The `rust/.cargo/config.toml` file is missing or cargo cannot see it. Make
sure you run `cargo build` from inside the `rust/` directory (cargo walks up
from CWD to find `.cargo/config.toml`).

**`No module named 'cogant._rust'`** — the wheel was not installed into the
venv you are currently using. Re-run `maturin develop --release` from
`rust/cogant-ffi/` while the target venv is active (either via
`source .venv/bin/activate` or by invoking
`/path/to/.venv/bin/python -m maturin`).

**`uv sync` removes cogant-rust** — `uv sync` only installs packages listed
in the workspace `pyproject.toml`, and `cogant-rust` lives outside that set.
After running `uv sync` re-run `maturin develop --release` to restore the
Rust extension.

**Maturin warnings about unused imports** — the warnings in `cogant-gnn`,
`cogant-store`, and `cogant-translate` are cosmetic and do not affect
functionality. They can be cleaned up with `cargo fix --lib -p <crate>`.
