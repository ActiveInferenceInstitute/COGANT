# AGENTS.md — COGANT manuscript

## Purpose

Long-form prose describing COGANT theory and practice in the same structural shape as the parent template's code-oriented manuscript projects when this checkout is linked into `projects/working/cogant/`. This folder is **not** a substitute for package documentation; it synthesizes narrative for PDF/HTML output via the template rendering stack when the project is active under `projects/`.

## Location terms

| Term | Meaning |
| --- | --- |
| COGANT project root | The directory above this manuscript folder; in this working checkout, `<cogant-sidecar>`. |
| COGANT package root | The nested `../cogant/` directory containing `pyproject.toml`, `py/cogant/`, package tests, and package docs. |
| Template render location | `<template-checkout>/projects/working/cogant`; parent-template validators and renderers apply only there. |

## Canonical sources of truth

When the Python API, CLI, export schema, or implementation status changes, update **both**:

1. Package docs under [`../cogant/docs/`](../cogant/docs/): MkDocs home [`../cogant/docs/index.md`](../cogant/docs/index.md), module map [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md), each `docs/<module>/README.md`, and deep pages.
2. The corresponding manuscript fragments (`02_01_*.md`, `06_04_*.md`, `08_02_*.md`, etc.).

Implementation status: [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md).

When updating quantitative claims, refresh [`../cogant/evaluation/METRICS.yaml`](../cogant/evaluation/METRICS.yaml) (`uv run --directory cogant python ../tools/regenerate_metrics.py` from the COGANT project root), then run [`../scripts/z_generate_manuscript_variables.py`](../scripts/z_generate_manuscript_variables.py) from the project root so `{{ TOKEN }}` tokens in `*.md` resolve consistently (registered names in [`../tools/manuscript_vars.py`](../tools/manuscript_vars.py); no spaces inside real keys). Use `--strict` on that script in CI only when no stray placeholder tokens remain in prose (documentation may use spaced `{{ TOKEN }}` forms that the injector ignores). After link edits, run [`../cogant/docs/verify_manuscript_links.py`](../cogant/docs/verify_manuscript_links.py) from the project root with `uv run --directory cogant python docs/verify_manuscript_links.py`.

**Fixture tables (examples chapter and performance metrics chapter).** `../cogant/evaluation/figures/metrics.json` is produced by [`../cogant/evaluation/figures/generate_figures.py`](../cogant/evaluation/figures/generate_figures.py), which calls [`../cogant/evaluation/figures/pipeline_api_metrics.py`](../cogant/evaluation/figures/pipeline_api_metrics.py) so node/edge/mapping tallies use `cogant.api.orchestration` (aligned with [`../cogant/benchmarks/bench_suite.py`](../cogant/benchmarks/bench_suite.py)). `mappings_total` is taken from the in-memory `semantic_mappings` dict immediately after `run_statespace` and before `process` / `export`; the benchmark’s `mappings` column is defined the same way. `TranslationEngine._resolve_conflicts` uses **sorted** iteration over colliding mapping pairs so the same fixture yields the same `mappings_total` in `generate_figures` and `bench_suite` for a given build. GNN/validator columns still come from the full `process` + `export` + `validate` pass.

**@tbl:coverage-stmt-modules (per-module coverage).** The statement-count and per-module percentage rows are canonical in [`06_04_tests_mutation_and_benchmarks.md`](06_04_tests_mutation_and_benchmarks.md) (post-table line `{#tbl:coverage-stmt-modules}`). [`06_00_experimental_setup.md`](06_00_experimental_setup.md) references that table with `@tbl:` / `@sec:` pointers only — it does **not** duplicate the table body (duplicate table labels break pandoc-crossref). These rows are **not** in `METRICS.yaml`. Refresh them from the canonical `coverage.py` report whenever the test suite or omit rules change, so they match the injected aggregate coverage and timestamp fields.

**Automated drift check (optional).** After `uv run pytest tests/ --cov=py/cogant` in the **package** root ([`../cogant/`](../cogant/), the inner tree next to this manuscript folder), run:

`uv run python ../tools/check_coverage_table.py` (or `--package-root ../cogant` from [`../tools/`](../tools/)) to compare @tbl:coverage-stmt-modules to `coverage report`. Use `--strict` in CI to fail on mismatch or missing data; without `--strict`, a missing `.coverage` file exits 0 with a message to stderr. See [`../PROMOTION.md`](../PROMOTION.md) post-move checklist.

## Cross-references (pandoc-crossref)

Section and table identifiers use `{#sec:…}` / `{#tbl:…}` on headings and table captions; prose references use `@sec:…` and `@tbl:…`. See [`SYNTAX.md`](SYNTAX.md). The combined PDF renderer runs Pandoc with `--filter pandoc-crossref` when the `pandoc-crossref` binary is on `PATH`; install it locally for resolved references in PDF output.

## Files excluded from combined PDF body

Per `infrastructure/rendering/manuscript_discovery.py`, these names are **not** concatenated as sections: `preamble.md`, `AGENTS.md`, `README.md`, `config.yaml`, `references.bib`. `SYNTAX.md` and `supplementary.md` are plain Markdown files in this directory and may be included by the renderer's "other" bucket unless the parent template skip list excludes them; keep examples safe or explicitly exclude them before publication rendering.

## Section ordering

