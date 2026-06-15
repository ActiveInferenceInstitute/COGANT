# COGANT manuscript

Template-aligned Markdown for **COGANT** (Codebase-to-GNN Translation): theory of the program graph IR and practice of the Python/Rust pipeline. Authoritative API, CLI, export schema, and plugin docs remain in the package tree:

**Documentation map:** [`../cogant/docs/index.md`](../cogant/docs/index.md) (MkDocs site home; narrative entry) and [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md) (every `docs/<module>/` area). Consolidated CLI flags: [`../cogant/docs/cli_reference.md`](../cogant/docs/cli_reference.md). Implementation scope: [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md).

## Location terms

| Term | Meaning |
| --- | --- |
| COGANT project root | The directory above this manuscript folder; in this working checkout, `<cogant-sidecar>`. |
| COGANT package root | The nested `../cogant/` directory containing `pyproject.toml`, `py/cogant/`, package tests, and package docs. |
| Template render location | `<template-checkout>/projects/working/cogant`; parent-template validators and renderers apply only there. |

## Section files

Stem order follows the parent template renderer (`infrastructure/rendering/manuscript_discovery.py`) when linked under `projects/working/cogant/`: digit-prefixed names sort lexicographically, so overview pages that own a chapter prefix use `NN_00_...` before `NN_01_...` detail files. Discovery concatenates main sections (`00_`-`10_`), then supplemental appendices (`S01_`-`S06_`), then glossary files (`98_`), then the **other** bucket (for example `SYNTAX.md`), then optional `99_*.md` references last. Do not hard-code section-file counts in prose; re-count with `find manuscript -maxdepth 1 -name '*.md'` from the COGANT project root after adds or splits.

**Pandoc-crossref sanity** (COGANT project root): `uv run python tools/audit_manuscript_crossrefs.py` — fails on duplicate `{#sec:…}` / `{#tbl:…}` ids or orphan `@sec:` / `@tbl:` references across body fragments (`SYNTAX.md` and a few helpers are skipped so example ids do not pollute the audit). **Formalism sanity:** `uv run python tools/audit_manuscript_formalisms.py --strict` — fails on `{#sec:def-...}`-style formal labels, hand-numbered formal claims, unresolved `@def:` / `@prop:` / `@inv:` / `@conj:` / `@alg:` / `@thm:` references, or generated numbering drift. **Citation sanity:** `uv run python tools/audit_manuscript_citations.py` — fails when a body citation key is missing from `references.bib` or duplicated there.

| Files | Contents |
|------|-----------|
| `00_abstract.md` | Structured abstract (method / evidence / scope); metrics via `METRICS.yaml` |
| `01_introduction.md` | Motivation, GNN terminology, reading lanes, non-goals, hub table, roadmap |
| `02_01_program_graph_and_formal_foundations.md` | Program graph, definitions, and scoped formal claims |
| `02_02_ir_progression_translation_engine.md` | Progressive IRs, rules, fixpoint, algorithms |
| `02_03_confidence_state_space_and_behavior.md` | Confidence model, state-space compilation, example |
| `02_04_gnn_export_and_error_handling.md` | GNN export contract and error philosophy |
| `03_api_and_workflows.md` | Session, pipeline, bundle, CLI, Review API |
| `04_examples_and_failure_modes.md` | End-to-end examples and degradation behavior |
| `06_00_experimental_setup.md` | Materials-and-methods overview, evidence model, reviewer-pressure map; detailed install/config/export/IR are in `06_01` / `06_02`; captioned fixture and test/benchmark tables are in `06_03` / `06_04` (avoids duplicate `{#tbl:…}` bodies) |
| `06_01_environment_api_and_config.md` | Environment, Session/Pipeline snippets, YAML config, CLI |
| `06_02_exports_parser_and_ir_stages.md` | Export targets, Python parser, IR stage table |
| `06_03_performance_and_fixture_metrics.md` | Performance targets, fixture tables |
| `06_04_tests_mutation_and_benchmarks.md` | Test matrix, mutation notes, benchmark harness |
| `06_05_reproducible_recording.md` | What to record for reproducibility |
| `07_reproducibility.md` | Versioning, determinism, validation gates |
| `08_00_scope_and_related_work.md` | **Section aggregator** — chapter heading, scholarship pressure map, scope statement, and title-based pointers to the related-work subsections |
| `08_01_landscape_and_tool_categories.md` | Landscape and tool categories |
| `08_02_program_analysis_for_ml_and_tables.md` | ML-related work and feature / I/O tables |
| `08_03_lenses_and_synthesis.md` | Lenses, synthesis, categorical framing |
| `08_04_world_models_boundaries_and_compatibility.md` | World models, active inference, boundaries |
| `08_05_threats_to_validity.md` | Threats to validity and scoped caveats |
| `09_ablation.md` | Rule-family and matrix ablations |
| `10_conclusion.md` | Capabilities, limitations, roadmap |

