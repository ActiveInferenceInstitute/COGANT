# AGENTS.md — COGANT manuscript tools

| Module / script | Role |
|-----------------|------|
| [`manuscript_vars.py`](manuscript_vars.py) | `MANUSCRIPT_VARS` registry (placeholder → dotted path in `METRICS.yaml`), `resolve_path`, `format_value_for_path`, `build_flat_variables`, `substitute_text`, `find_unresolved_placeholders`. Pure / no I/O. |
| [`inject_manuscript_vars.py`](inject_manuscript_vars.py) | CLI: substitute placeholders in a file or directory. Flags: `--dry-run`, `--report`, `--output`, `--output-dir`, `--all`, `--strict` (fail on unresolved `{{TOKEN}}`). |
| [`regenerate_metrics.py`](regenerate_metrics.py) | Regenerates `cogant/evaluation/METRICS.yaml` from the live repo (`pytest tests/` with `--no-cov` so default `addopts` coverage gates do not fire; mypy, ruff, coverage.json, AST walk, roundtrip JSONL). Directory-independent; paths anchored on `__file__`. |
| [`audit_manuscript_citations.py`](audit_manuscript_citations.py) | Citation-integrity gate: scans rendered-body Markdown for Pandoc citation keys, ignores crossrefs and code blocks, and fails on missing or duplicate `references.bib` keys. |
| [`audit_manuscript_numbers.py`](audit_manuscript_numbers.py) | Scans `manuscript/**/*.md` for numeric claims, compares to METRICS.yaml, writes a Markdown report, exits 1 on MISMATCH. |
| [`audit_manuscript_math_adjacency.py`](audit_manuscript_math_adjacency.py) | Resolves manuscript variables and rejects inline math spans whose closing `$` is immediately followed by a digit, catching Pandoc leaks such as `$-$10`. |
| [`audit_manuscript_claim_scope.py`](audit_manuscript_claim_scope.py) | Rejects high-risk claim wording when it lacks a local caveat: positive guarantees, inferential-statistics language, and semantic-totality claims. |
| [`audit_robustness_table.py`](audit_robustness_table.py) | Verifies the manuscript robustness table against `cogant/evaluation/robustness/robustness_results.json`. |
| [`audit_roadmap_truth.py`](audit_roadmap_truth.py) | Roadmap truth gate: rejects out-of-sync current-version labels, unsupported benchmark fixture/stage claims, and TODO/task drift for the active refactor tranche. |
| [`citation_claim_ledger.py`](citation_claim_ledger.py) | Emits JSONL claim/source pairs for selected citation keys so high-risk citation-backed statements can be reviewed explicitly. |
| [`check_metrics_fresh.py`](check_metrics_fresh.py) | Fast freshness gate: verifies METRICS.yaml `coverage_percent` agrees with `coverage.json` (±0.1 pp), `generator_git_sha` equals HEAD, roundtrip status counters match the JSONL ledger, and `--fail-on-dirty` rejects uncommitted metric provenance. |
| [`claim_ledger.py`](claim_ledger.py) | Manuscript claim inventory over rendered body files; includes placeholders, citations, figures, artifact paths, and literal numeric prose, with `--fail-on-literal-numbers` available for strict release review. |
| [`manuscript_evidence_audit.py`](manuscript_evidence_audit.py) | Section-level evidence matrix over source manuscript fragments; counts citation, metric-token, figure, artifact, validator, and boundary-language lanes, ranks the thinnest sections, emits non-fatal reviewer actions, and writes JSON / Markdown / PNG review artifacts. |
| [`manuscript_review_dashboard.py`](manuscript_review_dashboard.py) | Combined review dashboard over figure QA, section evidence, claim ledger, figure manifest outputs, and the evidence review queue; writes JSON / Markdown / PNG and can fail strict runs when any component surface is red. |
| [`batch_api.py`](batch_api.py) | In-process wrappers (subcommands: `graph-analysis`, `static-analysis`, `multi-export`, `visualize`) that call the real package APIs behind `cogant analyze-graph`, `cogant analyze-static`, `cogant export`, and `cogant visualize`. Used by [`../run_all.py`](../run_all.py) so the per-target output set is complete today. Each subcommand writes files under `--run-dir` and prints absolute paths to stdout, one per line, for subprocess parsing. |
| [`manuscript_figures.py`](manuscript_figures.py) | Curated figure registry + copier: moves package-generated and evaluation PNGs from registered COGANT artifacts into `../output/figures/`, writes `manifest.json` plus per-figure `.figure.json` sidecars, and optionally fails with `--strict` if a registered publication figure is missing or lacks required metadata / visual QA. |
| [`visualization_quality_audit.py`](visualization_quality_audit.py) | Reads the promoted figure manifest and sidecars, writes JSON / Markdown / PNG review artifacts, and optionally fails with `--strict` if a publication figure has missing visual QA, source evidence, degraded renderer metadata, or unreadable dimensions. |
| [`audit_test_names.py`](audit_test_names.py) | Active test/example naming audit. Rejects campaign labels (campaign numbers, dated batch tags, opaque coverage-only suffixes) so tests stay organized by behavior and subsystem. |
| [`audit_folder_docs.py`](audit_folder_docs.py) | Project-owned folder documentation audit. Checks README/AGENTS coverage, placeholder boilerplate, documented exceptions, and relative links while excluding vendored evaluation repositories and build outputs. |
| [`audit_synthetic_surfaces.py`](audit_synthetic_surfaces.py) | Classifies retained `fallback` / `mock` / `placeholder` / `stub` occurrences in tracked project files and, with `--strict`, verifies generated manuscript and matrix provenance artifacts. |

Authoritative ground truth for prose numbers: `../cogant/evaluation/METRICS.yaml`.

All CLIs in this directory are directory-independent — paths are anchored on `__file__`, so `uv run python tools/<script>.py` works from any cwd.

`manuscript_figures.py` is intentionally a small compatibility wrapper. Keep
the implementation split under `figures/` by concern: PNG inspection,
publication renderers, sidecar/metadata validation, and copy-manifest
orchestration. Preserve compatibility renderer symbols re-exported by the wrapper.
