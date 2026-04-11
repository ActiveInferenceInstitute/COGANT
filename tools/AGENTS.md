# AGENTS.md — COGANT manuscript tools

| Module / script | Role |
|-----------------|------|
| [`manuscript_vars.py`](manuscript_vars.py) | `MANUSCRIPT_VARS` registry (placeholder → dotted path in `METRICS.yaml`), `resolve_path`, `format_value_for_path`, `build_flat_variables`, `substitute_text`. |
| [`inject_manuscript_vars.py`](inject_manuscript_vars.py) | CLI: substitute placeholders in a file or directory; `--report` prints resolved values. |
| [`regenerate_metrics.py`](regenerate_metrics.py) | Regenerates `cogant/evaluation/METRICS.yaml` (run from package root per that file’s docstring). |

Authoritative ground truth for prose numbers: `../cogant/evaluation/METRICS.yaml`.
