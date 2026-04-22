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

From the package root (`cogant/cogant/`, the directory that contains `py/` and `docs/`):

```bash
uv run pytest tests/ -q
uv run pytest tests/unit -v
uv run pytest tests/integration -v
```

Default `addopts` in `pyproject.toml` enable coverage with `--cov-fail-under=89` (line gate; reported total is typically ~90% on measured lines, omits `tools/` and `static/treesitter_parser.py`). When you run **a single test file** that does not execute enough of `cogant`, coverage can drop below the threshold and fail. Use:

```bash
uv run pytest tests/unit/test_foo.py --no-cov
```

Full-suite runs should omit `--no-cov` so CI and local defaults stay aligned.

## Golden tests

Golden tests compare output against saved "golden" expectations:
1. Run pipeline on fixture repository
2. Capture output (bundle, graph, validation report)
3. Compare against saved golden output
4. Update golden on intentional changes (requires review)

Location: `tests/golden/`
Layout:
- `tests/golden/roundtrip/*.json` — canonical forward-reverse-forward expectations (currently `04_pomdp_minimal.json`, `06_hierarchical.json`, `12_full_pomdp.json`)
- `tests/golden/test_bundle_json_schema.py` — schema-level golden assertions over generated bundles

## Coverage policy

Configured in `pyproject.toml` (`[tool.coverage.run]`, `[tool.coverage.report]`):
- **Line gate**: `--cov-fail-under=89` (computed total is typically ~89.9–90.0%)
- **Branch**: `branch = false` (line-only gate)
- **Omit**: `cogant/tools/`, `cogant/static/treesitter_parser.py`
- Run `uv run pytest tests/ --cov=cogant --cov-report=term-missing` for a full report

## Dependencies
- pytest — test runner
- pytest-cov — coverage reporting
- conftest fixtures for common setup
