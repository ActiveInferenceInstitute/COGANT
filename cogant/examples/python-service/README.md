# Python Service Example

Complete Python service demonstrating COGANT analysis on real code.

CLI reference: [docs/cli_reference.md](../../docs/cli_reference.md).

## Structure

```
python-service/
├── src/
│   ├── app.py           # Service entry + route registration
│   ├── config.py        # Environment/config loader
│   ├── events.py        # In-process event bus
│   └── models.py        # Data models
└── tests/
    └── test_app.py      # End-to-end smoke tests
```

## Analysis

From the repository root:

```bash
cogant translate examples/python-service --output output/python-service
```

Artifacts are written under `output/python-service/` (for example `program_graph.json`, `gnn_model.json` after export). For a bundle JSON suitable for `cogant validate` / `cogant render`, use the Python API (`Bundle.save_json`) or [example_pipeline.py](../example_pipeline.py).

Expected output: ~50 nodes (classes, functions), ~100 edges (calls, imports, uses)

## Demonstrates
- Class and function extraction
- Import tracking (internal and standard library)
- Call graph construction
- Type hints and inference
- Multi-file project handling
