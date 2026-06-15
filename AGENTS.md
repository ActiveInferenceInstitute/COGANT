# AGENTS.md — COGANT project root

## Layout

| Path | Role |
|------|------|
| [`cogant/`](cogant/) | Nested COGANT package (`py/cogant/`, `tests/`, `pyproject.toml`, Rust crates, docs). **This is the installable package root.** |
| [`manuscript/`](manuscript/) | PDF/HTML manuscript templates with `{{PLACEHOLDER}}` substitution syntax. Source of truth for prose; never edit by hand any number that has a `{{...}}` token. |
| [`tools/`](tools/) | `MANUSCRIPT_VARS` registry, metrics regeneration CLI, inject CLI, audit helpers, manuscript figure copier. |
| [`scripts/`](scripts/) | Thin orchestrators (`z_generate_manuscript_variables.py`, which also refreshes `output/figures/`). |
| [`src/`](src/), [`tests/`](tests/), [`pyproject.toml`](pyproject.toml) | Tiny parent-template compatibility shell so `docxology/template` project discovery sees top-level source/tests when linked under `projects/working/cogant/`. The real package remains nested under `cogant/`. |
| [`run_all.py`](run_all.py), [`run_all.sh`](run_all.sh), [`run_all.example.json`](run_all.example.json) | Configurable batch run: `translate` + GNN exports + `render` + `viz` + `validate` per target. Targets are either `path` (under inner `cogant/`) or `git_url` (shallow clone to `<output_root>/<target_id>/_git_source/`). If `run_all.json` is absent, built-in defaults cover the three `examples/control_positive/*` fixtures plus two small Pallets repos; the shipped `run_all.json` is the larger corpus config. The shipped and built-in configs set `output_root: "cogant/output"`; `run_all.example.json` uses `output`. Each target writes under `<output_root>/<target_id>/` (with `data/`, `figures/`, `site/`, `reports/`, `gnn_package/`, `analysis/`, `exports/`, `roundtrip/`). Stderr + optional `--log`: per-target banner, per-step wall time / exit status, batch `summary` in `<output_root>/run_manifest.json`, cross-target `summary.md`/`summary.json`, and `<output_root>/dashboard/` when `steps.batch_dashboard` is enabled. |
| [`output/`](output/) | Generated manuscript outputs — `data/manuscript_variables.json`, `output/manuscript/` injected copy, and copied figures (all disposable and regeneratable). Batch runs write per-target directories under the configured `<output_root>/<target_id>/`; the shipped `run_all.json` uses `cogant/output`, while `run_all.example.json` uses project-root `output`. |
| [`PROMOTION.md`](PROMOTION.md) | Checklist for exposing this working sidecar tree to the parent template render location. |

## Location matrix

| Context | COGANT project root | COGANT package root | Notes |
| --- | --- | --- | --- |
| Working sidecar checkout | `<cogant-sidecar>` | `<cogant-sidecar>/cogant` | Current local checkout; run project-local commands here. |
| Parent-template render path | `<template-checkout>/projects/working/cogant` | `<template-checkout>/projects/working/cogant/cogant` | Created by the sidecar/template linker; render with `--project working/cogant`. |

## Two-directory structure (common confusion point)

Two paths named `cogant/` exist and mean different things:

```
COGANT_PROJECT_ROOT/                 ← project root (this file's directory)
  manuscript/                         ← manuscript templates
  tools/                              ← manuscript tooling (MANUSCRIPT_VARS registry, inject/regenerate/audit/figure CLIs)
  scripts/                            ← thin orchestrators (z_generate_manuscript_variables.py)
  src/, tests/, pyproject.toml         ← parent-template compatibility shell
  output/                             ← disposable manuscript outputs (variables JSON + injected copy + copied figures)
  cogant/                             ← THE ACTUAL PYTHON+RUST PACKAGE
    output/                           ← shipped run_all output_root (per-target run dirs)
    py/cogant/                        ← import root (import cogant → here)
    tests/                            ← pytest suite (run from cogant/)
    rust/                             ← 8 PyO3 crates
    docs/                             ← MkDocs site
    evaluation/METRICS.yaml           ← SINGLE SOURCE OF TRUTH for all numbers
    pyproject.toml
    Makefile
```

When any doc (README, AGENTS, cookbook, CLI help) says "run from `cogant/`" it means the **inner** `cogant/` — the installable package root — not the COGANT project root. "Run from the COGANT project root" means this file's directory.

## Key APIs (tools layer)

