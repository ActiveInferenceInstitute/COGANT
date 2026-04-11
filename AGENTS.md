# AGENTS.md — `projects_in_progress/cogant/`

## Layout

| Path | Role |
|------|------|
| [`cogant/`](cogant/) | Nested COGANT package (`py/cogant/`, `tests/`, `pyproject.toml`, Rust crates, docs). |
| [`manuscript/`](manuscript/) | PDF/HTML manuscript templates (`{{PLACEHOLDER}}` syntax). |
| [`tools/`](tools/) | Metrics regeneration, `MANUSCRIPT_VARS` registry, inject CLI. |
| [`scripts/`](scripts/) | Thin orchestrators (`z_generate_manuscript_variables.py`). |
| [`output/`](output/) | Generated `data/manuscript_variables.json`, `output/manuscript/` injected copy (disposable). |
| [`src/`](src/) | Compatibility note only; real package under `cogant/py/cogant/`. |
| [`tests/`](tests/) | Compatibility note; real suite under `cogant/tests/`. |
| [`PROMOTION.md`](PROMOTION.md) | Steps to move to `projects/cogant/`. |

## Key APIs (tools)

- `tools/manuscript_vars.py` — `MANUSCRIPT_VARS`, `resolve_path`, `format_value_for_path`, `build_flat_variables`, `substitute_text`.
- `tools/inject_manuscript_vars.py` — CLI to substitute one file or directory (dry-run supported).
- `scripts/z_generate_manuscript_variables.py` — Writes JSON + full `output/manuscript/` tree for rendering.

Authoritative numbers: `cogant/evaluation/METRICS.yaml` (from `tools/regenerate_metrics.py`).

## Discovery

Not in `discover_projects()` until promoted; see [`PROMOTION.md`](PROMOTION.md).
