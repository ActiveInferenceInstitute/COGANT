# AGENTS.md — `.github/workflows`

GitHub Actions workflows for `ActiveInferenceInstitute/COGANT`. All Python steps run
through `uv run` so CI matches local development.

## Workflow inventory

| File | Trigger(s) | Jobs | Purpose |
|------|-----------|------|---------|
| [`ci.yml`](ci.yml) | `push` to `main`/`feat/**`/`fix/**`, `pull_request`, `workflow_dispatch` | `lint`, `typecheck`, `test (3.11/3.12/3.13)`, `rust-build`, `clean-wheel`, `upstream-smoke` (manual dispatch only), `pre-commit` | Primary quality gate. Ruff (no-fix; `--output-format=github`), `ruff format --check`, `mypy --strict`, the full pytest matrix, Cargo fmt/check/test/clippy, a clean-wheel install smoke, and a `pre-commit run --all-files` pass. Coverage gate is `--cov-fail-under=89` on 3.11 only. |
| [`metrics.yml`](metrics.yml) | `push`/`pull_request` to `main` | `metrics` | Regenerate `cogant/evaluation/METRICS.yaml` against the live tree and refuse to merge if any structural field drifted (env-dependent fields like `generated_at`, `test_count_*`, `suite_runtime_s`, and `coverage_percent` are tolerated via `git diff -I`). |
| [`metrics-fresh.yml`](metrics-fresh.yml) | `pull_request` | `check-metrics` | Fast out-of-syncness gate — verifies `METRICS.yaml` was regenerated against the PR's HEAD. Runs `tools/check_metrics_fresh.py`. |
| [`docs.yml`](docs.yml) | `push` to `main` (paths `cogant/docs/**`, `cogant/mkdocs.yml`, `cogant/py/**`); `workflow_run: [CI] completed`; `workflow_dispatch` | `deploy` | `mkdocs build` + GitHub Pages deploy via `peaceiris/actions-gh-pages`. Only deploys when CI is green. |
| [`perf-smoke.yml`](perf-smoke.yml) | `schedule: 0 6 * * 1` (Mondays 06:00 UTC); `workflow_dispatch` | `perf` | Weekly graph-build benchmark; uploads `perf_results.txt` for 90 days. |

## Runtime versions

All actions are pinned to current majors that run on **Node 24** (the
mandatory runtime starting 2026-06-02), with `setup-uv` pinned to a
specific immutable tag because Astral does not publish floating
major tags for that action:

| Action | Version | Notes |
|--------|---------|-------|
| `actions/checkout` | `@v7` | Node 24. v7 refuses fork-PR code under `pull_request_target`/`workflow_run` unless `allow-unsafe-pr-checkout: true`; the guard only fires for a custom `repository`/`ref`, and every checkout here is the default self-checkout. Credentials are stored under `$RUNNER_TEMP` since v6; every job sets `persist-credentials: false` because all git calls are local. |
| `actions/setup-python` | `@v7` | Node 24. v7 is an internal ESM migration; inputs unchanged. |
| `actions/cache` | `@v6` | Node 24. v6 is an internal ESM migration; inputs unchanged. |
| `actions/upload-artifact` | `@v7` | Node 24 since v6 (v5 still ran on Node 20). v7 adds an opt-in `archive: false`; the zipped default is unchanged. |
| `astral-sh/setup-uv` | `@v10.3.0` | Pinned (immutable tag); no `@v10` floating tag exists. v9 changed the `prune-cache` default to `false`, so every cached step sets `prune-cache: true` to keep the old behaviour. v10's `enable-cache: auto` skips the cache on `release`, tag push, `pull_request_target` and `workflow_run` events (so the `docs` job's `workflow_run` runs are uncached); jobs that set `enable-cache: true` are unaffected. |
| `dtolnay/rust-toolchain` | `@stable` | Branch-pinned by design; replacement for the immutable `actions-rs/toolchain`. |
| `peaceiris/actions-gh-pages` | `@v4` | Current major. `@v4` resolves to v4.1.0, which runs on Node 24, so the former `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` override was removed. |

The `pre-commit` job intentionally **does not** use
`pre-commit/action` — its latest release (v3.0.1) still bundles
`actions/cache@v4` (Node 20). The job pip-installs `pre-commit`
itself, primes a Node-24 `actions/cache@v6`, and runs
`pre-commit run --all-files --show-diff-on-failure` directly.

Every workflow declares a top-level `permissions: contents: read`
(only the `docs` deploy job widens it to `contents: write`) and every
job has a `timeout-minutes` cap sized at roughly twice its observed
runtime.

When bumping any of these, update this table, the dependent
`docs/CI.md` reference, and the package-root template workflow in
[`../../cogant/.github/workflows/docs.yml`](../../cogant/.github/workflows/docs.yml).

## Coordination

* Edit alongside [`../../cogant/docs/CI.md`](../../cogant/docs/CI.md)
  whenever job names, gates, or artefact paths change.
* The CI `cov-fail-under` (89, 3.11 leg only) matches the
  `pyproject.toml` `addopts` floor; the measured coverage recorded in
  `METRICS.yaml` sits above it to absorb run-to-run noise.
* `metrics-refresh` is the only workflow that may produce a "drift"
  diff for `METRICS.yaml`; if it fails, run `cd cogant && uv run python
  ../tools/regenerate_metrics.py` and commit the result. The
  `git diff -I` rules in `metrics.yml` document precisely which fields
  are tolerated.
