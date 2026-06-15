# tools/

Manuscript-grounding utilities. The numbers that appear in
[`../manuscript/`](../manuscript/) are written here to a single source of
truth (`../cogant/evaluation/METRICS.yaml`) and substituted into the
prose by these scripts. The gates refuse out-of-sync metrics and numeric
mismatches; the claim ledger inventories unsupported literal claims for
review and can be made stricter with its release-only flags.

| Script | One-liner |
|--------|-----------|
| [`regenerate_metrics.py`](regenerate_metrics.py) | Run `pytest` / `mypy --strict` / `ruff` / coverage against the live tree, walk the AST, and (re)write `METRICS.yaml`. |
| [`regenerate_ablation.py`](regenerate_ablation.py) | Run the live translation/state-space/matrix pipeline on the 6 packaged fixtures and (re)write the `ablation:` block in `METRICS.yaml`. |
| [`manuscript_vars.py`](manuscript_vars.py) | Library — pure functions mapping `{{TOKEN}}` placeholders to dotted paths in `METRICS.yaml`. No I/O. |
| [`inject_manuscript_vars.py`](inject_manuscript_vars.py) | CLI — substitute `{{TOKEN}}` placeholders in a file or directory. |
| [`audit_manuscript_citations.py`](audit_manuscript_citations.py) | Verify Pandoc citation keys used in manuscript body files exist in `manuscript/references.bib`; fail on missing or duplicate BibTeX keys. |
| [`audit_manuscript_formalisms.py`](audit_manuscript_formalisms.py) | Verify COGANT-owned formalism labels and generated numbering for `@def:` / `@prop:` / `@inv:` / `@conj:` / `@alg:` / `@thm:` references. |
| [`audit_manuscript_numbers.py`](audit_manuscript_numbers.py) | Scan `manuscript/**/*.md` for raw numbers, compare to `METRICS.yaml`, fail on any MISMATCH, and report expected/manual-review cases. |
| [`audit_manuscript_math_adjacency.py`](audit_manuscript_math_adjacency.py) | Resolve manuscript variables and fail on inline math spans whose closing `$` is immediately followed by a digit, preventing Pandoc `$-$10` leaks. |
| [`audit_manuscript_claim_scope.py`](audit_manuscript_claim_scope.py) | Reject high-risk manuscript overclaims: uncaveated guarantees, inferential-statistics language, and semantic-totality claims. |
| [`audit_robustness_table.py`](audit_robustness_table.py) | Bind `@tbl:robustness-transforms` rows to `cogant/evaluation/robustness/robustness_results.json` so hand-written transform verdicts cannot drift. |
| [`audit_roadmap_truth.py`](audit_roadmap_truth.py) | Reject out-of-sync current-version labels, unsupported benchmark fixture/stage claims, and TODO/task drift for the active refactor tranche. |
| [`citation_claim_ledger.py`](citation_claim_ledger.py) | Spot-check high-risk citation claims by key and emit JSONL claim/source pairs for review-ledger audits. |
| [`check_metrics_fresh.py`](check_metrics_fresh.py) | Fast pre-commit / CI gate — confirm `METRICS.yaml` was regenerated against `HEAD`, agrees with `coverage.json`, matches the current roundtrip ledger, and optionally fails on a dirty worktree via `--fail-on-dirty`. |
| [`claim_ledger.py`](claim_ledger.py) | Generate the manuscript claim inventory across rendered body files; optional `--fail-on-literal-numbers` turns un-tokenized numeric prose into a release-gate failure. |
| [`manuscript_evidence_audit.py`](manuscript_evidence_audit.py) | Summarize section-level evidence lanes across source manuscript fragments, rank the thinnest sections, emit non-fatal reviewer actions, write JSON / Markdown / PNG artifacts, and fail strict runs when a section lacks support lanes. |
| [`manuscript_review_dashboard.py`](manuscript_review_dashboard.py) | Combine figure QA, evidence lanes, claim ledger, figure-manifest status, and the current review queue into one JSON / Markdown / PNG dashboard. |
| [`audit_publication_readiness.py`](audit_publication_readiness.py) | Combine claim primitives, publication-date autofill, evidence lanes, visual QA, figure metadata, and manuscript claim-scope/doc-constant gates into a JSON / Markdown readiness verdict. |
| [`batch_api.py`](batch_api.py) | Thin compatibility wrappers around the real package analysis/export/visualization APIs used by [`../run_all.py`](../run_all.py). |
| [`manuscript_figures.py`](manuscript_figures.py) | Copy curated real run and evaluation PNGs from registered COGANT artifacts into `../output/figures/`, write per-figure `.figure.json` metadata sidecars, and enforce visual-evidence completeness in strict mode. |
| [`visualization_quality_audit.py`](visualization_quality_audit.py) | Summarize promoted figure sidecars into JSON / Markdown / PNG review artifacts and fail strict runs when visual QA, source evidence, renderer metadata, or publication dimensions are unsafe. |
| [`organization_state_space_audit.py`](organization_state_space_audit.py) | Validate provisional organization state-space sketches and, when claimed, differentiable-surrogate optimization lanes without promoting them to shipped runtime capability. |
| [`audit_test_names.py`](audit_test_names.py) | Fail when active tests or thin examples use campaign-era names such as campaign numbers, dated batch tags, or opaque coverage-only suffixes. |
| [`audit_folder_docs.py`](audit_folder_docs.py) | Check COGANT-owned folders for README/AGENTS coverage, placeholder boilerplate, documented exceptions, and relative-link health. |
| [`audit_synthetic_surfaces.py`](audit_synthetic_surfaces.py) | Classify retained synthetic-surface terms and fail unallowlisted fallback/mock/placeholder/stub occurrences; `--strict` also checks generated manuscript variables and matrix sidecar provenance. |

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
uv run python tools/audit_synthetic_surfaces.py
```

Run the red-team manuscript guardrails that are also wired into CI:

```bash
uv run python tools/audit_manuscript_math_adjacency.py
uv run python tools/audit_manuscript_formalisms.py --strict
uv run python tools/audit_manuscript_claim_scope.py
uv run python tools/audit_robustness_table.py
uv run python tools/audit_roadmap_truth.py
uv run python tools/citation_claim_ledger.py --keys KEY [KEY ...]
uv run python tools/organization_state_space_audit.py --strict
```

Refresh manuscript figure assets and metadata sidecars after `run_all.py` has
produced package outputs and `cogant/evaluation/figures/generate_figures.py`
has refreshed fixture metrics:

```bash
uv run python tools/manuscript_figures.py --strict
uv run python tools/visualization_quality_audit.py --strict
uv run python tools/manuscript_evidence_audit.py --strict
uv run python tools/manuscript_review_dashboard.py --strict
uv run python tools/audit_publication_readiness.py --strict
uv run python tools/audit_synthetic_surfaces.py --strict
```

`manuscript_figures.py` is a compatibility CLI/wrapper. The implementation is
split under `tools/figures/`: PNG inspection, publication renderers,
metadata/sidecar validation, and copy-manifest orchestration are separate
modules so strict publication QA can evolve without rebuilding a monolith.

All scripts here are **directory-independent** — paths are anchored on
`__file__`, so any `uv run python tools/<script>.py` invocation works
from any cwd. See [`AGENTS.md`](AGENTS.md) for the full tool inventory.
