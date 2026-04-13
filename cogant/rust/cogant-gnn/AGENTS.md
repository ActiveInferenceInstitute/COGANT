# Agents — rust/cogant-gnn

## Owner
GNN Lead

## Responsibilities
- High-performance tensor generation for GNNs
- Feature matrix and edge index computation
- Multi-relation graph flattening
- PyArrow interop for zero-copy export

## Coordination
- Consumes graphs from cogant-graph
- Outputs tensors and tables to Python gnn/
- Direct PyArrow/polars interop

## Files
- Cargo.toml — Crate manifest
- src/lib.rs — TensorGenerator, feature extraction