**Supplemental appendices** (`S01_`–`S06_`): see [`supplementary.md`](supplementary.md) for the index. Currently six appendices — A (roundtrip ε), B (ablation), C (Galois sketch), D (inference math), E (extended related work), F (source references).

**Glossary / notation** (`98_`): `98_notation_supplement.md` — canonical reference for manuscript-level mathematical symbols, acronyms, and formal objects (Groups G.1–G.9). Discovery places this after the appendices and before the `99_` references.

Supporting files excluded by the template renderer: `config.yaml`, `preamble.md`, `references.bib`, `AGENTS.md`, and `README.md`. `SYNTAX.md` and `supplementary.md` are ordinary Markdown files in this flat directory and may enter the "other" bucket unless the renderer skip list excludes them; keep example labels in `SYNTAX.md` out of the audited body or add an explicit renderer exclusion before publication.

**Volatile metrics.** Quantitative claims use `{{ PLACEHOLDER }}` tokens (no spaces in real keys; see registry) filled from [`../cogant/evaluation/METRICS.yaml`](../cogant/evaluation/METRICS.yaml). Regenerate metrics, then build the injected manuscript:

Run these from the COGANT project root:

```bash
# Regenerate metrics from the package root.
uv run --directory cogant python ../tools/regenerate_metrics.py

# Build injected manuscript and copied figures.
uv run python scripts/z_generate_manuscript_variables.py
```

From the parent template root after linking under `projects/working/cogant/`:

```bash
uv run python projects/working/cogant/scripts/z_generate_manuscript_variables.py
```

Outputs: `../output/data/manuscript_variables.json`, `../output/data/formalism_registry.json`, `../output/manuscript/*.md` (plus copied `config.yaml`, `references.bib`, `preamble.md`), and `../output/figures/manifest.json` with the curated real-run and evaluation PNGs referenced from the manuscript. The renderer prefers `output/manuscript/` when those files exist, and the figure paths in generated Markdown resolve to sibling assets under `output/figures/`. Formal numbers are generated into `output/manuscript/` only; source prose keeps typed labels such as `{#def:program-graph}` and references such as `@def:program-graph`.

**Publication metadata and readiness.** `config.yaml` keeps `paper.date` empty on purpose; the template renderer fills the date at render time. Do not replace it with a fixed calendar date for active publication builds. `scripts/z_generate_manuscript_variables.py` also refreshes `../output/analysis/publication_readiness.json` and `.md`, which classify claim-ledger rows as metric-backed, artifact-backed, citation-backed, validator-backed, boundary/limitation, or unsupported. A strict readiness block means the manuscript still has a metadata, claim-support, figure, or validator issue that must be fixed before promotion.

**Manuscript figures.** The copied figures come from declared package-generated and evaluation outputs: calculator run artifacts under `../cogant/output/`, fixture metric figures under `../cogant/evaluation/figures/`, and the measured ablation render produced from `../cogant/evaluation/METRICS.yaml`. The registry covers the native graphical abstract and interpretability overview, forward graph/state-space/matrix renders, the all-page GNN Markdown mosaic, the Markov-blanket partition, upstream GNN POMDP visualization, the calculator-focused `run_all.py` publication timeline with the explicit `roundtrip_calculator` stage, roundtrip diff, rule-evidence trace, evidence-coverage/review-readiness panel, deterministic inference trace, rule-family ablation, and fixture graph/role/state-space/timing figures. The figure manifest and per-figure `.figure.json` sidecars record renderer, source artifact, data digest, dimensions, byte size, visual QA, reading guide, limitation, and alt text; strict promotion also rejects degraded SVG-rasterization placeholders, native-required detail panels produced by fallback rasterization, and timeline dimensions that are unsuitable for publication. Refresh them from the COGANT project root with:

