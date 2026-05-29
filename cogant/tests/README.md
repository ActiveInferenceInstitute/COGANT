# Tests — Test Suite

Unit, integration, and golden tests for COGANT.

## Contents
- **unit/** — Unit tests for individual modules (including `test_viz_png_degraded_paths`, `test_organize_example_outputs`, `test_render_output_figures`)
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

Default `addopts` in `pyproject.toml` enable coverage with `--cov-fail-under=89` (line gate; reported total is typically ~90% on measured lines, omits `static/treesitter_parser.py`). When you run **a single test file** that does not execute enough of `cogant`, coverage can drop below the threshold and fail. Use:

```bash
uv run pytest tests/unit/test_foo.py --no-cov
```

Full-suite runs should omit `--no-cov` so CI and local defaults stay aligned.

## Naming Policy

Test files are named by subsystem and behavior, not by implementation campaign.
Use durable names such as `test_server_app_http_routes.py`,
`test_reverse_idempotency_contract.py`, or
`test_viz_png_degraded_paths.py`. Do not introduce campaign numbers, dated
batch tags, or opaque coverage-only suffixes. Branch tests that exist primarily
for coverage should still name the exercised behavior or error path.

Run the active naming audit from the staging root before large test additions:

```bash
uv run python tools/audit_test_names.py
```

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

## Test-isolation policy ("no mocks") — honest characterization

Many test-file docstrings advertise "real objects only — no mocks, no MagicMock."
This claim is **scoped**: the suite does not use `unittest.mock`,
`MagicMock`, `mocker.patch`, or any mocking framework that fabricates
return values for an interface. It *does* use `pytest`'s
`monkeypatch` fixture in ~400 places, almost entirely for two
purposes:

1. **Optional-feature flag flipping** — e.g. forcing
   `rust_backend.RUST_AVAILABLE = False` to exercise the Python
   fallback path under a test that runs on a host without the Rust
   extension built.
2. **Environment-variable injection** — setting `COGANT_USE_RUST=0/1`
   or `MPLBACKEND=Agg` for the duration of a single test.

Both uses are *real-state* toggles; they do not fabricate API return
values or generate synthetic data through a mock. They are still
mocking in the broad sense of "substituting a runtime value for the
duration of a test," so the test policy is more accurately:

> "No fabricated return values; no `unittest.mock.MagicMock`; no
> `mocker.patch` of method return values. Where a test needs to
> exercise a non-default branch of a real production path, the test
> uses `monkeypatch` to toggle the same flag the production code
> would read."

The shorthand "no mocks" in individual docstrings is correct against the
narrow `MagicMock` reading and inaccurate against the broad reading;
this policy paragraph is the source-of-record.

## Coverage policy

Configured in `pyproject.toml` (`[tool.coverage.run]`, `[tool.coverage.report]`):
- **Line gate**: `--cov-fail-under=89` (computed total is typically ~89.9–90.0%)
- **Branch**: `branch = false` (line-only gate)
- **Omit**: `cogant/static/treesitter_parser.py`
- Run `uv run pytest tests/ --cov=py/cogant --cov-report=term-missing` for a full report

## Dependencies
- pytest — test runner
- pytest-cov — coverage reporting
- conftest fixtures for common setup
