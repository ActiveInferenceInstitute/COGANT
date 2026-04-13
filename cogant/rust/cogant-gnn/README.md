# cogant-gnn — GNN Tensor Generation

High-performance tensor generation for graph neural networks.

## Contents
- src/lib.rs — TensorGenerator, feature extraction, edge indexing

## Features
- Node feature matrix generation (embeddings, attributes)
- Edge index tensor (COO format)
- Edge weight assignment
- Multi-relation flattening
- PyArrow integration for zero-copy export
- GPU-ready tensor format

## Build

```bash
cargo build --release
cargo test
```

## Dependencies
- cogant-core, cogant-graph — Types and storage
- pyo3-polars — Arrow/Parquet export
- numpy — NumPy array interop

## Performance

100K nodes, 1M edges:
- Feature matrix: < 1s
- Edge indices: < 100ms
- Total export: < 2s
