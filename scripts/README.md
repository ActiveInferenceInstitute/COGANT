# scripts/

Thin staging-root orchestrators. Heavy lifting stays in
[`../tools/`](../tools/) and [`../cogant/`](../cogant/) — the scripts
here are glue that wires them together for end-to-end runs.

| Script | Purpose |
|--------|---------|
| [`z_generate_manuscript_variables.py`](z_generate_manuscript_variables.py) | Load `METRICS.yaml`, substitute `{{VAR}}` placeholders into `manuscript/*.md`, and emit `output/data/manuscript_variables.json` plus a fully-populated `output/manuscript/` tree (including `config.yaml`, `references.bib`, and `preamble.md`). Flags: `--regenerate-metrics`, `--strict`. |
| [`../run_all.py`](../run_all.py) | Staging-root sweep — run the full COGANT CLI chain (`translate`, `scan`, `graph`, `validate`, `export-gnn`, `render`, `viz`, optional `explain`) over every target listed in `run_all.json` (or the embedded `DEFAULT_CONFIG`). Local targets resolve via `path`; remote targets are cloned to `_git_source/` from `git_url`. Outputs land under `cogant/output/<id>/`. Entry point: [`../run_all.sh`](../run_all.sh) (works from staging root or inner `cogant/`). |

## Quickstart

Generate the manuscript variables, regenerating metrics first:

```bash
uv run python scripts/z_generate_manuscript_variables.py --regenerate-metrics --strict
```

Sweep every configured codebase end-to-end:

```bash
./run_all.sh
```

The `z_` prefix on `z_generate_manuscript_variables.py` keeps the script
last when sorted alphabetically — it is intentionally the final stage in
the manuscript pipeline. Paths are anchored on `__file__`, so the
script runs identically from any cwd. See [`AGENTS.md`](AGENTS.md) for
the rationale and full flag reference.
