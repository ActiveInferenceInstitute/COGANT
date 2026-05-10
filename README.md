# COGANT (staging)

Codebase-to-GNN translation — **package** under [`cogant/`](cogant/), **manuscript** under [`manuscript/`](manuscript/). This directory is staged in `projects_in_progress/` until moved to [`projects/cogant/`](../cogant/) ([`PROMOTION.md`](PROMOTION.md)).

## Manuscript variables (madlib)

1. Regenerate metrics (from package root [`cogant/`](cogant/)): `uv run python ../tools/regenerate_metrics.py`
2. Generate JSON + injected manuscript (from repo root):
   `uv run python projects_in_progress/cogant/scripts/z_generate_manuscript_variables.py`
3. Validate:
   `uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/manuscript/`
   `uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/output/manuscript/`

**Coverage table (Section 6.4, `{#tbl:coverage-stmt-modules}`).** Per-module `Stmts` / `Cover` rows in [`manuscript/06_04_tests_mutation_and_benchmarks.md`](manuscript/06_04_tests_mutation_and_benchmarks.md) are hand-copied from `coverage report`. After `uv run pytest tests/ --cov=cogant` in [`cogant/`](cogant/) (inner package root), run `uv run python ../tools/check_coverage_table.py` from the repo root (or `uv run python tools/check_coverage_table.py` from this staging folder) to compare the table to the report; use `--strict` to fail on drift. See [`manuscript/AGENTS.md`](manuscript/AGENTS.md) and [`PROMOTION.md`](PROMOTION.md).

Rendering uses `output/manuscript/` when present (see `infrastructure/rendering/pipeline.py`). Full pipeline PDF requires promotion and `scripts/03_render_pdf.py --project cogant`.

## Batch outputs (`run_all`)

Configurable orchestration at the staging root (same level as this file):

- **`run_all.sh`** — resolves the staging root (works from here or from inner [`cogant/`](cogant/)), then `cd` into the inner package and `uv run python ../run_all.py`
- **`run_all.py`** — reads **`run_all.json`** (optional; else built-in defaults), runs `cogant translate` → `scan`/`graph` → `export-gnn` → `render` → `viz` → **`validate`** (full GNN package + upstream `src.gnn` unless disabled in config) per target
- **`run_all.example.json`** — copy to `run_all.json` and set `targets` / `steps`

**Per-target output folders:** everything for one run goes under **`<output_root>/<target_id>/`** (`data/bundle.json`, `gnn_package/`, `site/`, `figures/` PNGs, `diagrams/`, `analysis/`, `exports/`, `roundtrip/`, `reports/run_summary.md`). The shipped [`run_all.json`](run_all.json) sets `output_root: "cogant/output"`, so real runs land at `cogant/output/<target_id>/`; the minimal [`run_all.example.json`](run_all.example.json) defaults to `output_root: "output"` (staging-root-relative) for quick smoke tests. A **`run_manifest.json`** in `output/` records top-level metadata (`started_at`, `staging_root`, `package_root`, `output_root`, `dry_run`) and a **`targets`** array: each entry has `id`, `run_dir`, `commands` (list of `{cmd, exit}`), and for `path`/`git_url` targets the fields described in `run_all.py` (`path`, `absolute_target`, `git_url`, `source_dir`, …). **`summary`** includes `total_wall_time_s`, `target_count`, and `failed_steps` (step labels when a non-zero exit was recorded). A cross-target **`output/summary.md`** + **`output/summary.json`** is written at the end with real per-target counts (nodes, edges, mappings), score, GNN-package file count, and presence flags for each layout subdirectory.

**Logging:** `+` command lines go to stdout (or append to `--log`); timestamped `[run_all …]` lines go to stderr (and duplicate to `--log` when set). Each target prints a `=== target …` banner before work (including `git clone` for remotes). Non-dry runs record per-step wall time and exit status; failed captured commands append an output tail. Use `./run_all.sh --dry-run` to list commands without executing.

**Defaults (no `run_all.json`):** all three shipped [`examples/control_positive/`](cogant/examples/control_positive/) fixtures (`calculator`, `event_pipeline`, `flask_mini`) plus two small public repos cloned with shallow `git` into **`output/<id>/_git_source/`** (`remote_itsdangerous`, `remote_markupsafe`). Set `"remote": { "refresh": true }` in JSON to delete and re-clone; `"git_ref"` optional per target.

Optional `manuscript.enabled` runs `scripts/z_generate_manuscript_variables.py` into `output/` (variables + injected manuscript), not under per-target run directories.

```bash
chmod +x run_all.sh
./run_all.sh --dry-run
./run_all.sh
```

Equivalent: `cd cogant && uv run python ../run_all.py --config ../run_all.json`

## Setup — eval submodules

Quantitative benchmarks under [`cogant/evaluation/`](cogant/evaluation/) read 12 third-party Python repositories vendored as git submodules under [`cogant/evaluation/eval_repos/`](cogant/evaluation/eval_repos/). Fresh clones leave them empty; populate them with either of:

```bash
git clone --recurse-submodules https://github.com/docxology/cogant.git
# or, for an existing clone:
git submodule update --init --recursive cogant/evaluation/eval_repos
```

Empty checkouts make benchmarks skip rather than fail, so this step is only required when running the evaluation pipeline. See [`cogant/evaluation/eval_repos/AGENTS.md`](cogant/evaluation/eval_repos/AGENTS.md) for per-submodule details.

## See also

- [`manuscript/README.md`](manuscript/README.md) — section index and validation commands
- [`cogant/README.md`](cogant/README.md) — package overview
- [`cogant/CONTRIBUTING.md`](cogant/CONTRIBUTING.md) — contribution guidelines and development setup
- Package tests and coverage policy: `cogant/pyproject.toml` (`pytest` defaults, `[tool.coverage.*]`)
