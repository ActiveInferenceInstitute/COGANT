# Agents — tests/

## Owner
Infra Lead

## Responsibilities
- Test suite design and coverage targets
- CI/CD pipeline and test execution
- Golden test management and expectations
- Performance benchmarking and regression detection

## Coordination
- Unit tests maintained by subsystem owners
- Integration tests for cross-module workflows
- All leads contribute tests for their modules

## Files
- README.md — How to run the suite (`uv run pytest tests/` from `cogant/cogant/`); use `--no-cov` for narrow single-file runs when coverage thresholds fail
- conftest.py — Pytest fixtures and configuration
- __init__.py — Test package marker
- test_engine.py — Pipeline integration tests
- unit/ — Unit tests per module (includes `test_bundle_site_cov.py` for `viz/bundle_site`, `test_verify_doc_links.py` for `docs/verify_doc_links.py`)
- integration/ — Cross-module integration tests
- golden/ — Golden test expectations and fixtures
- fuzz/ — Fuzz-adjacent tests
- property/ — Hypothesis property tests
