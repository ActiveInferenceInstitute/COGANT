# cogant-statespace — State Space Compilation

Fast state space extraction and compilation for control-flow models.

## Contents
- src/lib.rs — StateSpaceCompiler, temporal reasoning, abstraction

## Features
- Control-flow graph extraction (quadratic time bound)
- Variable domain inference
- State predicate compilation
- Temporal causality analysis

## Build

```bash
cargo build --release
cargo test
```

## Dependencies
- cogant-core, cogant-graph — Types and storage
- petgraph — Graph algorithms
- bitvec — Bit-packed state sets

## Performance

100K-node graph to state space: < 5s
