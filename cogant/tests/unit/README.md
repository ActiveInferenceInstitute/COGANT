# Unit Tests

Unit tests for individual COGANT modules.

## Structure

```
tests/unit/
├── test_ingest.py
├── test_graph.py
├── test_normalize.py
├── test_translate.py
├── test_export.py
├── test_validate.py
├── test_schemas.py
├── test_parsers.py
└── fixtures/
    ├── sample_python_file.py
    ├── sample_rust_file.rs
    └── test_manifests.yaml
```

## Running unit tests

```bash
pytest tests/unit -v
pytest tests/unit/test_graph.py::test_builder_add_node
```

## Test patterns
- Isolate each test with fixtures
- Mock external dependencies
- Use parametrize for multiple scenarios
- Test error cases and edge cases
- Aim for ≥ 80% coverage per module
