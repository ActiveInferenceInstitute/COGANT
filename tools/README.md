# tools/

Manuscript-grounding utilities. The numbers that appear in
[`../manuscript/`](../manuscript/) are written here to a single source of
truth (`../cogant/evaluation/METRICS.yaml`) and substituted into the
prose by these scripts. The same scripts gate CI to refuse stale or
unsupported claims.

| Script | One-liner |
|--------|-----------|
| [`regenerate_metrics.py`](regenerate_metrics.py) | Run `pytest` / `mypy --strict` / `ruff` / coverage against the live tree, walk the AST, and (re)write `METRICS.yaml`. |
| [`manuscript_vars.py`](manuscript_vars.py) | Library — pure functions mapping `{{TOKEN}}` placeholders to dotted paths in `METRICS.yaml`. No I/O. |
| [`inject_manuscript_vars.py`](inject_manuscript_vars.py) | CLI — substitute `{{TOKEN}}` placeholders in a file or directory. |
| [`audit_manuscript_numbers.py`](audit_manuscript_numbers.py) | Scan `manuscript/**/*.md` for raw numbers, compare to `METRICS.yaml`, fail on any MISMATCH. |
| [`check_metrics_fresh.py`](check_metrics_fresh.py) | Fast pre-commit / CI gate — confirm `METRICS.yaml` was regenerated against `HEAD` and agrees with `coverage.json`. |
| [`batch_api.py`](batch_api.py) | In-process wrappers for CLI subcommands that are still stubs in v0.5.0 (`analyze-graph`, `analyze-static`, `export`, `visualize`). Used by [`../run_all.py`](../run_all.py). |

## Common workflows

Regenerate metrics, audit the manuscript, fail on mismatch:

```bash
uv run python tools/regenerate_metrics.py
uv run python tools/audit_manuscript_numbers.py
```

Substitute `{{TOKEN}}` placeholders into the rendered manuscript:

```bash
uv run python tools/inject_manuscript_vars.py \
    --output-dir output/manuscript \
    --strict \
    manuscript/
```

Fast freshness gate (used by `metrics-fresh` GitHub Actions job):

```bash
uv run python tools/check_metrics_fresh.py
```

All scripts here are **directory-independent** — paths are anchored on
`__file__`, so any `uv run python tools/<script>.py` invocation works
from any cwd. See [`AGENTS.md`](AGENTS.md) for the full tool inventory.