- Main narrative: `00_`–`09_` with optional splits `NN_MM_slug.md` (for example `02_01_…`, `06_03_…`) — sorted by **full stem** string order.
- Supplemental appendices: `S01_*.md` … `S06_*.md` (Appendices A–F) after main sections.
- Glossary: `98_*.md` when present.
- Other Markdown (for example `SYNTAX.md`): **other** bucket after supplemental.
- References: `99_*.md` last among Markdown.

Keep numbering aligned with the parent template renderer (`infrastructure/rendering/manuscript_discovery.py`) when this project is linked under `projects/working/cogant/`.

**Appendix status (current manuscript):**
- S01 (Appendix A — Roundtrip role preservation): current native role-preservation evidence and drift rows.
- S02 (Appendix B — Ablation): current reconstructed ablation evidence; measured deltas remain scoped to the cited fixtures.
- S03 (Appendix C — Galois sketch): current Galois-style preorder comparison; approximate adjunction remains a conjecture and role preservation is a scoped empirical invariant.
- S04 (Appendix D — Inference math): current emitted-model inference mathematics; exactness claims are limited to the represented finite matrix model.
- S05 (Appendix E — Extended related work): current curated related-work map.
- S06 (Appendix F — Source references): current source-reference index for package docs, evaluation artifacts, and tooling.
- `98_notation_supplement.md` (Glossary G — Notation supplement): current symbol index for program graph, translation engine, confidence model, A/B/C/D matrices, category theory, equation index, roles/mapping kinds, node/edge enumerations, and acronyms.

Do **not** place full duplicate papers in the flat manuscript directory if they are not intended as PDF sections; store archival copies under `_archive/` (subdirectories are not scanned by discovery) or outside `manuscript/`. One-off split scripts that referenced removed monoliths have been removed; do not reintroduce them—edit the numbered fragments directly.

Canonical technical hubs to sync when the implementation changes:

- [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md) (full map of `docs/` modules and `docs/<module>/` areas)
- [`../cogant/docs/index.md`](../cogant/docs/index.md) (published docs entry)
- [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md)
- [`../cogant/docs/api/README.md`](../cogant/docs/api/README.md)
- [`../cogant/docs/cli/README.md`](../cogant/docs/cli/README.md)
- [`../cogant/docs/export/README.md`](../cogant/docs/export/README.md)
- [`../cogant/docs/plugins/README.md`](../cogant/docs/plugins/README.md)
- [`../cogant/docs/validation/README.md`](../cogant/docs/validation/README.md)
- [`../cogant/docs/architecture/README.md`](../cogant/docs/architecture/README.md)
- [`../cogant/docs/evaluation/README.md`](../cogant/docs/evaluation/README.md) (R&D log, empirical reports)
- [`../cogant/evaluation/README.md`](../cogant/evaluation/README.md) (benchmark corpora, dashboards; not in the wheel)

## Synchronization cadence

Update manuscript fragments **within two weeks** of any public API change, CLI addition,
or rule-set modification. The authoritative check is:

```bash
# From this COGANT project root
uv run python tools/audit_manuscript_crossrefs.py       # orphan @sec/@tbl vs {#sec:}/{#tbl:}; duplicate ids
uv run python tools/audit_manuscript_citations.py       # body @citation keys vs references.bib; duplicate bib keys
uv run python tools/audit_manuscript_formalisms.py --strict  # typed formal labels and generated formal numbering
uv run python tools/audit_manuscript_numbers.py           # numeric drift vs METRICS.yaml
uv run python tools/audit_manuscript_math_adjacency.py     # inline-math spans that would leak after digit substitution
uv run python tools/audit_robustness_table.py              # robustness table rows vs generated JSON artifact

# From this COGANT project root, running inside the inner package root
uv run --directory cogant python docs/verify_manuscript_links.py  # catch broken cross-links
```

Template `.github/workflows/` jobs do **not** invoke COGANT manuscript scripts unless this tree is linked under `projects/working/cogant/` and a workflow explicitly targets it; run these locally before manuscript edits.

**Source of truth on conflicts:** if package docs and manuscript prose disagree,
the package docs are authoritative for API names, types, and behaviour; the manuscript
is authoritative for the narrative framing and pedagogical presentation. When resolving
a conflict, update the manuscript to match the package docs — never the reverse.

**Breaking changes:** when an API is removed or renamed, keep manuscript prose on
the shipped replacement and avoid preserving removed forms as active methods.

## Citations

Keys live in `references.bib`. Use Pandoc cite syntax documented in [`SYNTAX.md`](SYNTAX.md).

## Figures

The examples chapter uses real package-run PNGs copied by [`../tools/manuscript_figures.py`](../tools/manuscript_figures.py). The registry source paths live under `../cogant/output/` (for example `calculator/figures/` and `dashboard/run_gantt.png`); the copied render assets live under `../output/figures/` and are referenced from generated Markdown as `../figures/<name>.png`. Strict mode now requires figure metadata, visual QA fields, source sidecars where available, registered-and-cited consistency, and evidence-specific displayed counts; it is not merely a file-presence check. From the COGANT project root, run `uv run python tools/manuscript_figures.py --strict` before publication renders so missing or under-documented visual evidence fails loudly.

## Pipeline caveat

In a standalone checkout, discovery-based parent-template scripts will not target this manuscript. After linking under `docxology/template/projects/working/cogant/`, run the parent template Markdown validator and PDF renderer described in [`README.md`](README.md).
