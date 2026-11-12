# Gate and CI run guide

`run_gate.py` at the COGANT project root is the single entry point for every
check. GitHub Actions jobs run the same arms, so a command exists in exactly
one place: this file describes what the gate runs, not a second copy of the
commands.

## Entry point

```bash
python run_gate.py --list                  # arms, their extras, one-line summaries
python run_gate.py lint                    # one arm
python run_gate.py lint types content docs # several arms, in order
python run_gate.py --prepare types         # one uv sync for the arm's extras, then run
python run_gate.py --dry-run test-full     # print the exact command
python run_gate.py                         # bare invocation: test-fast
python run_gate.py all                     # every arm
```

A bare invocation runs `test-fast`; `all` is explicit.

`--prepare` runs exactly one `uv sync` for the union of the selected arms'
extras. The arms themselves never install anything, never regenerate an
artifact they are supposed to check, and never run another arm's command.
`--keep-going` continues after a failure; by default the gate stops at the
first failing step so the first red check is the reported one.

Paths are anchored on `run_gate.py`, so the working directory does not matter.
CI invokes it from `cogant/` as `python ../run_gate.py ...`.

## Arms

| Arm | What it runs | Extras |
| --- | --- | --- |
| `lint` | `ruff check --no-fix` and `ruff format --check` over `py/cogant/` and `tests/` | `dev` |
| `types` | strict mypy over the installed package (viz interfaces installed) | `dev`, `viz` |
| `content` | repository fact gates: docs constants, folder docs, stage list, test names, manuscript module/math/link/robustness/coverage/figure checks, synthetic-surface classification | `dev` |
| `docs` | `mkdocs build --strict` plus `docs/verify_doc_links.py` | `dev` |
| `test-fast` | default test arm: `--no-cov`, `--ignore=tests/property/`, `-m "not slow"` | `all` |
| `test-property` | Hypothesis law tests (also collected by `test-full`) | `all` |
| `test-full` | full suite with the coverage gate (`--cov=cogant --cov-fail-under=89`) | `all` |
| `gnn` | pinned upstream conformance probe, four bridge/integration test files, release-integrity provenance audit | `upstream`, `dev` |
| `wheel` | `tools/wheel_smoke.py` clean-wheel build + isolated import smoke, then `audit_release_integrity.py --require-wheel --check-wheel-reproducibility` | `dev` |
| `rust` | `cargo fmt --check`, `check`, `test`, `clippy -D warnings` for `cogant/rust` | — |
| `manuscript` | inject variables, validate the figure registry, render the PDF, verify manuscript links | `dev` |

`test-property` is a diagnostic arm for iterating on Hypothesis failures. It is
not run separately in CI because `test-full` collects the property tree.

## CI mapping

| Workflow job (key / display) | Gate invocation |
| --- | --- |
| `static` / Static gates (lint, content, docs) | `python ../run_gate.py --prepare lint content docs` |
| `typecheck` / Typecheck (mypy) | `python ../run_gate.py --prepare types` |
| `test` / `test (3.11)` | `python ../run_gate.py --prepare test-full` |
| `test` / `test (3.12)`, `test (3.13)`, `test (3.14)` | `python ../run_gate.py --prepare test-fast` |
| `rust-build` / Rust backend checks | `python3 ../run_gate.py rust` |
| `clean-wheel` / Clean wheel install smoke | `python ../run_gate.py --prepare wheel` |
| `gnn-conformance` / gnn conformance (pinned) | `python ../run_gate.py --prepare gnn` |
| `pre-commit` / Pre-commit hooks | third-party file-hygiene hooks only; ruff is not a hook |

`pre-commit` is the one job that does not run a gate arm: it executes
third-party hygiene hooks (trailing whitespace, end-of-file, YAML syntax, large
files) that no arm covers. Ruff was removed from the hook set so the repository
has exactly one ruff invocation, `run_gate.py lint`.

## GNN conformance pin

- Pin file: [`.github/gnn-pin.json`](../.github/gnn-pin.json), schema
  `gnn-importer-pin/v1`, repository
  `ActiveInferenceInstitute/Generalized_Notation_Notation`, tag `v5.0.3`,
  commit `8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`.
- Workflow job: key `gnn-conformance`, display name
  `gnn conformance (pinned)`, in
  [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).
- Probe: [`cogant/scripts/gnn_conformance_probe.py`](../cogant/scripts/gnn_conformance_probe.py)
  emits a package from `cogant/examples/control_positive/calculator`, validates
  it at the `standard` and `strict` levels, and runs upstream steps 3, 5 and 6.
  What the job parses is recorded in [`.github/GNN.md`](../.github/GNN.md).
