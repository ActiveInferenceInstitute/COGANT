# Agents — rust/cogant-graph

## Owner
Infra Lead

## Responsibilities
- High-performance graph storage (adjacency lists, CSR)
- Graph queries and traversals (BFS, DFS, shortest path)
- Memory-efficient representation
- Parallelization of graph algorithms

## Coordination
- Consumes types from cogant-core
- Feeds to cogant-translate and cogant-statespace
- Provides results via cogant-ffi to Python

## Files
- Cargo.toml — Crate manifest
- src/lib.rs — GraphStorage, QueryEngine, algorithms
