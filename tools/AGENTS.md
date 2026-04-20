# AGENTS.md — COGANT manuscript tools

| Module / script | Role |
|-----------------|------|
| [`manuscript_vars.py`](manuscript_vars.py) | `MANUSCRIPT_VARS` registry (placeholder → dotted path in `METRICS.yaml`), `resolve_path`, `format_value_for_path`, `build_flat_variables`, `substitute_text`, `find_unresolved_placeholders`. Pure / no I/O. |
| [`inject_manuscript_vars.py`](inject_manuscript_vars.py) | CLI: substitute placeholders in a file or directory. Flags: `--dry-run`, `--report`, `--output`, `--output-dir`, `--all`, `--strict` (fail on unresolved `{{TOKEN}}`). |
| [`regenerate_metrics.py`](regenerate_metrics.py) | Regenerates `cogant/evaluation/METRICS.yaml` from the live repo (`pytest tests/` with `--no-cov` so default `addopts` coverage gates do not fire; mypy, ruff, coverage.json, AST walk, roundtrip JSONL). Directory-independent; paths anchored on `__file__`. |
| [`audit_manuscript_numbers.py`](audit_manuscript_numbers.py) | Scans `manuscript/**/*.md` for numeric claims, compares to METRICS.yaml, writes a Markdown report, exits 1 on MISMATCH. |
| [`check_metrics_fresh.py`](check_metrics_fresh.py) | Fast freshness gate: verifies METRICS.yaml `coverage_percent` agrees with `coverage.json` (±0.1 pp) and `generator_git_sha` equals HEAD. |

Authoritative ground truth for prose numbers: `../cogant/evaluation/METRICS.yaml`.

All CLIs in this directory are directory-independent — paths are anchored on `__file__`, so `uv run python tools/<script>.py` works from any cwd.