| Module | Key exports |
|--------|------------|
| `tools/manuscript_vars.py` | `MANUSCRIPT_VARS` registry (placeholder → YAML dotpath), `resolve_path`, `format_value_for_path`, `build_flat_variables`, `substitute_text`, `find_unresolved_placeholders` |
| `tools/inject_manuscript_vars.py` | CLI: substitute one file or directory; `--dry-run`, `--report`, `--strict` flags |
| `tools/regenerate_metrics.py` | Rebuilds `cogant/evaluation/METRICS.yaml` from live test + pipeline runs |
| `tools/audit_manuscript_citations.py` | Verifies body citation keys exist in `manuscript/references.bib`; fails on missing or duplicate keys |
| `tools/audit_manuscript_formalisms.py` | Verifies typed formalism labels, generated formal numbering, and `@def:` / `@prop:` / `@inv:` / `@conj:` / `@alg:` / `@thm:` references |
| `tools/audit_manuscript_numbers.py` | Checks all prose numbers against `METRICS.yaml`; flags drift |
| `tools/audit_manuscript_markdown_links.py` | Rejects rendered body links to `.md` files; public manuscript links should be intra-manuscript refs, figures/tables/equations/formalisms, or citations |
| `tools/audit_manuscript_math_adjacency.py` | Resolves manuscript variables and fails on inline math spans whose closing `$` is immediately followed by a digit |
| `tools/audit_manuscript_claim_scope.py` | Rejects uncaveated guarantees, inferential-statistics wording, and semantic-totality overclaims in manuscript prose |
| `tools/audit_robustness_table.py` | Checks the manuscript robustness table against the generated robustness JSON artifact |
| `tools/audit_synthetic_surfaces.py` | Classifies retained synthetic-surface terminology and fails on unallowlisted or unbacked cases |
| `tools/audit_figure_renderers.py` | Verifies registered figure renderer import paths and locked caption/provenance constants |
| `tools/audit_publication_readiness.py` | Combines claim ledger, evidence audit, visual QA, figure manifest, date autofill, claim-scope, and docs-constant status into a publication readiness verdict |
| `tools/citation_claim_ledger.py` | Emits reviewable claim/source pairs for selected citation keys |
| `tools/check_metrics_fresh.py` | Warns if `METRICS.yaml` has drifted from source artifacts |
| `tools/manuscript_figures.py` | Copies curated package-generated PNGs from `cogant/output/` into `output/figures/` |
| `scripts/z_generate_manuscript_variables.py` | Thin orchestrator: YAML → JSON + full `output/manuscript/` tree + copied figures |

## Manuscript pipeline (three commands)

Run these from the COGANT project root:

```bash
# 1. Regenerate METRICS.yaml from live test + benchmark runs.
uv run --directory cogant python ../tools/regenerate_metrics.py

# 2. Build manuscript_variables.json + formalism_registry.json + output/manuscript/ + output/figures/.
uv run python scripts/z_generate_manuscript_variables.py

# 3. Validate local links + manuscript structure.
uv run --directory cogant python docs/verify_manuscript_links.py
uv run python tools/audit_manuscript_crossrefs.py
uv run python tools/audit_manuscript_citations.py
uv run python tools/audit_manuscript_formalisms.py --strict
uv run python tools/audit_manuscript_numbers.py
uv run python tools/audit_manuscript_markdown_links.py
uv run python tools/audit_manuscript_math_adjacency.py
uv run python tools/audit_manuscript_claim_scope.py
uv run python tools/audit_robustness_table.py
uv run python tools/audit_synthetic_surfaces.py --strict
uv run python tools/audit_figure_renderers.py
uv run python tools/audit_publication_readiness.py --strict
```

When this tree is linked under the parent template as `projects/working/cogant/`,
also run the template Markdown validator from the template root:

```bash
uv run python -m infrastructure.validation.cli markdown projects/working/cogant/manuscript/
uv run python -m infrastructure.validation.cli markdown projects/working/cogant/output/manuscript/
```

All `{{PLACEHOLDER}}` tokens in `manuscript/*.md` resolve against `cogant/evaluation/METRICS.yaml`
via the registry in `tools/manuscript_vars.py`. **Never hand-edit a number that has a `{{...}}`
token** — fix the METRICS.yaml source instead.
`tools/regenerate_ablation.py` populates `ablation.*` in `METRICS.yaml` and is called by `tools/regenerate_metrics.py`.
Keep `manuscript/config.yaml` `paper.date` empty for active publication builds so the parent template fills the render date.

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
manuscript. If a prose number looks drifted, regenerate and re-inject; never hand-edit.

**Live suite:** run `cd cogant && uv run pytest tests/ -q` from the inner package root; counts are
not duplicated here (they drift every commit).

**Coverage (package `pyproject.toml`):** `pytest-cov` measures `py/cogant` with `branch = false`
(line gate), `omit` for `py/cogant/static/treesitter_parser.py`,
and `--cov-fail-under=89`. Treat the current aggregate percentage in
`cogant/evaluation/METRICS.yaml` as authoritative rather than duplicating it here.

Canonical benchmark-style figures still in `METRICS.yaml` (roundtrip, etc.) — refresh via
`regenerate_metrics.py` when changing fixtures or thresholds.

## Promotion checklist

`PROMOTION.md` is authoritative. In brief:
1. Ensure the sidecar/template linker exposes this tree under `../template/projects/working/cogant`.
2. Run the three manuscript commands above.
3. From the template root, run `uv run python scripts/03_render_pdf.py --project working/cogant`.

After promotion, this tree is discovered by the parent template `./run.sh` and infrastructure
pipeline; before promotion, use the project-local `uv` / `make` / `pytest` commands above.

## Discovery

Discovered by `discover_projects()` only when linked under the parent template
project tree; see [`PROMOTION.md`](PROMOTION.md) for the current render-location checklist.

## Imported Claude Cowork project instructions

Methodical, intelligent, most relevant, modular, functional, well-documented.
