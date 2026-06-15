# AGENTS.md — `.github/workflows`

GitHub Actions workflows for `ActiveInferenceInstitute/COGANT`. All Python steps run
through `uv run` so CI matches local development.

## Workflow inventory

| File | Trigger(s) | Jobs | Purpose |
|------|-----------|------|---------|
| [`ci.yml`](ci.yml) | `push` to `main`/`feat/**`/`fix/**`, `pull_request`, `workflow_dispatch` | `lint`, `typecheck`, `test (3.11/3.12/3.13)`, `rust-build`, `pre-commit` | Primary quality gate. Ruff (no-fix; `--output-format=github`), `ruff format --check`, `mypy --strict`, the full pytest matrix, a Cargo `check` smoke, and a `pre-commit run --all-files` pass. Coverage gate is `--cov-fail-under=75` on 3.11 only. |
| [`metrics.yml`](metrics.yml) | `push`/`pull_request` to `main` | `metrics` | Regenerate `cogant/evaluation/METRICS.yaml` against the live tree and refuse to merge if any structural field drifted (env-dependent fields like `generated_at`, `test_count_*`, `suite_runtime_s`, and `coverage_percent` are tolerated via `git diff -I`). |
| [`metrics-fresh.yml`](metrics-fresh.yml) | `pull_request` | `check-metrics` | Fast out-of-syncness gate — verifies `METRICS.yaml` was regenerated against the PR's HEAD. Runs `tools/check_metrics_fresh.py`. |
| [`docs.yml`](docs.yml) | `push` to `main` (paths `cogant/docs/**`, `cogant/mkdocs.yml`, `cogant/py/**`); `workflow_run: [CI] completed`; `workflow_dispatch` | `deploy` | `mkdocs build` + GitHub Pages deploy via `peaceiris/actions-gh-pages`. Only deploys when CI is green. |
| [`perf-smoke.yml`](perf-smoke.yml) | `schedule: 0 6 * * 1` (Mondays 06:00 UTC); `workflow_dispatch` | `perf` | Weekly graph-build benchmark; uploads `perf_results.txt` for 90 days. |

## Runtime versions

All actions are pinned to majors that ship on **Node 24** (the
mandatory runtime starting 2026-06-02), with `setup-uv` pinned to a
specific immutable tag because Astral no longer publishes floating
major tags for that action:

| Action | Version | Notes |
|--------|---------|-------|
| `actions/checkout` | `@v5` | Node 24 since v5.0.0. |
| `actions/setup-python` | `@v6` | Node 24. |
| `actions/cache` | `@v5` | Node 24 since v5.0.0. |
| `actions/upload-artifact` | `@v5` | Node 24. |
| `astral-sh/setup-uv` | `@v8.1.0` | Pinned (immutable tag); `@v8` floating tag is intentionally unpublished. |
| `dtolnay/rust-toolchain` | `@stable` | Replacement for the immutable `actions-rs/toolchain`. |
| `peaceiris/actions-gh-pages` | `@v4` | Current major; the action's own runtime is still Node 20, so the `docs` job sets `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"` to opt in early. Drop that env once the action ships a Node 24 release (or migrate to `actions/deploy-pages`). |

The `pre-commit` job intentionally **does not** use
`pre-commit/action` — that action transitively bundles
`actions/cache@v4` (Node 20). The job pip-installs `pre-commit`
itself, primes a Node-24 `actions/cache@v5`, and runs
`pre-commit run --all-files --show-diff-on-failure` directly.

When bumping any of these, update this table and the dependent
`docs/CI.md` reference.

## Coordination

* Edit alongside [`../../cogant/docs/CI.md`](../../cogant/docs/CI.md)
  whenever job names, gates, or artefact paths change.
* The CI `cov-fail-under` (75) is **intentionally lower** than the local
  `pyproject.toml` default (89) so partial test runs on slow runners
  do not flake the CI gate; the higher number is enforced locally.
* `metrics-refresh` is the only workflow that may produce a "drift"
  diff for `METRICS.yaml`; if it fails, run `cd cogant && uv run python
  ../tools/regenerate_metrics.py` and commit the result. The
  `git diff -I` rules in `metrics.yml` document precisely which fields
  are tolerated.
