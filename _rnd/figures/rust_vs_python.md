# Rust vs Python Benchmark

Date: 2026-04-09
Author: COGANT engineering (Marcus Webb bench run, session P1.5)
Harness: `cogant/benchmarks/rust_vs_python.py`

## Build Status

| Component                    | Status |
|------------------------------|--------|
| `cargo build --release` (8 crates) | ok — all crates compile, warnings only |
| `maturin develop --release` (cogant-ffi) | ok — wheel built, installed editable |
| `cogant._rust` importable from Python | ok — `get_version() == "0.1.0"` |
| `cogant.rust_backend.RUST_AVAILABLE`  | `True` |
| `COGANT_USE_RUST=1` gating            | respected by `build_program_graph()` |

**Crates built (release):** `cogant-core`, `cogant-graph`, `cogant-translate`,
`cogant-statespace`, `cogant-store`, `cogant-trace`, `cogant-gnn`, `cogant-ffi`.
Final `cogant-ffi` build completed in **3.84s** (incremental after full
workspace compile).

**Fix applied this session:** `.cargo/config.toml` already contained the
correct macOS PyO3 linker flags
(`-C link-arg=-undefined -C link-arg=dynamic_lookup`), but they are only
discovered when `cargo` is invoked from inside `rust/` (config is searched
from the invocation cwd upward). Running `cargo build --manifest-path
rust/Cargo.toml` from the parent `cogant/` directory silently ignores them
and fails to link. Fix: invoke from `rust/` directly or export the flags
via `RUSTFLAGS`. Documented in `RUST_SETUP.md` follow-up.

## Machine

- rustc 1.94.0 (aarch64-apple-darwin, LLVM 21.1.8)
- CPython 3.12 via uv-managed venv
- Apple Silicon (arm64), macOS Darwin 25.4.0

## Pipeline under test

Core pipeline, LLM stages excluded:
`run_ingest -> run_static -> run_normalize -> run_graph -> run_translate`

3 samples per fixture after a single warm-up run on `calculator` (primes
Python imports, tree-sitter grammars, and the shared identity resolver).

## Speedup Results (best-of-3)

| Fixture       | Python (ms) | Rust (ms) | Nodes | Edges | Speedup |
|---------------|-------------|-----------|-------|-------|---------|
| calculator    |       34.0  |    31.7   |    12 |    25 |  1.07x  |
| flask_app     |       82.6  |    81.6   |    98 |   154 |  1.01x  |
| requests_lib  |       69.7  |    75.5   |    98 |   152 |  0.92x  |

Full samples (ms):

```
Python (COGANT_USE_RUST=0):
  calculator    [34.5, 34.0, 37.1]   mean 35.2
  flask_app     [82.6, 90.5, 84.1]   mean 85.7
  requests_lib  [74.4, 69.7, 75.5]   mean 73.2

Rust   (COGANT_USE_RUST=1):
  calculator    [33.6, 31.7, 33.4]   mean 32.9
  flask_app     [87.7, 81.6, 89.6]   mean 86.3
  requests_lib  [79.4, 75.5, 82.7]   mean 79.2
```

## Notes

### Why speedup is ~1x instead of 2-4x

The current `RustProgramGraphAdapter` in `py/cogant/rust_backend.py`
mirrors every Rust insertion with a **shadow Python store**:

```python
self._nodes[node_id] = node       # Python pydantic Node
self._rust_graph.add_node(...)    # mirror into Rust
```

Every node and edge is allocated twice (once as a pydantic `Node`/`Edge`
on the Python side, once as a `PyNodeData` in Rust). `finalize()` then
materialises a pure-Python `ProgramGraph` from the **Python** shadow, not
from the Rust graph. The Rust graph is effectively write-only in this
adapter: nothing downstream reads it.

This explains the measured numbers:

- **Raw node-only Rust benchmark** (from P1): **1.28x** faster
  (Rust `add_node` + build vs pure-Python builder, no adapter).
- **Full adapter with Python shadow store** (this run): **~1.00x**
  parity. The ~1.28x Rust gain on the insertion path is exactly
  cancelled by the additional FFI round-trip per node/edge and the
  duplicated pydantic allocation.
- **Target once edge ingest + finalize move into Rust FFI**: estimated
  **2-4x** on flask_app / requests_lib based on graph-backend literature
  (petgraph insertion + bulk FFI transfer).

### What the timings are actually measuring

The pipeline wall-clock is dominated by parsing (tree-sitter / AST walk)
and normalization, not by graph insertion. On `flask_app` the graph has
only 98 nodes + 154 edges — insertion is < 5% of the wall clock. Even a
hypothetical infinite speedup on graph construction would barely move
the needle on these fixtures.

The right next fixtures for a meaningful Rust-vs-Python benchmark are:

1. A repo with **thousands** of nodes (e.g. the cogant repo on itself,
   or CPython stdlib) where graph insertion dominates.
2. A **microbenchmark** that isolates `build_program_graph` from the
   parsing pipeline (already exists as the P1 node-only test showing
   1.28x).

### Decision

The adapter pattern as currently shipped gives us functional Rust
integration (`_rust` module loads, `COGANT_USE_RUST=1` gates work,
tests pass) but no speedup on the real-repo pipeline. For real speedup,
two things need to change:

1. **Move edge ingest into Rust FFI** — the adapter currently only
   forwards `add_node`; `add_edge` is Python-only.
2. **Skip the Python shadow store** — `finalize()` should convert the
   Rust graph directly into the output `ProgramGraph` (or the
   downstream consumers should accept the Rust handle). This is the
   larger change and needs a migration across `statespace/`,
   `translate/`, `export/`.

Deferred to **P1.6: edge-ingest FFI + shadow-store removal**.

## Reproducing

```bash
cd projects_in_progress/cogant/cogant

# Build Rust workspace (must be run from rust/ so .cargo/config.toml is found)
cd rust && cargo build --release && cd ..

# Install Python extension module
cd rust/cogant-ffi && maturin develop --release && cd ../..

# Run the benchmark
uv run python benchmarks/rust_vs_python.py
```

## References

- `_rnd/R&D_LOG.md` entry 2026-04-09 (P1.5)
- `cogant/benchmarks/rust_vs_python.py` (harness)
- `cogant/py/cogant/rust_backend.py` (adapter, gating, fallback)
- `cogant/rust/cogant-ffi/src/lib.rs` (PyO3 surface)
- `cogant/rust/.cargo/config.toml` (linker flags)
