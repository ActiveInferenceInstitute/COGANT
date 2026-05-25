# tools/

Manuscript-grounding utilities. The numbers that appear in
[`../manuscript/`](../manuscript/) are written here to a single source of
truth (`../cogant/evaluation/METRICS.yaml`) and substituted into the
prose by these scripts. The gates refuse stale metrics and numeric
mismatches; the claim ledger inventories unsupported literal claims for
review and can be made stricter with its release-only flags.

| Script | One-liner |
|--------|-----------|
| [`regenerate_metrics.py`](regenerate_metrics.py) | Run `pytest` / `mypy --strict` / `ruff` / coverage against the live tree, walk the AST, and (re)write `METRICS.yaml`. |
| [`regenerate_ablation.py`](regenerate_ablation.py) | Run the live translation/state-space/matrix pipeline on the 6 packaged fixtures and (re)write the `ablation:` block in `METRICS.yaml`. |
| [`manuscript_vars.py`](manuscript_vars.py) | Library — pure functions mapping `{{TOKEN}}` placeholders to dotted paths in `METRICS.yaml`. No I/O. |
| [`inject_manuscript_vars.py`](inject_manuscript_vars.py) | CLI — substitute `{{TOKEN}}` placeholders in a file or directory. |
| [`audit_manuscript_citations.py`](audit_manuscript_citations.py) | Verify Pandoc citation keys used in manuscript body files exist in `manuscript/references.bib`; fail on missing or duplicate BibTeX keys. |
| [`audit_manuscript_numbers.py`](audit_manuscript_numbers.py) | Scan `manuscript/**/*.md` for raw numbers, compare to `METRICS.yaml`, fail on any MISMATCH, and report expected/manual-review cases. |
| [`check_metrics_fresh.py`](check_metrics_fresh.py) | Fast pre-commit / CI gate — confirm `METRICS.yaml` was regenerated against `HEAD`, agrees with `coverage.json`, matches the current roundtrip ledger, and optionally fails on a dirty worktree via `--fail-on-dirty`. |
| [`claim_ledger.py`](claim_ledger.py) | Generate the manuscript claim inventory across rendered body files; optional `--fail-on-literal-numbers` turns un-tokenized numeric prose into a release-gate failure. |
| [`batch_api.py`](batch_api.py) | Thin compatibility wrappers around the real package analysis/export/visualization APIs used by [`../run_all.py`](../run_all.py). |
| [`manuscript_figures.py`](manuscript_figures.py) | Copy curated real run and evaluation PNGs from registered COGANT artifacts into `../output/figures/`, write per-figure `.figure.json` metadata sidecars, and enforce visual-evidence completeness in strict mode. |
| [`audit_test_names.py`](audit_test_names.py) | Fail when active tests or thin examples use campaign-era names such as campaign numbers, dated batch tags, or opaque coverage-only suffixes. |
| [`audit_folder_docs.py`](audit_folder_docs.py) | Check COGANT-owned folders for README/AGENTS coverage, placeholder boilerplate, documented exceptions, and relative-link health. |

## Common workflows

Regenerate metrics, audit the manuscript, fail on mismatch:

```bash
uv run python tools/regenerate_metrics.py
uv run python tools/audit_manuscript_citations.py
uv run python tools/audit_manuscript_numbers.py
```

Refresh just the `ablation.*` block in `METRICS.yaml` from the packaged-fixture pipeline:

```bash
uv run python tools/regenerate_ablation.py
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
uv run python tools/check_metrics_fresh.py --fail-on-dirty   # release gate
```

Audit active test/example naming and folder documentation:

```bash
uv run python tools/audit_test_names.py
uv run python tools/audit_folder_docs.py
```

Refresh manuscript figure assets and metadata sidecars after `run_all.py` has
produced package outputs and `cogant/evaluation/figures/generate_figures.py`
has refreshed fixture metrics:

```bash
uv run python tools/manuscript_figures.py --strict
```

All scripts here are **directory-independent** — paths are anchored on
`__file__`, so any `uv run python tools/<script>.py` invocation works
from any cwd. See [`AGENTS.md`](AGENTS.md) for the full tool inventory.
