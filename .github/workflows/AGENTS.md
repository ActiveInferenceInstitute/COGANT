# AGENTS.md — `.github/workflows`

GitHub Actions workflows for `ActiveInferenceInstitute/COGANT`. All Python steps run
through `uv run` so CI matches local development.

## Workflow inventory

| File | Trigger(s) | Jobs | Purpose |
|------|-----------|------|---------|
| [`ci.yml`](ci.yml) | `push` to `main`/`feat/**`/`fix/**`, `pull_request`, `workflow_dispatch` | `lint`, `typecheck`, `test (3.11/3.12/3.13/3.14)`, `rust-build`, `clean-wheel`, `gnn conformance (pinned)`, `pre-commit` | Primary quality gate. Ruff (no-fix; `--output-format=github`), `ruff format --check`, `mypy --strict`, the full pytest matrix, Cargo fmt/check/test/clippy, a clean-wheel install smoke, the pinned upstream GNN conformance lane (`gnn conformance (pinned)`), and a `pre-commit run --all-files` pass. Coverage gate is `--cov-fail-under=89` on 3.11 only. |
| [`metrics.yml`](metrics.yml) | `push`/`pull_request` to `main` | `metrics` | Regenerate `cogant/evaluation/METRICS.yaml` against the live tree and refuse to merge if any structural field drifted (env-dependent fields like `generated_at`, `test_count_*`, `suite_runtime_s`, and `coverage_percent` are tolerated via `git diff -I`). |
| [`metrics-fresh.yml`](metrics-fresh.yml) | `pull_request` | `check-metrics` | Fast out-of-syncness gate — verifies `METRICS.yaml` was regenerated against the PR's HEAD. Runs `tools/check_metrics_fresh.py`. |
| [`docs.yml`](docs.yml) | `push` to `main` (paths `cogant/docs/**`, `cogant/mkdocs.yml`, `cogant/py/**`); `workflow_run: [CI] completed`; `workflow_dispatch` | `deploy` | `mkdocs build` + GitHub Pages deploy via `peaceiris/actions-gh-pages`. Only deploys when CI is green. |
| [`perf-smoke.yml`](perf-smoke.yml) | `schedule: 0 6 * * 1` (Mondays 06:00 UTC); `workflow_dispatch` | `perf` | Weekly graph-build benchmark; uploads `perf_results.txt` for 90 days. |

## Runtime versions

Every action is pinned to a full commit SHA whose trailing comment names the
resolved release. All of them run on **Node 24** (the mandatory runtime starting
2026-06-02):

| Action | Pin | Notes |
|--------|-----|-------|
| `actions/checkout` | `v7.0.1` (`3d3c42e5aac5ba805825da76410c181273ba90b1`) | Node 24. v7 refuses fork-PR code under `pull_request_target`/`workflow_run` unless `allow-unsafe-pr-checkout: true`; the guard only fires for a custom `repository`/`ref`, and every checkout here is the default self-checkout. Credentials are stored under `$RUNNER_TEMP` since v6; every job sets `persist-credentials: false` because all git calls are local. |
| `actions/setup-python` | `v7.1.0` (`6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`) | Node 24. v7 is an internal ESM migration; inputs unchanged. |
| `actions/cache` | `v6.1.0` (`55cc8345863c7cc4c66a329aec7e433d2d1c52a9`) | Node 24. v6 is an internal ESM migration; inputs unchanged. |
| `actions/upload-artifact` | `v7.0.2` (`cf430e030ddbb5b0abf93d22962f4752f3646cd9`) | Node 24 since v6 (v5 still ran on Node 20). v7 adds an opt-in `archive: false`; the zipped default is unchanged. |
| `astral-sh/setup-uv` | `v10.3.3` (`68559e99cc807c1eb7e9238fd43a15bba460eec2`) | The SHA is the stable reference form here: Astral publishes no floating major tag for this action. v9 changed the `prune-cache` default to `false`, so every cached step sets `prune-cache: true` to keep the old behaviour. v10's `enable-cache: auto` skips the cache on `release`, tag push, `pull_request_target` and `workflow_run` events (so the `docs` job's `workflow_run` runs are uncached); jobs that set `enable-cache: true` are unaffected. |
| `dtolnay/rust-toolchain` | `stable` branch tip `b725eda525362e7cf34af9a7243cac1e3f01a7ec` | Replacement for the immutable `actions-rs/toolchain`. The action's `toolchain` input defaults to `stable` in this revision, so pinning the ref does not change which toolchain is installed. |
| `peaceiris/actions-gh-pages` | `v4.1.0` (`84c30a85c19949d7eee79c4ff27748b70285e453`) | Runs on Node 24, so the former `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` override was removed. |
| `actions/upload-pages-artifact` | `v5.0.0` (`fc324d3547104276b827a68afc52ff2a11cc49c9`) | Only used by the package-root template workflow [`../../cogant/.github/workflows/docs.yml`](../../cogant/.github/workflows/docs.yml). |
| `actions/deploy-pages` | `v5.0.1` (`368f82528645a54fb793d4d04e342629a3f51346`) | Only used by the same package-root template workflow. |

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
