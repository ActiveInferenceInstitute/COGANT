# scripts/

Thin staging-root orchestrators. Heavy lifting stays in
[`../tools/`](../tools/) and [`../cogant/`](../cogant/) — the scripts
here are glue that wires them together for end-to-end runs.

| Script | Purpose |
|--------|---------|
| [`z_generate_manuscript_variables.py`](z_generate_manuscript_variables.py) | Load `METRICS.yaml`, substitute `{{VAR}}` placeholders into `manuscript/*.md`, emit `output/data/manuscript_variables.json` plus a fully-populated `output/manuscript/` tree (including `config.yaml`, `references.bib`, and `preamble.md`), and refresh `output/figures/` from package-generated PNGs. Flags: `--regenerate-metrics`, `--strict`. |
| [`batch_dashboard.py`](batch_dashboard.py) | Cross-target dashboard generator — reads `<output_root>/run_manifest.json` plus each per-target `bundle.json` and writes `<output_root>/dashboard/` (Markdown report, CSV, JSON, four Mermaid charts). Calls `cogant.viz.batch_dashboard.BatchDashboardGenerator`. Flags: `--output-root`, `--dashboard-dir`, `--manifest`, `--quiet`. See [`../cogant/docs/reference/batch_dashboard.md`](../cogant/docs/reference/batch_dashboard.md). |
| [`../run_all.py`](../run_all.py) | Staging-root sweep — run the configured COGANT chain over every target listed in `run_all.json` (or the embedded `DEFAULT_CONFIG`). The default output root is `cogant/output`; target directories are `<output_root>/<id>/`. The core order is export/render/viz/validate, followed by enabled post-validate steps such as roundtrip, API analysis/export, diagram/inspection artifacts, and batch dashboard generation. Local targets resolve via `path`; remote targets are cloned to `_git_source/` from `git_url`. Entry point: [`../run_all.sh`](../run_all.sh) (works from staging root or inner `cogant/`). |

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
