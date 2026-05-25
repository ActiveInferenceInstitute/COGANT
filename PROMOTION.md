# Promoting COGANT to `projects/cogant/`

The template pipeline discovers projects only under `projects/` (see `infrastructure/project/discovery.py`). This document describes how to place a COGANT checkout at `projects/cogant/` inside `docxology/template`; the old `projects_in_progress/cogant/` path is historical staging context, not the default workflow for this passive checkout.

## Location matrix

| Context | COGANT project root | COGANT package root | Promotion status |
| --- | --- | --- | --- |
| Passive standalone checkout | `/Users/4d/Documents/GitHub/projects/passive/cogant` | `/Users/4d/Documents/GitHub/projects/passive/cogant/cogant` | Local package/manuscript work; template discovery inactive. |
| Active parent-template project | `docxology/template/projects/cogant` | `docxology/template/projects/cogant/cogant` | Target location for template discovery and PDF rendering. |
| Historical staging path | `docxology/template/projects_in_progress/cogant` | `docxology/template/projects_in_progress/cogant/cogant` | Legacy move source only; update old literals during promotion. |

## Preconditions

- Manuscript templates use `{{PLACEHOLDER}}` tokens resolved from `cogant/evaluation/METRICS.yaml` via [`tools/manuscript_vars.py`](tools/manuscript_vars.py), and Section 4 figures are copied from real package outputs via [`tools/manuscript_figures.py`](tools/manuscript_figures.py).
- The claim ledger, dashboard QA, and manuscript figures are generated tools:
  `uv run python projects/cogant/tools/claim_ledger.py`,
  `uv run python projects/cogant/scripts/dashboard_browser_qa.py <dashboard.html>`,
  and `uv run python projects/cogant/tools/manuscript_figures.py --strict`
  after outputs exist.
- The v0.6 drift gates are generated tools:
  `uv run python projects/cogant/tools/audit_docs_constants.py`,
  `uv run python projects/cogant/tools/audit_folder_docs.py`,
  `uv run python projects/cogant/tools/audit_pyi_exports.py`, and
  `uv run python projects/cogant/tools/audit_stage_list.py` (enforces
  the canonical `cogant.pipeline.RUNNER_STAGES` tuple against every
  documented full-pipeline stage list in docs/CLI docstrings/manuscript;
  paired with `tests/test_audit_stage_list.py` + CI step in
  `.github/workflows/ci.yml`).
- Regenerate metrics before release from the COGANT project root: `uv run --directory cogant python ../tools/regenerate_metrics.py` (equivalent to running `uv run python ../tools/regenerate_metrics.py` from the inner package root).

## Move

If the tree still lives at the historical staging path, run this from the parent template repository root:

```bash
git mv projects_in_progress/cogant projects/cogant
```

If you are starting from the passive standalone checkout instead, copy or move the whole COGANT project root into `docxology/template/projects/cogant/` without changing the nested package layout. Resolve any relative links in docs that still say `projects_in_progress/cogant`.

## Post-move checklist (links and validation)

1. **Search** the repository for the old path string: `rg 'projects_in_progress/cogant'` and update READMEs, scripts, and CI snippets that still hard-code the staging path.
2. **Manuscript links** (from repository root): `uv run --directory projects/cogant/cogant python docs/verify_manuscript_links.py`.
3. **Markdown validation** (from repository root):  
   `uv run python -m infrastructure.validation.cli markdown projects/cogant/manuscript/`  
   `uv run python -m infrastructure.validation.cli markdown projects/cogant/output/manuscript/`
4. **Regenerate** variables, injected manuscript, and copied figures: `uv run python projects/cogant/scripts/z_generate_manuscript_variables.py`
5. **Claim ledger**: `uv run python projects/cogant/tools/claim_ledger.py` and inspect `projects/cogant/output/claim_ledger.md` for unsupported literal claims.
6. **Docs/constants audit**: `uv run python projects/cogant/tools/audit_docs_constants.py`.
7. **Folder documentation audit**: `uv run python projects/cogant/tools/audit_folder_docs.py`.
8. **Stub export audit**: `uv run python projects/cogant/tools/audit_pyi_exports.py`.
9. **Stage-list drift gate**: `uv run python projects/cogant/tools/audit_stage_list.py` (must exit 0; pinned by `projects/cogant/tests/test_audit_stage_list.py`).
10. **Dashboard QA**: after a sample `run_all.py` or calculator run, `uv run python projects/cogant/scripts/dashboard_browser_qa.py projects/cogant/cogant/output/calculator/site/inspection_dashboard.html --output-dir projects/cogant/cogant/output/calculator/dashboard_qa`.
11. **Active projects doc** (optional): `uv run python scripts/generate_active_projects_doc.py`
12. **Optional:** After `cd projects/cogant/cogant && uv run pytest tests/ --cov=py/cogant`, from repo root run `uv run python projects/cogant/tools/check_coverage_table.py` (or `--strict` in CI) so @tbl:coverage-stmt-modules matches `coverage report` — see [`manuscript/AGENTS.md`](manuscript/AGENTS.md).

## Expected layout after move

The template expects each active project to have at least `src/`, `tests/`,
`manuscript/`, and `pyproject.toml` at **`projects/cogant/`**.
COGANT satisfies that contract with a tiny top-level template shell while
keeping the real Python/Rust package nested at `projects/cogant/cogant/`.

- **Template shell**: [`src/`](src/), [`tests/`](tests/), and
  [`pyproject.toml`](pyproject.toml) exist so `discover_projects()` and
  template-level tests have a real source/test surface after promotion.
- **Source**: the installable Python package remains at
  [`cogant/py/cogant/`](cogant/py/cogant/) (import name `cogant`).
- **Package tests**: [`cogant/tests/`](cogant/tests/) is the full package
  suite. The top-level [`tests/`](tests/) only checks the template shell.
- **Manuscript**: `projects/cogant/manuscript/` (templates); injected copy
  for rendering: `projects/cogant/output/manuscript/` and copied PNG assets
  under `projects/cogant/output/figures/` after
  `z_generate_manuscript_variables.py`.

## Post-move commands

Regenerate injected manuscript and variables, validate, then render (when LaTeX is available):

```bash
uv run python projects/cogant/scripts/z_generate_manuscript_variables.py
uv run python projects/cogant/tools/audit_docs_constants.py
uv run python projects/cogant/tools/audit_folder_docs.py
uv run python projects/cogant/tools/audit_pyi_exports.py
uv run python -m infrastructure.validation.cli markdown projects/cogant/manuscript/
uv run python -m infrastructure.validation.cli markdown projects/cogant/output/manuscript/
uv run python scripts/03_render_pdf.py --project cogant
```

Update [`docs/_generated/active_projects.md`](../../docs/_generated/active_projects.md) if your workflow requires it (`uv run python scripts/generate_active_projects_doc.py`).
