# AGENTS.md — COGANT manuscript

## Purpose

Long-form prose describing COGANT theory and practice in the same structural shape as [`projects/code_project/manuscript/`](../../../projects/code_project/manuscript/). This folder is **not** a substitute for package documentation; it synthesizes narrative for PDF/HTML output via the template rendering stack when the project is active under `projects/`.

## Canonical sources of truth

When the Python API, CLI, export schema, or implementation status changes, update **both**:

1. Package docs under [`../cogant/docs/`](../cogant/docs/) (or the paths referenced there).
2. The corresponding section here (`02_methodology.md`, `03_api_and_workflows.md`, `06_experimental_setup.md`, etc.).

Implementation status tables: [`../cogant/docs/SPEC.md`](../cogant/docs/SPEC.md).

## Files excluded from combined PDF body

Per `infrastructure/rendering/manuscript_discovery.py`, these names are **not** concatenated as sections: `preamble.md`, `AGENTS.md`, `README.md`, `config.yaml`, `config.yaml.example`, `references.bib`.

## Section ordering

Numeric prefixes `00_`–`08_` sort before supplemental `S*.md`, then `98_*`, then other `*.md` (e.g. `SYNTAX.md`), then `99_*`. Keep numbering aligned with [`../../../infrastructure/rendering/manuscript_discovery.py`](../../../infrastructure/rendering/manuscript_discovery.py).

Canonical technical references to sync when the implementation changes:

- [`../cogant/docs/SPEC.md`](../cogant/docs/SPEC.md)
- [`../cogant/docs/API_GUIDE.md`](../cogant/docs/API_GUIDE.md)
- [`../cogant/docs/CLI_GUIDE.md`](../cogant/docs/CLI_GUIDE.md)
- [`../cogant/docs/GNN_EXPORT.md`](../cogant/docs/GNN_EXPORT.md)
- [`../cogant/docs/VALIDATION.md`](../cogant/docs/VALIDATION.md)

## Citations

Keys live in `references.bib`. Use Pandoc cite syntax documented in [`SYNTAX.md`](SYNTAX.md).

## Figures

If figures are added later, follow the template figure path contract (`output/{project}/figures/` after promotion) and register paths consistent with `infrastructure/rendering` expectations.

## Pipeline caveat

Until this project is promoted under [`../../../projects/`](../../../projects/), discovery-based pipeline scripts will not target it. [`README.md`](README.md) documents manual Markdown validation and post-promotion PDF rendering.
