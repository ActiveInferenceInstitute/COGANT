# Linking COGANT for Template Rendering

The private sidecar checkout lives at:

```text
<cogant-sidecar>
```

The public template engine lives in the sibling checkout:

```text
<template-checkout>
```

The sidecar/template linker should expose this project to the template as:

```text
<template-checkout>/projects/working/cogant
```

Render commands should use the lifecycle-qualified project name:

```bash
uv run python scripts/03_render_pdf.py --project working/cogant
uv run python scripts/rerender_working_pdfs.py --project cogant
```

## Preconditions

- Manuscript templates use `{{PLACEHOLDER}}` tokens resolved from
  `cogant/evaluation/METRICS.yaml` via [`tools/manuscript_vars.py`](tools/manuscript_vars.py).
- Section figures are copied from real package outputs via
  [`tools/manuscript_figures.py`](tools/manuscript_figures.py).
- The sidecar contents must remain private unless deliberately published from a
  self-versioned COGANT repository.

## Link or Copy

From `<template-checkout>`, refresh sidecar links:

```bash
uv run python -m infrastructure.orchestration link-projects
```

If linking is unavailable, copy the whole COGANT project root into
`template/projects/working/cogant/` without changing the nested package layout.

## Validation Checklist

Run from the COGANT project root unless noted otherwise:

```bash
uv run --directory cogant python ../tools/regenerate_roundtrip_ledger.py
uv run --directory cogant python ../tools/regenerate_metrics.py
uv run python scripts/z_generate_manuscript_variables.py --strict
uv run python tools/check_metrics_fresh.py --fail-on-dirty
uv run python tools/audit_docs_constants.py
uv run python tools/audit_folder_docs.py
uv run python tools/audit_pyi_exports.py
uv run python tools/audit_stage_list.py
uv run python tools/audit_manuscript_crossrefs.py
uv run python tools/audit_manuscript_citations.py
uv run python tools/audit_manuscript_numbers.py --output /tmp/cogant_number_audit.md
uv run python tools/claim_ledger.py --manuscript-dir manuscript --output-dir /tmp/cogant_claim_ledger --fail-on-literal-numbers
uv run --directory cogant python docs/verify_manuscript_links.py
uv run pytest tests/ -q
uv run --directory cogant pytest tests/ -q
uv run --directory cogant ruff check py/cogant tests
uv run --directory cogant mypy --strict py/cogant
```

Run from the template root after linking:

```bash
uv run python -m infrastructure.validation.cli markdown projects/working/cogant/manuscript/
uv run python -m infrastructure.validation.cli markdown projects/working/cogant/output/manuscript/
uv run python scripts/03_render_pdf.py --project working/cogant
```

## Expected Layout

```text
projects/working/cogant/
├── manuscript/
├── output/
├── scripts/
├── src/
├── tests/
├── tools/
├── pyproject.toml
└── cogant/
    ├── docs/
    ├── evaluation/
    ├── py/cogant/
    ├── tests/
    └── pyproject.toml
```
