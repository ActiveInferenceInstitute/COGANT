# Promoting COGANT to `projects/cogant/`

The template pipeline discovers projects only under [`projects/`](../../projects/) (see `infrastructure/project/discovery.py`). This staging tree lives under `projects_in_progress/cogant/` until you move it.

## Preconditions

- Manuscript templates use `{{PLACEHOLDER}}` tokens resolved from `cogant/evaluation/METRICS.yaml` via [`tools/manuscript_vars.py`](tools/manuscript_vars.py).
- Regenerate metrics before release: from [`cogant/`](cogant/) (package root), `uv run python ../tools/regenerate_metrics.py` (paths as in that tool’s docstring).

## Move

From the repository root:

```bash
git mv projects_in_progress/cogant projects/cogant
```

Resolve any relative links in docs that still say `projects_in_progress/cogant`.

## Post-move checklist (links and validation)

1. **Search** the repository for the old path string: `rg 'projects_in_progress/cogant'` and update READMEs, scripts, and CI snippets that still hard-code the staging path.
2. **Manuscript links** (from package root): `cd projects/cogant/cogant && uv run python docs/verify_manuscript_links.py` (adjust path after move).
3. **Markdown validation** (from repository root):  
   `uv run python -m infrastructure.validation.cli markdown projects/cogant/manuscript/`  
   `uv run python -m infrastructure.validation.cli markdown projects/cogant/output/manuscript/`
4. **Regenerate** variables and injected manuscript: `uv run python projects/cogant/scripts/z_generate_manuscript_variables.py`
5. **Active projects doc** (optional): `uv run python scripts/generate_active_projects_doc.py`
6. **Optional:** After `cd projects/cogant/cogant && uv run pytest tests/ --cov=cogant`, from repo root run `uv run python projects/cogant/tools/check_coverage_table.py` (or `--strict` in CI) so @tbl:coverage-stmt-modules matches `coverage report` — see [`manuscript/AGENTS.md`](manuscript/AGENTS.md).

## Expected layout after move

The template expects each active project to have at least `src/`, `tests/`, `manuscript/`, and `pyproject.toml` at **`projects/cogant/`** (see [`projects/code_project/`](../../projects/code_project/)). COGANT keeps the **nested package** at `projects/cogant/cogant/` (implementation) alongside staging-only `tools/`, `scripts/`, and `manuscript/`.

- **Source**: Python package remains at [`cogant/py/cogant/`](cogant/py/cogant/) (import name `cogant`). A thin [`src/README.md`](src/README.md) documents the mapping; optional future refactors may symlink or relocate to `src/cogant/` to match other projects.
- **Tests**: [`cogant/tests/`](cogant/tests/) (see [`tests/README.md`](tests/README.md)).
- **Manuscript**: `projects/cogant/manuscript/` (templates); injected copy for rendering: `projects/cogant/output/manuscript/` after `z_generate_manuscript_variables.py`.

## Post-move commands

Regenerate injected manuscript and variables, validate, then render (when LaTeX is available):

```bash
uv run python projects/cogant/scripts/z_generate_manuscript_variables.py
uv run python -m infrastructure.validation.cli markdown projects/cogant/manuscript/
uv run python -m infrastructure.validation.cli markdown projects/cogant/output/manuscript/
uv run python scripts/03_render_pdf.py --project cogant
```

Update [`docs/_generated/active_projects.md`](../../docs/_generated/active_projects.md) if your workflow requires it (`uv run python scripts/generate_active_projects_doc.py`).
