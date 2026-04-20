# Agents — rust/

## Owner
Infra Lead

## Responsibilities
- Rust performance-critical implementations
- FFI bindings to Python via PyO3
- Memory safety and performance optimization
- Cross-platform compatibility

## Coordination
- Provides fast implementations of graph, store, translate, statespace, trace, and GNN operations
- Python via cogant-ffi (COGANT_USE_RUST=1)
- Unified cargo workspace with 8 crates

## Crates
| Crate | Purpose |
|-------|---------|
| `cogant-core` | Core types: StableId, NodeKind, SemanticRole |
| `cogant-graph` | High-performance graph storage and queries (connected_components FFI) |
| `cogant-translate` | Rule engine and graph transformations |
| `cogant-statespace` | State space compilation |
| `cogant-store` | Persistent storage and indexing |
| `cogant-trace` | Trace collection and processing |
| `cogant-gnn` | GNN tensor generation |
| `cogant-ffi` | Python bindings via PyO3 (extension module `_rust`) |

## Files
- `Cargo.toml` (workspace) — Workspace manifest and shared dependencies
- `cogant-core/` through `cogant-ffi/` — 8 crate directories
