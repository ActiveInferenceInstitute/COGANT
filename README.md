# COGANT

Codebase-to-GNN translation — **package** under [`cogant/`](cogant/), **manuscript** under [`manuscript/`](manuscript/). This checkout is self-contained at the COGANT project root; when vendored into `docxology/template`, the same tree is expected to live at `projects/cogant/` and be discovered by the template pipeline (`infrastructure/project/discovery.py`). See [`PROMOTION.md`](PROMOTION.md) for the promotion checklist.

Top-level [`src/`](src/), [`tests/`](tests/), and [`pyproject.toml`](pyproject.toml)
form a tiny compatibility shell for the parent `docxology/template` project
discovery contract. The actual installable COGANT package remains the nested
[`cogant/`](cogant/) tree.

## Location matrix

| Context | COGANT project root | COGANT package root | Notes |
| --- | --- | --- | --- |
| Passive standalone checkout | `/Users/4d/Documents/GitHub/projects/passive/cogant` | `/Users/4d/Documents/GitHub/projects/passive/cogant/cogant` | Current local checkout; parent-template discovery and PDF rendering are not active. |
| Active parent-template project | `docxology/template/projects/cogant` | `docxology/template/projects/cogant/cogant` | Template discovery, Markdown validation, and `scripts/03_render_pdf.py --project cogant` apply here. |
| Historical staging path | `docxology/template/projects_in_progress/cogant` | `docxology/template/projects_in_progress/cogant/cogant` | Legacy references only; do not add new workflow docs that require this path. |

In this documentation, **COGANT project root** means the directory containing this README, `run_all.py`, `tools/`, `scripts/`, `manuscript/`, and the nested package directory. **COGANT package root** means the inner [`cogant/`](cogant/) directory containing `pyproject.toml`, `py/cogant/`, package tests, docs, and Rust crates.

## Manuscript variables (madlib)

Run these from the COGANT project root:

```bash
# 1. Regenerate METRICS.yaml from live test + benchmark runs.
uv run --directory cogant python ../tools/regenerate_metrics.py

# 2. Build manuscript_variables.json + output/manuscript/ + output/figures/.
uv run python scripts/z_generate_manuscript_variables.py

# 3. Validate local links + manuscript structure.
uv run --directory cogant python docs/verify_manuscript_links.py
uv run python tools/audit_manuscript_crossrefs.py
uv run python tools/audit_manuscript_citations.py
uv run python tools/audit_manuscript_numbers.py
```

When vendored under the parent template as `projects/cogant/`, also run from the template root:

```bash
uv run python -m infrastructure.validation.cli markdown projects/cogant/manuscript/
uv run python -m infrastructure.validation.cli markdown projects/cogant/output/manuscript/
```

Audit drift-sensitive docs and stubs:

```bash
uv run python tools/audit_docs_constants.py
uv run python tools/audit_folder_docs.py
uv run python tools/audit_pyi_exports.py
uv run python tools/audit_stage_list.py
uv run python tools/audit_manuscript_crossrefs.py
uv run python tools/audit_manuscript_citations.py
uv run python tools/audit_manuscript_numbers.py
uv run python tools/check_coverage_table.py --strict
uv run python tools/check_metrics_fresh.py --fail-on-dirty
```

`tools/audit_stage_list.py` enforces `RUNNER_STAGES` vs. doc/CLI drift. `tools/check_metrics_fresh.py --fail-on-dirty` is a release gate that refuses uncommitted metric provenance.

**Coverage table (`{#tbl:coverage-stmt-modules}`).** Per-module `Stmts` / `Cover` rows in [`manuscript/06_04_tests_mutation_and_benchmarks.md`](manuscript/06_04_tests_mutation_and_benchmarks.md) are hand-copied from `coverage report`. After `uv run pytest tests/ --cov=py/cogant` in [`cogant/`](cogant/) (inner package root), run `uv run python tools/check_coverage_table.py` from this project root to compare the table to the report; use `--strict` to fail on drift. See [`manuscript/AGENTS.md`](manuscript/AGENTS.md) and [`PROMOTION.md`](PROMOTION.md).

Rendering uses `output/manuscript/` when present in the parent template renderer (see `infrastructure/rendering/pipeline.py`). Full template PDF rendering requires the vendored `projects/cogant/` location and `scripts/03_render_pdf.py --project cogant`.

