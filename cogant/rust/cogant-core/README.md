# cogant-core — Core Types and Algorithms

Rust core types and fundamental algorithms for COGANT.

## Contents
- src/lib.rs — Module organization and public exports
- Core types: Node, Edge, Graph, Symbol, Span
- Algorithms: symbol table, caching, identity resolution

## Build

```bash
cargo build --release
cargo test
```

## Dependencies
- dashmap, parking_lot — Concurrent data structures
- serde — Serialization
- No external system dependencies

## Python FFI

Exported via cogant-ffi using PyO3.

## Performance characteristics

- O(1) symbol lookup (hashmap)
- O(n) node/edge iteration
- Zero-copy interop with Python via Arrow
