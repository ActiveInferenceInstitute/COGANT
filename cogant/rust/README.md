# Rust — Optional Acceleration Workspace

PyO3-based Rust workspace that ships optional acceleration for COGANT. The pure-Python package is the authoritative implementation; these crates exist to offload hot paths once benchmarks justify the port.

## Workspace members (8 crates)
- **cogant-core/** — Shared types (`StableId`, `NodeKind`, `EdgeKind`, `Confidence`, `Provenance`, `SemanticRole`)
- **cogant-graph/** — In-memory `ProgramGraph` + `connected_components` helper
- **cogant-translate/** — Rust-side rule engine scaffold (not yet at parity with Python rules)
- **cogant-statespace/** — State-space compilation scaffold
- **cogant-store/** — In-memory store scaffold (no on-disk backend yet)
- **cogant-trace/** — Trace record scaffold (no collection pipeline yet)
- **cogant-gnn/** — `format_json` / `format_markdown` helpers consumed by the FFI
- **cogant-ffi/** — PyO3 `cdylib` compiled as `_rust` (imports via `cogant._rust`)
- `Cargo.toml` (workspace) — Shared versions for `serde`, `serde_json`, `petgraph`, `pyo3`, `uuid`, `thiserror`, `anyhow`, `tracing`, `tracing-subscriber`, `tokio`

## Build

```bash
cd rust
cargo build --release
cargo test
```

From the package root ([`..`](../)), `make build-rust` invokes `maturin develop` against `cogant-ffi` to produce `py/cogant/_rust.*.so`. Set `COGANT_USE_RUST=1` in the environment to route the supported hot paths through Rust; without it the Python fallbacks remain active.

## Workspace dependencies

`[workspace.dependencies]` in `Cargo.toml`:

- `serde`, `serde_json` — Serialization
- `petgraph` — Graph primitives (used by `cogant-graph` and `cogant-ffi`)
- `pyo3` (extension-module feature) — Python bindings (`cogant-ffi` only)
- `uuid`, `thiserror`, `anyhow` — Identifiers and error types
- `tracing`, `tracing-subscriber` — Diagnostics
- `tokio` — Async runtime reserved for future async tasks

No `rayon`, no `dashmap`, no `pyo3-polars` — add these only when a crate actually imports them and the usage is tied to a checked-in benchmark.

## Documentation

Per-crate `README.md` and `AGENTS.md` describe the actual Cargo dependencies and current scope. When a crate grows its dependency list or API, update **both** files in lockstep with `Cargo.toml`.

See [`RUST_SETUP.md`](RUST_SETUP.md) for step-by-step build instructions.