The same generator refreshes manuscript figures under `output/figures/` by
copying curated real run PNGs from `cogant/output/` (program graph,
state-space factor graph, A/B/C/D matrices, upstream GNN visualization, and
the roundtrip batch Gantt). After a new `run_all.py` batch, re-run step 2
above or run `uv run python tools/manuscript_figures.py --strict` to fail if
any publication figure is missing.

## Batch outputs (`run_all`)

Configurable orchestration at the project root (same level as this file):

- **`run_all.sh`** — resolves the project root (works from here or from inner [`cogant/`](cogant/)), then `cd` into the inner package and `uv run python ../run_all.py`
- **`run_all.py`** — reads **`run_all.json`** (optional; else built-in defaults), runs `cogant translate` → `scan`/`graph` → `export-gnn` → `render` → `viz` → **`validate`** (full GNN package + upstream `src.gnn` unless disabled in config) per target
- **`run_all.example.json`** — copy to `run_all.json` and set `targets` / `steps`

**Per-target output folders:** everything for one run goes under **`<output_root>/<target_id>/`** (`data/bundle.json`, `gnn_package/`, `site/`, `figures/` PNGs, `diagrams/`, `analysis/`, `exports/`, `roundtrip/`, `reports/run_summary.md`). The shipped [`run_all.json`](run_all.json) and built-in no-config defaults set `output_root: "cogant/output"`, so corpus runs land at `cogant/output/<target_id>/`; the minimal [`run_all.example.json`](run_all.example.json) sets `output_root: "output"` for project-root-relative smoke tests. A **`<output_root>/run_manifest.json`** records top-level metadata (`started_at`, `staging_root`, `package_root`, `output_root`, `dry_run`) and a **`targets`** array: each entry has `id`, `run_dir`, `commands` (list of `{cmd, step, exit, wall_time_s}`), and for `path`/`git_url` targets the fields described in `run_all.py` (`path`, `absolute_target`, `git_url`, `source_dir`, …). **`summary`** includes `total_wall_time_s`, `target_count`, and `failed_steps` (step labels when a non-zero exit was recorded). A cross-target **`<output_root>/summary.md`** + **`<output_root>/summary.json`** is written at the end with real per-target counts (nodes, edges, mappings), score, GNN-package file count, and presence flags for each layout subdirectory.

**Logging:** `+` command lines go to stdout (or append to `--log`); timestamped `[run_all …]` lines go to stderr (and duplicate to `--log` when set). Each target prints a `=== target …` banner before work (including `git clone` for remotes). Non-dry runs record per-step wall time and exit status; failed captured commands append an output tail. Use `./run_all.sh --dry-run` to list commands without executing.

**Batch dashboard (`<output_root>/dashboard/`).** When `steps.batch_dashboard` is on (default), `run_all` finishes by invoking [`scripts/batch_dashboard.py`](scripts/batch_dashboard.py), which calls `cogant.viz.batch_dashboard.BatchDashboardGenerator` against the just-written manifest. It writes corpus-stratified target metrics, parser/fallback summaries, roundtrip status counts, artifact-completeness flags, `summary.csv`, `metrics_per_target.json`, `dashboard.md`, and Mermaid artifacts. Re-run manually any time:

```bash
uv run --directory cogant python ../scripts/batch_dashboard.py \
    --output-root cogant/output
```

Full reference: [`cogant/docs/reference/batch_dashboard.md`](cogant/docs/reference/batch_dashboard.md). Opt out for a single batch via `"steps": { "batch_dashboard": false }` in `run_all.json`.

**Defaults (no `run_all.json`):** all three shipped [`examples/control_positive/`](cogant/examples/control_positive/) fixtures (`calculator`, `event_pipeline`, `flask_mini`) plus two small public repos cloned with shallow `git` into **`<output_root>/<target_id>/_git_source/`** (`remote_itsdangerous`, `remote_markupsafe`). The built-in default `output_root` is `cogant/output`; the example config uses `output`. Set `"remote": { "refresh": true }` in JSON to delete and re-clone; `"git_ref"` optional per target.

Optional `manuscript.enabled` runs `scripts/z_generate_manuscript_variables.py` into `output/` (variables + injected manuscript + copied manuscript figures), not under per-target run directories.

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
