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
- conftest.py — Pytest fixtures and configuration
- __init__.py — Test package marker
- test_engine.py — Pipeline integration tests
- unit/ — Unit tests per module
- integration/ — Cross-module integration tests
- golden/ — Golden test expectations and fixtures
