# COGANT manuscript

Template-aligned Markdown for **COGANT** (Codebase-to-GNN Translation): theory of the program graph IR and practice of the Python/Rust pipeline. Authoritative API, CLI, export schema, and plugin docs remain in the package tree:

`../cogant/docs/` (start with `README.md` in that folder).

## Section files

| File | Contents |
|------|-----------|
| `00_abstract.md` | Problem, approach, scope |
| `01_introduction.md` | Motivation and pointer to package docs |
| `02_methodology.md` | IR progression, graph, rules, export |
| `03_api_and_workflows.md` | Session, pipeline, bundle, CLI, examples |
| `04_examples_and_failure_modes.md` | End-to-end example outputs and degradation behavior |
| `05_conclusion.md` | Limitations, intended users, and roadmap |
| `06_experimental_setup.md` | How to run API/CLI and exports |
| `07_reproducibility.md` | Versioning, determinism, validation, and artifact integrity |
| `08_scope_and_related_work.md` | Related research and tool boundaries |

Supporting files: `config.yaml`, `preamble.md`, `references.bib`, `SYNTAX.md`.

## Pipeline discovery

This tree is typically nested next to the package as `../cogant/`; it is **not** listed by `infrastructure.project.discovery.discover_projects()` until promoted. Root scripts such as `scripts/03_render_pdf.py --project cogant` apply only after COGANT lives under [`../../../projects/cogant/`](../../../projects/cogant/) with the required `src/`, `tests/`, and `pyproject.toml` layout.

## Validate Markdown (now)

Run from the **repository root** (the directory that contains `infrastructure/` and the root `pyproject.toml`), using a path relative to that root:

```bash
uv run python -m infrastructure.validation.cli markdown ./projects_in_progress/cogant/manuscript/
```

## COGANT package tests (in progress)

The implementation and integration tests for the translator live under [`../cogant/tests/`](../cogant/tests/) (relative to this manuscript folder). From that package root:

```bash
uv run pytest tests/ -q
```

Unit coverage for GNN action fields (`effects` vs `affects_state_vars`) lives in [`../cogant/tests/unit/test_gnn_formatter_action_effects.py`](../cogant/tests/unit/test_gnn_formatter_action_effects.py).

For API and CLI details, use package docs as the authoritative reference:

- [`../cogant/docs/API_GUIDE.md`](../cogant/docs/API_GUIDE.md)
- [`../cogant/docs/CLI_GUIDE.md`](../cogant/docs/CLI_GUIDE.md)
- [`../cogant/docs/GNN_EXPORT.md`](../cogant/docs/GNN_EXPORT.md)
- [`../cogant/docs/SPEC.md`](../cogant/docs/SPEC.md)

## Render PDF (after promotion)

After moving the project under `projects/cogant/` and wiring the manuscript path as for other template projects:

```bash
uv run python scripts/03_render_pdf.py --project cogant
```

## See also

- [`AGENTS.md`](AGENTS.md) — editor protocol
- [`../../../projects/code_project/manuscript/README.md`](../../../projects/code_project/manuscript/README.md) — exemplar manuscript layout