- The job installs the pin through the `upstream` extra in
  [`cogant/pyproject.toml`](../cogant/pyproject.toml); it does not read
  `gnn-pin.json`. `tools/audit_release_integrity.py --no-openapi` checks the
  installed pin against `cogant/uv.lock`.

The Python setup in every job uses the org composite action
`ActiveInferenceInstitute/.github/.github/actions/setup-python-uv@7159e67315330aac8e414aebae0ad1e999a41448`.

## Prerequisites for the non-Python arms

- `manuscript`: `pandoc`, `pandoc-crossref`, and a LaTeX engine
  (`xelatex`) on `PATH`, plus generated run artifacts. Missing figure sources
  fail the arm; generate them with `cd cogant && uv run python
  ../run_all.py --targets calculator,flask_app`, then re-run the arm.
- `gnn`: the `upstream` extra builds `h5py`, which needs the HDF5 system
  library on macOS/Python versions without a prebuilt wheel. CI uses Python
  3.12, where the wheel is available; on this host the arm can run under 3.12
  with `UV_PYTHON=3.12 UV_PROJECT_ENVIRONMENT=.venv-gnn`.
- `wheel`: network access for `uv build` dependencies and the isolated install.

## Measured wall time on the estate workstation

One run per arm, macOS arm64, 18 cores, Python 3.15.2 for the Python arms
(`gnn` under 3.12 because the `h5py` wheel for 3.15 is not published), warm uv
environment. The host load average during these runs was 25–34 from other
repositories' suites, so the absolute numbers are pessimistic; the relative
comparison still holds because every arm ran under the same conditions.

"Before" is the command as it stood in the workflow that owned it, measured
directly before the gate was introduced where the command changed. For arms
whose command is unchanged, one measurement serves both columns — the change is
where the command lives and how many times a job runs it.

| Arm | Before | After | Notes |
| --- | --- | --- | --- |
| `lint` | 0.22 s | 0.23 s | same two ruff commands |
| `types` | 5.15 s | 0.40 s | before cold `.mypy_cache`, after warm; a cold after-run is ~5 s |
| `content` | 7.19 s | 7.7 s | before also ran `check_metrics_fresh`, now owned by `metrics-fresh.yml` |
| `docs` | 17.9 s | 22.6 s | after adds `--strict` and the relative-link check |
| `test-fast` | same command | not run (bounded) | stopped after 25 min at ~2 % under host contention |
| `test-full` | same command | not run (bounded) | not started; same suite plus property and coverage |
| `gnn` | same three commands | 96.9 s | plus one `uv sync` (~110 s) on a fresh environment; probe moved from an inline workflow heredoc to `cogant/scripts/gnn_conformance_probe.py` |
| `rust` | same four commands | 24.8 s | warm `rust/target` |
| `wheel` | CI only (pip wheel + target install) | 13.6 s | now `tools/wheel_smoke.py` + the wheel-reproducibility audit |
| `manuscript` | n/a | 121.5 s | no repository-local render command existed before |

Job-level deduplication (the part that saves the most runner time):

- the 3.11 test leg ran the suite three times (fast, property, coverage); it now
  runs once (`test-full`), and the other legs run `test-fast` once each;
- lint, typecheck, and the documentation/content audits previously occupied
  four jobs with four checkouts and four `uv sync` runs; they now share one;
- ruff previously ran twice per pull request (the lint job and the
  `pre-commit` job); it now runs once.

### Test arms: bounded, not completed

`test-fast` and `test-full` were **not** run to completion. The host was running
six other repositories' suites (load average 34 on 18 cores); `test-fast`
reached ~2 % of 10,018 selected tests after 25 minutes with the pytest process
at 0 % CPU, so it was stopped under the estate's 10-minute-per-arm bound.
`test-full` was not started.

Bounded commands that were run:

```bash
cd cogant && uv run pytest tests/ --collect-only -q --no-cov
# 10,091 tests collected in 15.8 s

cd cogant && uv run pytest tests/integration/test_full_pipeline.py -q --no-cov -o addopts=
# 69 passed in 50.4 s (one file, not the arm)
```

Neither arm's command changed in this pass, so their correctness does not rest
on the refactor; what is unverified on this host is their wall time. Run
`python run_gate.py --prepare test-fast` and
`python run_gate.py --prepare test-full` on an idle host and replace this
section with the measured numbers.
