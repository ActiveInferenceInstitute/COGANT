# AGENTS.md — COGANT staging scripts

Thin orchestrators only; metrics logic stays in [`../tools/`](../tools/) and [`../cogant/`](../cogant/).

| Script | Purpose |
|--------|---------|
| [`z_generate_manuscript_variables.py`](z_generate_manuscript_variables.py) | Load `METRICS.yaml`, substitute `{{VAR}}` in `manuscript/*.md`, write `output/data/manuscript_variables.json` and `output/manuscript/`, copy `config.yaml` / `references.bib` / `preamble.md`. Flags: `--regenerate-metrics` (run `tools/regenerate_metrics.py` first), `--strict` (exit non-zero on any surviving `{{PLACEHOLDER}}`; off by default because `manuscript/README.md` and `manuscript/AGENTS.md` contain literal `{{PLACEHOLDER}}` as documentation). |

Run from anywhere (paths anchored on `__file__`): `uv run python projects_in_progress/cogant/scripts/z_generate_manuscript_variables.py`.
