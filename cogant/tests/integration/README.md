# Integration Tests

End-to-end and cross-module integration tests.

## Structure

```
tests/integration/
├── test_pipeline.py
├── test_multi_language.py
├── test_export_formats.py
└── fixtures/
    ├── python_service/
    ├── rust_library/
    └── mixed_project/
```

## Running integration tests

```bash
pytest tests/integration -v
pytest tests/integration/test_pipeline.py::test_full_pipeline
```

## Test scenarios
- Full pipeline (ingest → export) on fixture repos
- Multi-language projects
- Export format consistency
- Validation and error handling
- Configuration overrides

## Fixtures
Small example repositories in fixtures/:
- python_service/ — Python service for testing
- rust_library/ — Rust library for testing
- mixed_project/ — Multi-language project
