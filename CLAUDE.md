# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository shape (the two `cogant/` directories will confuse you)

This directory is a **staging tree** under the outer template's `projects_in_progress/`. It is **not yet** discovered by `infrastructure/project/discovery.py` (see `PROMOTION.md` for the `git mv` to `projects/cogant/`). Two nested `cogant/` paths exist and mean different things:

- `projects_in_progress/cogant/` — staging root (this file's directory). Holds `manuscript/`, `tools/`, `scripts/`, `output/`, and thin `src/README.md` / `tests/README.md` pointers.
- `projects_in_progress/cogant/cogant/` — the **actual COGANT Python+Rust package** (`py/cogant/`, `rust/`, `tests/`, `docs/`, `pyproject.toml`, `Makefile`). Import name is `cogant`; sources live under `py/` (`[tool.setuptools] package-dir = {"" = "py"}`).
- The package's own `src/` stub (`cogant/src/README.md`) only documents the `py/cogant/` mapping — do **not** create code there.

When the parent template's `CLAUDE.md` talks about `projects/{name}/src/`, that convention does **not** apply here: COGANT keeps the nested package at `cogant/py/cogant/` and the staging root only holds manuscript-related infrastructure.

## What COGANT is

Codebase-to-GNN translation engine: ingests Python / JS / TS source, builds a `ProgramGraph` (typed nodes + edges), runs a **fixpoint engine with 22 declarative translation rules** to produce `SemanticMappings` (HIDDEN_STATE / OBSERVATION / ACTION / POLICY / ...), compiles those into an Active Inference state space, and emits a GNN markdown bundle with A/B/C/D matrices plus an AII validator score. A reverse path (`py/cogant/reverse/`) synthesizes a runnable Python package from a GNN bundle; `cogant roundtrip` closes the forward–reverse–forward loop. See `cogant/README.md` for the full architecture diagram and CLI surface (24 Typer subcommands registered in `py/cogant/cli/main.py`).

## Commands

### Package development (run from `cogant/` — the inner package root)

```bash
uv sync --extra all                              # python + viz + tree-sitter + rust deps
uv run cogant doctor                             # environment diagnostics (python, uv, tree-sitter, rust, disk)
uv run pytest tests/ -q                          # full suite (~2129 passing; 75% cov gate in pyproject.toml)
uv run pytest tests/unit/test_engine.py::test_name -v   # single test
uv run pytest -m property                        # hypothesis law tests (markers: unit, integration, slow, requires_rust, fuzz, property)
uv run mypy py/cogant/                           # strict mypy (0 errors across ~179 files is the target)
uv run ruff check py/cogant/                     # 0 errors on v0.5.0
make build-rust                                  # optional; cd rust && cargo build --release
```

`make lint` / `make type-check` only target `py/cogant/api` (focused gate); use `make lint-all` or `uv run ruff check py/cogant tests examples` for the full tree. The `cogant` CLI entry point is `cogant.cli.main:app`.

Test discovery is anchored in the package `pyproject.toml`: `testpaths = ["tests"]`, so pytest must be invoked from `cogant/` (not from the staging root). Coverage configuration is parallel-mode (`[tool.coverage.run] parallel = true`) with `--cov-fail-under=75`.

### Optional Rust acceleration

PyO3 bindings for graph `connected_components` live under `cogant/rust/` (workspace with `cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-ffi`, etc.). Gated by `COGANT_USE_RUST=1`; pure-Python fallback is the default. Build with `make build-rust` or `cd cogant/rust && cargo build --release`.

### Manuscript variable injection (run from repo root)

Manuscript Markdown uses `{{PLACEHOLDER}}` tokens resolved against `cogant/evaluation/METRICS.yaml`. The pipeline is three steps:

```bash
# 1. Regenerate METRICS.yaml — run from the package root (cogant/)
cd projects_in_progress/cogant/cogant && uv run python ../tools/regenerate_metrics.py

# 2. Generate the flat JSON + the injected output/manuscript/ tree (run from REPO root)
uv run python projects_in_progress/cogant/scripts/z_generate_manuscript_variables.py

# 3. Validate templates and the injected copy
uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/manuscript/
uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/output/manuscript/
```

Outputs land at `projects_in_progress/cogant/output/data/manuscript_variables.json` and `projects_in_progress/cogant/output/manuscript/*.md`. The template renderer (`infrastructure/rendering/pipeline.py`) prefers `output/manuscript/` when it exists, so full PDF rendering via `scripts/03_render_pdf.py --project cogant` only works **after** promotion to `projects/cogant/`.

Tool surface (`tools/`):
- `manuscript_vars.py` — `MANUSCRIPT_VARS` registry, `resolve_path`, `format_value_for_path`, `build_flat_variables`, `substitute_text`.
- `inject_manuscript_vars.py` — CLI to substitute a single file or directory; `--dry-run` and `--report` supported.
- `regenerate_metrics.py` — rebuilds `cogant/evaluation/METRICS.yaml` (authoritative ground truth for all prose numbers).
- `audit_manuscript_numbers.py`, `check_metrics_fresh.py` — sanity checks against drift between prose and metrics.

## Architecture landmarks inside `cogant/py/cogant/`

The package is a forward pipeline with a reverse synthesis arm. Key module groups (each ships a `.pyi` stub and `py.typed`):

- `ingest/`, `parsers/`, `static/`, `dynamic/` — language front ends (CPython `ast` for Python, `tree-sitter` for JS/TS with a JS-grammar fallback for `.ts`) and symbol / coverage extraction.
- `graph/` — `ProgramGraph` construction (typed nodes and edges: READS, WRITES, CONSTRAINT, CONFIGURATION, ...).
- `translate/` — fixpoint engine (`translate/engine.py`) plus 22 declarative rules under `translate/rules/` in five families (structural / semantic / control / behavioral / resilience; 5+5+3+4+5). Mutation-tested by `mutmut` on `engine.py` and `markov/blanket.py`.
- `markov/` — Markov blanket partition (`O(V+E)`, five seed strategies: `auto`, `module`, `class`, `subgraph`, `manual`).
- `statespace/` — compiles `SemanticMappings` into hidden states, observations, actions, transitions, and policies.
- `gnn/`, `export/` — AII-spec-compliant GNN markdown bundle emission (A/B/C/D matrices derived from edge kinds; **not** keyword heuristics).
- `reverse/` — `PackagePlan`-based synthesis of a runnable Python package from a GNN bundle; drives `cogant reverse` and `cogant roundtrip`. v0.5.0 fixed POLICY / CONTEXT stub emission to attain 23/23 ISOMORPHIC on the canonical roundtrip eval.
- `runtime/` — `AgentRuntime` with `run_episode`, `run_multi_episode`, `update_D_from_posterior`, `update_A_from_counts` (multi-episode Bayesian learning).
- `server/` — FastAPI app (`cogant.server.app`) with 12 routes: `/health`, `/ready`, `/metrics`, `/analyze`, `/reverse`, `/roundtrip`, plus `/api/v1/` namespace (`rules`, `analyze`, `roundtrip`, `visualize`, `metrics`); packaged via `cogant/Dockerfile` and `docker-compose.yml` (EXPOSE 8080).
- `pipeline/` — `PipelineConfig` orchestrates the forward run. `PipelineConfig.incremental_since` (same as `cogant translate --incremental <git-ref>`) re-uses the previous run's `ProgramGraph` for unchanged paths; benchmarked at 19.6× no-change / 5.6× single-file on Flask.
- `cli/main.py` — Typer app registering the 24 subcommands documented in `cogant/README.md`. Ruff `B008` is intentionally suppressed here (Typer's `typer.Argument` / `typer.Option` defaults are the canonical idiom).
- `rust_backend.py` — thin Python wrapper over the compiled `_rust` extension when `COGANT_USE_RUST=1`; transparently falls back to pure Python otherwise.
- `validate/`, `scoring/` — AII validator that scores bundles 0–100 (all six shipped fixtures score 100/100).

Fixtures under `cogant/examples/` (e.g. `control_positive/calculator`, `event_pipeline`, `flask_mini`, `flask_app`, `requests_lib`, `json_stdlib`) are the ground truth for the forward pipeline; `examples/zoo/` drives the roundtrip evaluation. `cogant/evaluation/METRICS.yaml` is regenerated from these runs and is the single source of truth for every numeric claim in the manuscript.

## Known METRICS.yaml pitfall: `test_count_passing = 0`

`regenerate_metrics.py` shells out to pytest. If pytest cannot import the package (missing optional deps, bad `PYTHONPATH`, or the script is run from the wrong directory), it may collect tests but fail to execute any, leaving `test_count_passing = 0`. **Before trusting the generated METRICS.yaml, check that `test_count_passing` is non-zero.** If it is zero despite `uv run pytest tests/ -q` passing locally, the regeneration environment is broken — re-run from inside `cogant/` with `uv run python ../tools/regenerate_metrics.py`.

Canonical v0.5.0 values: 2129 passing, 83.42% coverage. If the regenerated file contradicts these, trust the running test suite, not the file, until you identify what broke the regeneration run.

## Non-obvious conventions

- **Numbers in the manuscript are never hand-edited.** If a prose number looks stale, fix `METRICS.yaml` (via `regenerate_metrics.py`) and re-run `z_generate_manuscript_variables.py`; the injected `output/manuscript/` copy is disposable and will be overwritten.
- **`mypy --strict` with 0 errors is a hard invariant.** The package ships `.pyi` stubs and a `py.typed` marker; `tests/*` and a short list of third-party modules (`networkx`, `pyarrow`, `duckdb`, `typer`, `matplotlib`, `tree_sitter`, `numpy`, `cogant._rust`, `yaml`) are the only `ignore_missing_imports` overrides.
- **No-mocks policy inherited from the parent template.** Tests use real graphs, real fixtures under `examples/`, and real temp files — not `unittest.mock`. Hypothesis (`property`, `fuzz` markers) supplies generators for law-based tests.
- **Ruff `tests/**/*.py` E402 is intentional** — test files do `sys.path` manipulation before imports for the editable-install fallback.
- **Degraded outputs are explicit.** When the pipeline lacks evidence for a rule or matrix entry, it emits a validation finding plus a documented fallback (identity-biased A, identity-fallback B, uniform C/D) rather than silently guessing. See `cogant/docs/theory/active_inference.md § Known limitations`.
- **Docs are modular, not monolithic.** Per `cogant/docs/AGENTS.md`, the April 2026 refactor decoupled the 12 large root-level docs into `architecture/`, `reference/`, `evaluation/`, etc. Do not resurrect monolithic files; add new content as fragments inside the existing module directories. `cogant/docs/index.md` is the MkDocs home (no competing `README.md` beside it).
- **Link hygiene tooling lives in `cogant/docs/`:** `verify_doc_links.py` for `docs/` cross-links, `verify_manuscript_links.py` (run from the package root: `uv run python docs/verify_manuscript_links.py`) for manuscript links into the package tree. The manuscript validator skips `../../../` links because those target the parent template checkout.

## Before promotion to `projects/cogant/`

`PROMOTION.md` is authoritative. In brief: `git mv projects_in_progress/cogant projects/cogant`, fix any `projects_in_progress/cogant` literals in docs, then the three manuscript commands above plus `scripts/03_render_pdf.py --project cogant` will work end-to-end with the parent template's 10-stage pipeline. Until then, **this tree is invisible to `./run.sh` and `scripts/execute_pipeline.py`** — work on it via the package's own `uv` / `make` / `pytest` commands.
