# COGANT (staging)

Codebase-to-GNN translation — **package** under [`cogant/`](cogant/), **manuscript** under [`manuscript/`](manuscript/). This directory is staged in `projects_in_progress/` until moved to [`projects/cogant/`](../cogant/) ([`PROMOTION.md`](PROMOTION.md)).

## Manuscript variables (madlib)

1. Regenerate metrics (from package root [`cogant/`](cogant/)): `uv run python ../tools/regenerate_metrics.py`
2. Generate JSON + injected manuscript (from repo root):  
   `uv run python projects_in_progress/cogant/scripts/z_generate_manuscript_variables.py`
3. Validate:  
   `uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/manuscript/`  
   `uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/output/manuscript/`

Rendering uses `output/manuscript/` when present (see `infrastructure/rendering/pipeline.py`). Full pipeline PDF requires promotion and `scripts/03_render_pdf.py --project cogant`.

## See also

- [`manuscript/README.md`](manuscript/README.md) — section index and validation commands
- [`cogant/README.md`](cogant/README.md) — package overview
