# COGANT Code Quality Audit (Thermo-Nuclear)

**Date:** 2026-05-24  
**Scope:** Authored Python under `cogant/py/cogant/`, `tools/`, `scripts/`, `run_all.py`, outer `src/` (excludes `cogant/evaluation/eval_repos/**` vendored trees).  
**Rubric:** Thermo-nuclear maintainability review — 1k-line ceiling, anti-spaghetti, boundary cleanliness, code-judo restructuring.

## Executive verdict

**Conditional pass after W1 remediation.** Presumptive blockers on monolithic modules are resolved for the highest-risk files (`viz/png_export.py`, `cli/main.py`, `run_all.py`). Remaining files above 1k lines are scheduled in W2/W3. Baseline gates before refactor: mypy clean (211 files), ruff clean, pytest suite green at ≥89% coverage on `py/cogant`.

## Metrics snapshot (pre-refactor → post-W1)

| Metric | Before | After W1 |
|--------|--------|----------|
| Largest authored file | `viz/png_export.py` **4081** | `viz/png/mermaid.py` **1042** |
| Files >1000 lines (authored) | **16** | **12** |
| `cli/main.py` | 2053 | **17** (wiring only) |
| `run_all.py` | 1037 | **41** (argparse only) |
| `tools/manuscript_figures.py` | 1921 | **1405** (+ registry **524**) |
| `viz/png_export.py` shim | — | **87** (re-exports) |

### Files still >1000 lines (W2 targets)

| File | Lines | Issue class |
|------|------:|-------------|
| `viz/inspection_dashboard.py` | 2526 | HTML workbench monolith |
| `viz/png/mermaid.py` | 1042 | Residual png split (just over ceiling) |
| `tools/manuscript_figures.py` | 1405 | Copy/validation orchestration |
| `statespace/compiler.py` | 1447 | Compilation phases tangled |
| `api/orchestration.py` | 1440 | Step dispatch + viz hooks |
| `reverse/idempotency.py` | 1381 | Special-case branches |
| `viz/dashboard/generator.py` | 1392 | Dashboard HTML generation |
| `gnn/package.py` | 1273 | Package assembly |
| `viz/pdf_export.py` | 1263 | PDF rasterization |
| `server/app.py` | 1172 | FastAPI routes |
| `viz/batch_dashboard.py` | 1092 | Cross-target dashboard |
| `tools/run_all_runner.py` | 1023 | Batch target loop (extracted, still large) |
| `tools/regenerate_metrics.py` | 1015 | Metrics regeneration |
| `tools/audit_manuscript_numbers.py` | 1056 | Manuscript number audit |
| `gnn/json_export.py` | 1005 | JSON export |

## W1 remediations (completed)

### W1-A: `viz/png_export.py` → `viz/png/*`

Split into focused modules with a backward-compatible shim:

- `viz/png/config.py` — `RenderConfig`, shared drawing helpers
- `viz/png/program_graph.py`, `mermaid.py`, `svg.py`, `dot.py`, `state_space.py`, …
- `viz/png/orchestrator.py` — `render_all_pngs()` registry
- `viz/png_export.py` — re-export shim (public imports unchanged)

**Code-judo:** centralized backend dispatch; mermaid CLI resolution delegates through shim for test monkeypatch compatibility.

### W1-B: `cli/main.py` → `cli/_app.py` + `cli/commands/*`

- `cli/main.py` — Typer wiring + plugin/migrate registration (**17 lines**)
- `cli/_app.py` — shared app, console, pipeline error helpers
- `cli/commands/` — `setup.py`, `ingest.py`, `translate_cmd.py`, `analyze.py`, `export_validate.py`, `tools.py` (all **<510 lines**)

### W1-C: `run_all.py` → `tools/run_all_runner.py`

- `run_all.py` — argparse + `--print-default-config` (**41 lines**)
- `tools/run_all_runner.py` — batch implementation (`run_batch()`)

### W1-D: `tools/manuscript_figure_registry.py`

- Extracted `ManuscriptFigure` + `MANUSCRIPT_FIGURES` registry (**524 lines**)
- `tools/manuscript_figures.py` — copy/validation CLI (**1405 lines**, down from 1921)

## W2 recommendations (should-fix)

1. **Split `viz/inspection_dashboard.py`** into `inspection/model.py`, `panels/*.py`, `render_html.py` — largest remaining monolith.
2. **Split `viz/png/mermaid.py`** at parser vs renderer boundary (`mermaid_parse.py`, `mermaid_render.py`) to drop below 1k.
3. **Extract `tools/run_all_runner.py` target loop** into `run_target(steps, target, …)` module; keep runner under 600 lines.
4. **Split `api/orchestration.py`** — separate stage dispatch table from post-pipeline viz/manuscript hooks; import `RUNNER_STAGES` from `cogant.pipeline` instead of duplicating stage names in docs/CLI strings.
5. **Split `statespace/compiler.py`** by compilation phase (variables, temporal, matrices).

## W3 recommendations (defer)

- `reverse/idempotency.py`, `gnn/package.py`, `server/app.py` — decompose when those subsystems next change.
- `tools/regenerate_metrics.py` / `audit_manuscript_numbers.py` — extract metric source collectors behind a registry (mirror manuscript figure pattern).

## Boundary violations noted

| Location | Issue | Remedy |
|----------|-------|--------|
| `run_all.json` steps vs `RUNNER_STAGES` | Parallel vocabularies (batch steps ≠ pipeline stages) | Document mapping in `tools/audit_stage_list.py`; avoid merging unrelated stage lists |
| `api/orchestration.py` | Lazy-imports `render_all_pngs` mid-pipeline | Acceptable; keep viz coupling behind orchestration facade |
| `tools/` vs `cogant/py/cogant/` | Manuscript tooling at project root | Intentional for template vendoring (`PROMOTION.md`) |

## Verification checklist

From inner package root (`cogant/`):

```bash
uv run pytest tests/ -q --cov=py/cogant --cov-fail-under=89
uv run mypy py/cogant/
uv run ruff check py/cogant/
```

From COGANT project root:

```bash
uv run python run_all.py --print-default-config
uv run python tools/manuscript_figures.py --help
uv run cogant --help
```

PNG smoke (after a translate run):

```bash
uv run cogant translate examples/control_positive/calculator -o /tmp/cogant-smoke
uv run python -c "from cogant.viz.png_export import render_all_pngs; render_all_pngs('/tmp/cogant-smoke')"
```

## Approval bar status

| Criterion | Status |
|-----------|--------|
| No unjustified >1k file growth from W1 | Pass — largest W1 output is residual list above |
| Public API imports stable | Pass — `cogant.viz.png_export`, CLI entrypoints |
| Structural regressions | None observed in png/cli/run_all splits |
| Full test + type + lint gates | Re-run after merge (see verification) |
