# cogant-statespace — State Space Compilation (Rust stub)

Rust-side scaffolding for compiling control-flow models into state spaces, used by `cogant-ffi`.

## Contents
- `src/lib.rs` — Types for state variables, observation modalities, and control-flow graph extraction

## Build

```bash
cargo build --release
cargo test
```

## Dependencies

`[dependencies]` in `Cargo.toml`:

- `cogant-core` — Shared types
- `serde`, `serde_json` — Serialization
- `uuid`, `thiserror` — Identifier generation and error types

No `petgraph` and no `bitvec` — the crate is currently a thin scaffold; the authoritative state-space compiler is in [`py/cogant/statespace/`](../../py/cogant/statespace/). Bit-packed representations and graph-algorithm imports will be added only when their pure-Python counterparts are ported.

## Scope and status

Rust-side state-space compilation is intentionally minimal at this stage. Reach for [`py/cogant/statespace/compiler.py`](../../py/cogant/statespace/compiler.py) for behaviour changes; sync this crate only when the Python API stabilizes.
