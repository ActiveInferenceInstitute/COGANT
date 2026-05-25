# AGENTS.md — COGANT manuscript tools

| Module / script | Role |
|-----------------|------|
| [`manuscript_vars.py`](manuscript_vars.py) | `MANUSCRIPT_VARS` registry (placeholder → dotted path in `METRICS.yaml`), `resolve_path`, `format_value_for_path`, `build_flat_variables`, `substitute_text`, `find_unresolved_placeholders`. Pure / no I/O. |
| [`inject_manuscript_vars.py`](inject_manuscript_vars.py) | CLI: substitute placeholders in a file or directory. Flags: `--dry-run`, `--report`, `--output`, `--output-dir`, `--all`, `--strict` (fail on unresolved `{{TOKEN}}`). |
| [`regenerate_metrics.py`](regenerate_metrics.py) | Regenerates `cogant/evaluation/METRICS.yaml` from the live repo (`pytest tests/` with `--no-cov` so default `addopts` coverage gates do not fire; mypy, ruff, coverage.json, AST walk, roundtrip JSONL). Directory-independent; paths anchored on `__file__`. |
| [`audit_manuscript_citations.py`](audit_manuscript_citations.py) | Citation-integrity gate: scans rendered-body Markdown for Pandoc citation keys, ignores crossrefs and code blocks, and fails on missing or duplicate `references.bib` keys. |
| [`audit_manuscript_numbers.py`](audit_manuscript_numbers.py) | Scans `manuscript/**/*.md` for numeric claims, compares to METRICS.yaml, writes a Markdown report, exits 1 on MISMATCH. |
| [`check_metrics_fresh.py`](check_metrics_fresh.py) | Fast freshness gate: verifies METRICS.yaml `coverage_percent` agrees with `coverage.json` (±0.1 pp), `generator_git_sha` equals HEAD, roundtrip status counters match the JSONL ledger, and `--fail-on-dirty` rejects uncommitted metric provenance. |
| [`claim_ledger.py`](claim_ledger.py) | Manuscript claim inventory over rendered body files; includes placeholders, citations, figures, artifact paths, and literal numeric prose, with `--fail-on-literal-numbers` available for strict release review. |
| [`batch_api.py`](batch_api.py) | In-process wrappers (subcommands: `graph-analysis`, `static-analysis`, `multi-export`, `visualize`) that call the real package APIs behind `cogant analyze-graph`, `cogant analyze-static`, `cogant export`, and `cogant visualize`. Used by [`../run_all.py`](../run_all.py) so the per-target output set is complete today. Each subcommand writes files under `--run-dir` and prints absolute paths to stdout, one per line, for subprocess parsing. |
| [`manuscript_figures.py`](manuscript_figures.py) | Curated figure registry + copier: moves package-generated and evaluation PNGs from registered COGANT artifacts into `../output/figures/`, writes `manifest.json` plus per-figure `.figure.json` sidecars, and optionally fails with `--strict` if a registered publication figure is missing or lacks required metadata / visual QA. |
| [`audit_test_names.py`](audit_test_names.py) | Active test/example naming audit. Rejects campaign labels (campaign numbers, dated batch tags, opaque coverage-only suffixes) so tests stay organized by behavior and subsystem. |
| [`audit_folder_docs.py`](audit_folder_docs.py) | Project-owned folder documentation audit. Checks README/AGENTS coverage, placeholder boilerplate, documented exceptions, and relative links while excluding vendored evaluation repositories and build outputs. |

Authoritative ground truth for prose numbers: `../cogant/evaluation/METRICS.yaml`.

All CLIs in this directory are directory-independent — paths are anchored on `__file__`, so `uv run python tools/<script>.py` works from any cwd.
