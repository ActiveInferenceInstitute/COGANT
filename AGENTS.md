# AGENTS.md — `projects_in_progress/cogant/`

## Layout

| Path | Role |
|------|------|
| [`cogant/`](cogant/) | Nested COGANT package (`py/cogant/`, `tests/`, `pyproject.toml`, Rust crates, docs). **This is the installable package root.** |
| [`manuscript/`](manuscript/) | PDF/HTML manuscript templates with `{{PLACEHOLDER}}` substitution syntax. Source of truth for prose; never edit by hand any number that has a `{{...}}` token. |
| [`tools/`](tools/) | `MANUSCRIPT_VARS` registry, metrics regeneration CLI, inject CLI, audit helpers. |
| [`scripts/`](scripts/) | Thin orchestrators (`z_generate_manuscript_variables.py`). |
| [`run_all.py`](run_all.py), [`run_all.sh`](run_all.sh), [`run_all.example.json`](run_all.example.json) | Configurable batch run: `translate` + GNN exports + `render` + `viz` + `validate` per target. Targets are either `path` (under inner `cogant/`) or `git_url` (shallow clone to `output/runs/<id>/_git_source/`). Defaults: all three `examples/control_positive/*` fixtures plus two small Pallets repos. Copy `run_all.example.json` → `run_all.json`. Each target writes only under `output/runs/<id>/`. Stderr + optional `--log`: per-target banner, per-step wall time / exit status, batch `summary` in `run_manifest.json`. |
| [`output/`](output/) | Generated outputs — `data/manuscript_variables.json`, `output/manuscript/` injected copy (both disposable and regeneratable); `output/runs/` when using `run_all`. |
| [`src/`](src/) | Compatibility stub only; real package lives at `cogant/py/cogant/`. |
| [`tests/`](tests/) | Compatibility stub only; real suite lives at `cogant/tests/`. See [`tests/AGENTS.md`](tests/AGENTS.md). |
| [`PROMOTION.md`](PROMOTION.md) | Authoritative checklist: steps to `git mv` this tree into `projects/cogant/`. |
| [`CLAUDE.md`](CLAUDE.md) | Claude Code guidance: two-directory layout, commands, architecture landmarks, non-obvious conventions. |

## Two-directory structure (common confusion point)

Two paths named `cogant/` exist and mean different things:

```
projects_in_progress/cogant/          ← staging root (this file's directory)
  manuscript/                         ← manuscript templates
  tools/                              ← manuscript tooling
  scripts/                            ← thin orchestrators
  output/                             ← disposable generated outputs
  cogant/                             ← THE ACTUAL PYTHON+RUST PACKAGE
    py/cogant/                        ← import root (import cogant → here)
    tests/                            ← pytest suite (run from cogant/)
    rust/                             ← 8 PyO3 crates
    docs/                             ← MkDocs site
    evaluation/METRICS.yaml           ← SINGLE SOURCE OF TRUTH for all numbers
    pyproject.toml
    Makefile
```

When `CLAUDE.md` or any other doc says "run from `cogant/`" it means the **inner** `cogant/` (the package root), not the staging root.

## Key APIs (tools layer)

| Module | Key exports |
|--------|------------|
| `tools/manuscript_vars.py` | `MANUSCRIPT_VARS` registry (placeholder → YAML dotpath), `resolve_path`, `format_value_for_path`, `build_flat_variables`, `substitute_text`, `find_unresolved_placeholders` |
| `tools/inject_manuscript_vars.py` | CLI: substitute one file or directory; `--dry-run`, `--report`, `--strict` flags |
| `tools/regenerate_metrics.py` | Rebuilds `cogant/evaluation/METRICS.yaml` from live test + pipeline runs |
| `tools/audit_manuscript_numbers.py` | Checks all prose numbers against `METRICS.yaml`; flags drift |
| `tools/check_metrics_fresh.py` | Warns if `METRICS.yaml` is stale (mtime > 48 h) |
| `scripts/z_generate_manuscript_variables.py` | Thin orchestrator: YAML → JSON + full `output/manuscript/` tree |

## Manuscript pipeline (three commands)

```bash
# 1. Regenerate METRICS.yaml from live test + benchmark runs (run from inner cogant/)
cd projects_in_progress/cogant/cogant && uv run python ../tools/regenerate_metrics.py

# 2. Build manuscript_variables.json + output/manuscript/ (run from REPO root)
uv run python projects_in_progress/cogant/scripts/z_generate_manuscript_variables.py

# 3. Validate templates + injected copy (run from REPO root)
uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/manuscript/
uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/output/manuscript/
```

All `{{PLACEHOLDER}}` tokens in `manuscript/*.md` resolve against `cogant/evaluation/METRICS.yaml`
via the registry in `tools/manuscript_vars.py`. **Never hand-edit a number that has a `{{...}}`
token** — fix the METRICS.yaml source instead.

## Package development commands (run from `cogant/` — inner package root)

```bash
uv sync --extra all                                  # install everything
uv run cogant doctor                                 # verify environment
uv run pytest tests/ -q                              # full suite (see live count; coverage gate in cogant/pyproject.toml)
uv run pytest tests/unit/test_engine.py -v           # single test file
uv run pytest -m property                            # Hypothesis law tests
uv run mypy py/cogant/                               # strict mypy (target: 0 errors)
uv run ruff check py/cogant/                         # lint (target: 0 violations)
make build-rust                                      # optional: compile Rust backend
```

Test markers: `unit`, `integration`, `slow`, `requires_rust`, `fuzz`, `property`.

## Authoritative numbers

`cogant/evaluation/METRICS.yaml` is the single source of truth for every numeric claim in the
manuscript. If a prose number looks stale, regenerate and re-inject; never hand-edit.

**Live suite:** run `cd cogant && uv run pytest tests/ -q` from the inner package root; counts are
not duplicated here (they drift every commit).

**Coverage (package `pyproject.toml`):** `pytest-cov` measures `cogant` with `branch = false`
(line gate), `omit` for `py/cogant/tools/` and `py/cogant/static/treesitter_parser.py`,
and `--cov-fail-under=89` (computed total is typically ~89.9%; the text report rounds to 90%).

Canonical benchmark-style figures still in `METRICS.yaml` (roundtrip, etc.) — refresh via
`regenerate_metrics.py` when changing fixtures or thresholds.

## Promotion checklist

`PROMOTION.md` is authoritative. In brief:
1. `git mv projects_in_progress/cogant projects/cogant`
2. Fix `projects_in_progress/cogant` literals in docs
3. Run the three manuscript commands above
4. Run `scripts/03_render_pdf.py --project cogant` for PDF generation

Until promoted, this tree is **invisible to `./run.sh`** and the infrastructure pipeline; work
via the package's own `uv` / `make` / `pytest` commands.

## Discovery

Not in `discover_projects()` until promoted; see [`PROMOTION.md`](PROMOTION.md).
