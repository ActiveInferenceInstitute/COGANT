# Tests — Test Suite

Unit, integration, and golden tests for COGANT.

## Contents
- **unit/** — Unit tests for individual modules (including `test_png_export`, `test_organize_example_outputs`, `test_render_output_figures`)
- **integration/** — Cross-module integration tests (`test_layout_output`, `test_full_pipeline`, …)
- **golden/** — Golden test fixtures and expected outputs
- conftest.py — Pytest configuration and fixtures
- test_engine.py — Pipeline end-to-end tests

Some integration cases in `test_full_pipeline.py` **skip** when the roundtrip does not emit the packaged GNN directory, execution trace, or populated `state_space` (optional orchestrator outputs).

## Running tests

```bash
pytest tests/unit -v
pytest tests/integration -v
pytest --cov=cogant --cov-report=html
```

## Golden tests

Golden tests compare output against saved "golden" expectations:
1. Run pipeline on fixture repository
2. Capture output (bundle, graph, validation report)
3. Compare against saved golden output
4. Update golden on intentional changes (requires review)

Location: tests/golden/
Files: *.json, *.yaml, *.md (golden expectations)

## Coverage targets
- Unit test coverage: ≥ 80%
- Integration test coverage: ≥ 60%
- Critical paths: ≥ 90%

## Dependencies
- pytest — test runner
- pytest-cov — coverage reporting
- conftest fixtures for common setup
