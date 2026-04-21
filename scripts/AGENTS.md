# AGENTS.md — COGANT staging scripts

Thin orchestrators only; metrics logic stays in [`../tools/`](../tools/) and [`../cogant/`](../cogant/).

| Script | Purpose |
|--------|---------|
| [`z_generate_manuscript_variables.py`](z_generate_manuscript_variables.py) | Load `METRICS.yaml`, substitute `{{VAR}}` in `manuscript/*.md`, write `output/data/manuscript_variables.json` and `output/manuscript/`, copy `config.yaml` / `references.bib` / `preamble.md`. Flags: `--regenerate-metrics` (run `tools/regenerate_metrics.py` first), `--strict` (exit non-zero on any surviving `{{PLACEHOLDER}}`; off by default because `manuscript/README.md` contains literal `{{PLACEHOLDER}}` as documentation). |
| [`../run_all.py`](../run_all.py) | Staging-root orchestrator: JSON config (`run_all.json` / `run_all.example.json`) runs the full CLI chain per target into `cogant/output/<id>/` (the inner `cogant/` package owns the `output/` tree). Local targets use `path`; remotes use `git_url` (clone to `_git_source/`). Entry: [`../run_all.sh`](../run_all.sh) (works from staging root or inner `cogant/`). Optional `manuscript` block invokes this manuscript script. |

Run from anywhere (paths anchored on `__file__`): `uv run python projects_in_progress/cogant/scripts/z_generate_manuscript_variables.py`.
