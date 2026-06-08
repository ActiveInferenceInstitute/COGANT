# AGENTS.md — COGANT scripts

Thin orchestrators only; metrics logic stays in [`../tools/`](../tools/) and [`../cogant/`](../cogant/).

| Script | Purpose |
|--------|---------|
| [`z_generate_manuscript_variables.py`](z_generate_manuscript_variables.py) | Load `METRICS.yaml`, substitute `{{VAR}}` in `manuscript/*.md`, write `output/data/manuscript_variables.json` and `output/manuscript/`, copy `config.yaml` / `references.bib` / `preamble.md`, and refresh `output/figures/` via `tools/manuscript_figures.py`. Flags: `--regenerate-metrics` (run `tools/regenerate_metrics.py` first), `--strict` (exit non-zero on any surviving `{{PLACEHOLDER}}`; off by default because `manuscript/README.md` contains literal `{{PLACEHOLDER}}` as documentation). |
| [`batch_dashboard.py`](batch_dashboard.py) | Build `output/dashboard/` from a `run_all.py` output root: `summary.csv`, `metrics_per_target.json`, `dashboard.md`, and Mermaid charts. Used by `run_all.py` when `steps.batch_dashboard` is true; accepts paths relative to the project root or current cwd. |
| [`../run_all.py`](../run_all.py) | Project-root orchestrator: JSON config (`run_all.json` / `run_all.example.json`) runs the full CLI chain per target into `cogant/output/<id>/` (the inner `cogant/` package owns the `output/` tree). Local targets use `path`; remotes use `git_url` (clone to `_git_source/`). Entry: [`../run_all.sh`](../run_all.sh) (works from project root or inner `cogant/`). Optional `manuscript` block invokes this manuscript script. |

Run from anywhere (paths anchored on `__file__`): `uv run python scripts/z_generate_manuscript_variables.py` from this project root, or `uv run python projects/working/cogant/scripts/z_generate_manuscript_variables.py` from the parent template root after linking.