```bash
uv run python tools/manuscript_figures.py --strict
uv run python tools/visualization_quality_audit.py --strict
uv run python tools/manuscript_evidence_audit.py --strict
uv run python tools/manuscript_review_dashboard.py --strict
uv run python tools/audit_publication_readiness.py --strict
```

**@tbl:coverage-stmt-modules (per-module statement coverage).** The `Stmts` / `Cover` rows in [`06_04_tests_mutation_and_benchmarks.md`](06_04_tests_mutation_and_benchmarks.md) (referenced from [`06_00_experimental_setup.md`](06_00_experimental_setup.md) via `@tbl:`) are **not** generated from `METRICS.yaml`. They must be updated manually from the same canonical `uv run pytest tests/ --cov=py/cogant` run (for example `htmlcov/` or `coverage report -m`) whenever the suite or instrumentation changes, so they stay aligned with the aggregate **{{COVERAGE_PCT}}%** and **{{METRICS_GENERATED_AT}}** fields that *are* injected.

**pandoc-crossref:** install `pandoc-crossref` on your `PATH` (for example `brew install pandoc-crossref` on macOS) so `@sec:` / `@tbl:` references in the manuscript expand in the combined PDF. See [`SYNTAX.md`](SYNTAX.md).

Optional spot-check from the COGANT project root: `uv run python tools/inject_manuscript_vars.py manuscript/00_abstract.md --dry-run`

Retired monoliths (not concatenated into the PDF) may live under an `_archive/` subdirectory — for example `cogant_paper_monolith.md` or `02_methodology_monolith.md` — if and when they are brought back. No such archive ships with the current tree; see [`AGENTS.md`](AGENTS.md) for the archival convention.

## Pipeline discovery

This manuscript tree is nested next to the package as `../cogant/`. In a standalone COGANT checkout, use the local commands in this README. In the parent `docxology/template` repository, discovery-based scripts such as `scripts/03_render_pdf.py --project working/cogant` apply only after the project appears under `projects/working/cogant/` with the layout expected by the template (for this codebase: `src/`, `tests/`, and `pyproject.toml` at the project root, with the real package nested under `cogant/`).

## Validate Markdown (now)

Run locally from this COGANT project root:

```bash
uv run python tools/audit_manuscript_crossrefs.py
uv run python tools/audit_manuscript_citations.py
uv run python tools/audit_manuscript_formalisms.py --strict
uv run python tools/audit_manuscript_numbers.py
uv run python tools/audit_publication_readiness.py --strict
uv run --directory cogant python docs/verify_manuscript_links.py
```

When the project is vendored under the parent template, additionally run from the template root:

```bash
uv run python -m infrastructure.validation.cli markdown ./projects/working/cogant/manuscript/
uv run python -m infrastructure.validation.cli markdown ./projects/working/cogant/output/manuscript/
```

## COGANT package tests

The implementation and integration tests for the translator live under [`../cogant/tests/`](../cogant/tests/) (relative to this manuscript folder). From that package root:

```bash
uv run pytest tests/ -q
# Coverage gate (matches pyproject.toml addopts):
uv run pytest tests/ -q --cov=py/cogant
```

Unit coverage for GNN action fields (`effects` vs `affects_state_vars`) lives in [`../cogant/tests/unit/test_gnn_formatter_action_effects.py`](../cogant/tests/unit/test_gnn_formatter_action_effects.py).

For API and CLI details, use package docs as the authoritative reference:

- [`../cogant/docs/api/README.md`](../cogant/docs/api/README.md)
- [`../cogant/docs/cli/README.md`](../cogant/docs/cli/README.md)
- [`../cogant/docs/export/README.md`](../cogant/docs/export/README.md)
- [`../cogant/docs/evaluation/README.md`](../cogant/docs/evaluation/README.md) — R&D log and empirical reports
- [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md)

## Render PDF (after promotion)

After linking the project under `projects/working/cogant/` and wiring the manuscript path as for other template projects:

```bash
uv run python scripts/03_render_pdf.py --project working/cogant
```

## See also

- [`AGENTS.md`](AGENTS.md) — editor protocol for this folder
- [`../cogant/AGENTS.md`](../cogant/AGENTS.md) — package tree orientation (docs live under `cogant/docs/`)
- Parent template code-project manuscript docs — exemplar layout when this tree is linked under `docxology/template/projects/working/cogant/`
