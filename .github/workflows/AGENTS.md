# Agents — .github/workflows

## Purpose

GitHub Actions workflows for this repository:

- `ci.yml` — tests and quality gates (`--cov-fail-under=75`; local dev uses 89 from `pyproject.toml`)
- `docs.yml` — documentation site or link checks as configured.
- `perf-smoke.yml` — performance smoke checks.
- `metrics-fresh.yml` — freshness check for `evaluation/METRICS.yaml`.
- `metrics.yml` — metrics regeneration.

## Coordination

Edit alongside [`../../cogant/docs/CI.md`](../../cogant/docs/CI.md). Prefer `uv run` for Python steps to match local dev.

**Note**: CI `cov-fail-under` (75) is intentionally lower than `pyproject.toml` (89) to avoid
flaky CI failures from partial test runs; full coverage is enforced locally.
