# AGENTS.md — COGANT staging scripts

Thin orchestrators only; metrics logic stays in [`../tools/`](../tools/) and [`../cogant/`](../cogant/).

| Script | Purpose |
|--------|---------|
| [`z_generate_manuscript_variables.py`](z_generate_manuscript_variables.py) | Load `METRICS.yaml`, substitute `{{VAR}}` in `manuscript/*.md`, write `output/data/manuscript_variables.json` and `output/manuscript/`, copy `config.yaml` / `references.bib` / `preamble.md`. |

Run from repository root: `uv run python projects_in_progress/cogant/scripts/z_generate_manuscript_variables.py`.
