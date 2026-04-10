# COGANT manuscript

Template-aligned Markdown for **COGANT** (Codebase-to-GNN Translation): theory of the program graph IR and practice of the Python/Rust pipeline. Authoritative API, CLI, export schema, and plugin docs remain in the package tree:

[`../cogant/docs/index.md`](../cogant/docs/index.md) (MkDocs site home; narrative entry) and [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md) (module map). Implementation scope: [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md).

## Section files

Stem order follows [`../../../infrastructure/rendering/manuscript_discovery.py`](../../../infrastructure/rendering/manuscript_discovery.py): digit-prefixed names sort lexicographically, so `02_01_…` fragments appear before `03_…`, and `06_01_…` before `07_…`.

| Files | Contents |
|------|-----------|
| `00_abstract.md` | Problem, approach, scope |
| `01_introduction.md` | Motivation, terminology, documentation map |
| `02_01_program_graph_and_formal_foundations.md` | Program graph, definitions, theorems |
| `02_02_ir_progression_translation_engine.md` | Progressive IRs, rules, fixpoint, algorithms |
| `02_03_confidence_state_space_and_behavior.md` | Confidence model, state-space compilation, example |
| `02_04_gnn_export_and_error_handling.md` | GNN export contract and error philosophy |
| `03_api_and_workflows.md` | Session, pipeline, bundle, CLI, Review API |
| `04_examples_and_failure_modes.md` | End-to-end examples and degradation behavior |
| `05_conclusion.md` | Capabilities, limitations, roadmap |
| `06_01_environment_api_and_config.md` | Environment, Session/Pipeline snippets, YAML config, CLI |
| `06_02_exports_parser_and_ir_stages.md` | Export targets, Python parser, IR stage table |
| `06_03_performance_and_fixture_metrics.md` | Performance targets, fixture tables |
| `06_04_tests_mutation_and_benchmarks.md` | Test matrix, mutation notes, benchmark harness |
| `06_05_reproducible_recording.md` | What to record for reproducibility |
| `07_reproducibility.md` | Versioning, determinism, validation gates |
| `08_01_landscape_and_tool_categories.md` | Landscape and tool categories |
| `08_02_program_analysis_for_ml_and_tables.md` | ML-related work and feature / I/O tables |
| `08_03_lenses_and_synthesis.md` | Lenses, synthesis, categorical framing |
| `08_04_world_models_boundaries_and_compatibility.md` | World models, active inference, boundaries |
| `09_ablation.md` | Rule-family and matrix ablations |

**Supplemental appendices** (`S01_`–`S06_`): see [`supplementary.md`](supplementary.md) for the index.

Supporting files: `config.yaml`, `preamble.md`, `references.bib`, `SYNTAX.md`.

**Abstract metrics.** Counts in `00_abstract.md` (tests passed, coverage %) drift with every suite change — refresh them when cutting a release by running `uv run pytest tests/ -q` from [`../cogant/`](../cogant/) and copying the summary line plus `pytest --cov` totals.

Retired monoliths (not concatenated into the PDF) may live under [`_archive/`](_archive/) — for example `cogant_paper_monolith.md` or `02_methodology_monolith.md` if present.

## Pipeline discovery

This tree is typically nested next to the package as `../cogant/`; it is **not** listed by `infrastructure.project.discovery.discover_projects()` until promoted. Root scripts such as `scripts/03_render_pdf.py --project cogant` apply only after COGANT lives under [`../../../projects/cogant/`](../../../projects/cogant/) with the layout expected by the template (for this codebase: `py/`, `tests/`, and `pyproject.toml` at the package root — see [`../cogant/AGENTS.md`](../cogant/AGENTS.md)).

## Validate Markdown (now)

Run from the **repository root** (the directory that contains `infrastructure/` and the root `pyproject.toml`), using a path relative to that root:

```bash
uv run python -m infrastructure.validation.cli markdown ./projects_in_progress/cogant/manuscript/
```

## COGANT package tests

The implementation and integration tests for the translator live under [`../cogant/tests/`](../cogant/tests/) (relative to this manuscript folder). From that package root:

```bash
uv run pytest tests/ -q
```

Unit coverage for GNN action fields (`effects` vs `affects_state_vars`) lives in [`../cogant/tests/unit/test_gnn_formatter_action_effects.py`](../cogant/tests/unit/test_gnn_formatter_action_effects.py).

For API and CLI details, use package docs as the authoritative reference:

- [`../cogant/docs/api/README.md`](../cogant/docs/api/README.md)
- [`../cogant/docs/cli/README.md`](../cogant/docs/cli/README.md)
- [`../cogant/docs/export/README.md`](../cogant/docs/export/README.md)
- [`../cogant/docs/evaluation/README.md`](../cogant/docs/evaluation/README.md) — R&D log and empirical reports
- [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md)

## Render PDF (after promotion)

After moving the project under `projects/cogant/` and wiring the manuscript path as for other template projects:

```bash
uv run python scripts/03_render_pdf.py --project cogant
```

## See also

- [`AGENTS.md`](AGENTS.md) — editor protocol for this folder
- [`../cogant/AGENTS.md`](../cogant/AGENTS.md) — package tree orientation (docs live under `cogant/docs/`)
- [`../../../projects/code_project/manuscript/README.md`](../../../projects/code_project/manuscript/README.md) — exemplar manuscript layout
