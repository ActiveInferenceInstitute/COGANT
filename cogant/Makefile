.PHONY: help install dev test lint format type-check build-rust clean docs coverage

help:
	@echo "COGANT Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install package and dependencies"
	@echo "  make dev           Install in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run full test suite"
	@echo "  make test-unit     Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make coverage      Generate coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run linting checks (ruff)"
	@echo "  make format        Auto-format code (ruff format)"
	@echo "  make type-check    Run type checking (mypy)"
	@echo ""
	@echo "Building:"
	@echo "  make build         Build Python package"
	@echo "  make build-rust    Build Rust components"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         Clean build artifacts"
	@echo "  make clean-cache   Clean pytest/mypy caches"
	@echo "  make docs          Generate documentation"

# Installation targets (prefer uv; pip remains for compatibility)
install:
	uv pip install -e ".[all]"

dev:
	uv pip install -e ".[dev,viz]"

# Testing targets
test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit -v -m unit

test-integration:
	uv run pytest tests/integration -v -m integration

coverage:
	uv run pytest tests/ --cov=py/cogant --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

# Code quality targets
# Focused lint (API + orchestration). Full-tree cleanup tracked separately.
lint:
	uv run ruff check py/cogant/api

lint-all:
	uv run ruff check py/cogant tests examples

format:
	uv run ruff format py/cogant tests examples

type-check:
	uv run mypy py/cogant/api

# Stage-list drift gate (TODO #4 durable fix) — enforces that every documented
# full-pipeline stage sequence (CLI docstring, docs/cli_reference.md, FAQ,
# quickstart, manuscript API section) matches ``cogant.pipeline.RUNNER_STAGES``.
audit-stages:
	cd .. && uv run python tools/audit_stage_list.py

# Metrics-freshness gate (RedTeam F19) — coverage drift, git SHA drift,
# AND roundtrip-status laundering check. Re-classifies every row of
# ``roundtrip_results.jsonl`` via the same ``_status()`` logic the
# regenerator uses and asserts the resulting count distribution matches
# what METRICS.yaml claims. Catches the keystone laundering failure
# mode where METRICS.yaml inherits a richer prior regen and the data
# file has since been stripped to non-native rows.
audit-metrics-fresh:
	cd .. && uv run python tools/check_metrics_fresh.py

# Coverage-table drift gate (RedTeam F10). Runs ``check_coverage_table.py``
# in strict mode against either ``.coverage`` SQLite (if present) or the
# committed ``coverage.json`` fallback (always present), and fails if any
# per-module Stmts/Cover row in ``@tbl:coverage-stmt-modules`` disagrees
# with the live data. Catches hand-edit drift on the per-module table
# that the prior gate could not enforce from a clean checkout.
audit-coverage-table:
	cd .. && uv run python tools/check_coverage_table.py --strict

# Building
build:
	uv build

build-rust:
	cd rust && cargo build --release

# Cleanup
clean: clean-cache
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf rust/target/

clean-cache:
	rm -rf .pytest_cache/ .mypy_cache/ htmlcov/
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

docs:
	@echo "Generating documentation..."
	@echo "Documentation should be built from docs/ directory"
	@echo "Update with your documentation system (Sphinx, MkDocs, etc.)"

# Development helpers
check: lint type-check test
	@echo "All checks passed!"

install-pre-commit:
	pip install pre-commit
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# CI/CD helpers
ci: install test lint type-check
	@echo "CI checks completed"

# Utility targets
show-config:
	@cat cogant.yaml

show-deps:
	@echo "Core dependencies:"
	@grep "^    \"" pyproject.toml | head -10

show-test-files:
	@find tests -name "test_*.py" -type f

show-example-repos:
	@find examples -name "*.py" -type f | sort
