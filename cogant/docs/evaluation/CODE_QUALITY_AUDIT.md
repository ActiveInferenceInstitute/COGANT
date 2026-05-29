# COGANT Code Quality Audit (Thermo-Nuclear)

**Date:** 2026-05-28 (post-restore verification)  
**Scope:** Authored Python under `cogant/py/cogant/`, `tools/`, `scripts/`, `run_all.py`, outer `src/` (excludes `cogant/evaluation/eval_repos/**` vendored trees).  
**Rubric:** Thermo-nuclear maintainability review — 1k-line ceiling, anti-spaghetti, boundary cleanliness, code-judo restructuring.

## Executive verdict

**Pass (post-restore).** Incomplete wave-3 mechanical line-range splits were discarded; HEAD functionality restored on `main` with W1/W2 semantic splits retained (`cli/`, `png/`, `run_target`, mermaid parse/render). PNG orchestration now dispatches through `cogant.viz.png_export` so tests can monkeypatch the public shim. Gates measured 2026-05-28: ruff clean, mypy clean (232 files), pytest **9651+** passed at **95.5%** line coverage on `py/cogant` (≥89% gate), `cogant doctor` READY.

**Do not repeat:** `scripts/split_*.py` line-range generators, mixin reassembly, or partial wiring of orphan draft modules. Future splits are one monolith at a time with TDD (see backlog below).

## Metrics snapshot (pre-refactor → post-W1 → post-restore)

| Metric | Before | After W1 | Post-restore (2026-05-28) |
|--------|--------|----------|---------------------------|
| Largest authored file | `viz/png_export.py` **4081** | `viz/inspection_dashboard.py` **2526** | `viz/inspection_dashboard.py` **2526** |
| Files >1000 lines (authored) | **16** | **12** | **12** |
| `cli/main.py` | 2053 | **17** | **17** |
| `run_all.py` | 1037 | **41** | **41** |
| `viz/png_export.py` shim | — | **87** | **109** (re-exports + test dispatch) |
| `viz/png/orchestrator.py` | — | — | **229** (lazy `png_export` dispatch) |
| pytest + coverage | — | re-run after merge | **9651 passed**, **95.5%** on `py/cogant` |
| mypy `py/cogant/` | clean (211 files) | clean | **clean (232 files)** |
| ruff `py/cogant/` | clean | clean | **clean** |

### Files still >1000 lines (semantic-split backlog)

| Priority | File | Lines | Better approach |
|----------|------|------:|-----------------|
| P1 | `server/app.py` | 1172 | `routes.py` + `middleware.py`; keep `ErrorResponse` imported in handlers |
| P2 | `viz/pdf_export.py` | 1263 | Mirror W2 `png/` pattern: `viz/pdf/orchestrator.py` + per-report modules |
| P3 | `api/orchestration.py` | 1440 | Stage dispatch table vs post-pipeline hooks |
| P4 | `statespace/compiler.py` | 1447 | Phase extractors + shared `model_types.py` first |
| P5 | `viz/inspection_dashboard.py` | 2526 | `inspection/html/`, `inspection/svg/` when panel boundaries are clear |
| — | `viz/png/mermaid.py` | ~1042 | Parser vs renderer (`mermaid_parse.py`, `mermaid_render.py`) |
| — | `tools/manuscript_figures.py` | 1405 | Further registry extraction |
| — | `reverse/idempotency.py` | 1381 | Defer until subsystem changes |
| — | `gnn/package.py` | 1273 | Defer |
| — | `tools/run_all_runner.py` | 1023 | Extract `run_target` loop (partially done) |

## W1 remediations (completed)

### W1-A: `viz/png_export.py` → `viz/png/*`

Split into focused modules with a backward-compatible shim:

- `viz/png/config.py` — `RenderConfig`, shared drawing helpers
- `viz/png/program_graph.py`, `mermaid.py`, `svg.py`, `dot.py`, `state_space.py`, …
- `viz/png/orchestrator.py` — `render_all_pngs()` registry
- `viz/png_export.py` — re-export shim (public imports unchanged)

**Post-restore dispatch:** `orchestrator.render_all_pngs` lazy-imports `cogant.viz.png_export` and calls renderers on that module so unit tests can monkeypatch `png_export.*`. Submodule batch helpers (`render_all_svg_in_run`, `render_all_mermaid_in_run`) delegate file-level renders through the same shim.

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

## Wave-3 mechanical split (aborted — do not revive)

A line-range `scripts/split_*.py` wave gutted seven shims and left **52 unreachable orphan modules** duplicating live monoliths. Symptoms included import failures, server `ErrorResponse` `NameError` (422→500), and deleted tests. Recovery: branch `wip/broken-wave3-backup` preserves forensics; `main` restored to `2d5c2d9` plus minimal dispatch fixes above.

### Rules for any future split

1. **One monolith at a time** — wiring + tests + delete old code in the same change.
2. **Semantic boundaries** — compilation phase, route group, renderer type; never `lines[178:364]`.
3. **No throwaway generators** — ban `scripts/split_*.py` pattern.
4. **No mixin reassembly** — prefer composition or a single class module.
5. **No orphan tests** — no `_part1..N` islands without shared fixtures.
6. **Import closure** — after each split, import-sweep; every new module reachable from tracked code.

## Boundary violations noted

| Location | Issue | Remedy |
|----------|-------|--------|
| `run_all.json` steps vs `RUNNER_STAGES` | Parallel vocabularies | Document mapping in `tools/audit_stage_list.py` |
| `api/orchestration.py` | Lazy-imports `render_all_pngs` mid-pipeline | Acceptable; keep viz coupling behind orchestration facade |
| `tools/` vs `cogant/py/cogant/` | Manuscript tooling at project root | Intentional for template vendoring (`PROMOTION.md`) |
| `test_package_init_metadata` reload | Stale `png_export` refs in long pytest runs | Exception tests use `_live_png_export()` helper |

## Verification checklist

From inner package root (`cogant/`):

```bash
uv run python -c "import cogant; import cogant.viz"
uv run ruff check py/cogant/
uv run mypy py/cogant/
uv run pytest tests/ -q --cov=py/cogant --cov-fail-under=89
uv run cogant doctor
```

From COGANT project root:

```bash
uv run python run_all.py --print-default-config
uv run python scripts/z_generate_manuscript_variables.py
uv run python tools/audit_manuscript_numbers.py
uv run cogant --help
```

Real-functionality smokes:

```bash
uv run cogant translate examples/control_positive/calculator -o /tmp/cogant-smoke
uv run python -c "from cogant.viz.png_export import render_all_pngs; print(sum(len(v) for v in render_all_pngs('/tmp/cogant-smoke').values()))"
uv run python -c "from fastapi.testclient import TestClient; from cogant.server.app import create_app; assert TestClient(create_app()).post('/analyze', json={}).status_code == 422"
```

## Approval bar status

| Criterion | Status |
|-----------|--------|
| No unjustified >1k file growth from W1 | Pass |
| Public API imports stable | Pass — `cogant.viz.png_export`, CLI entrypoints |
| Structural regressions | None after restore + dispatch fix |
| Full test + type + lint gates | **Pass** (measured 2026-05-28) |
| Mechanical wave-3 debris removed | Pass — backup on `wip/broken-wave3-backup` |
