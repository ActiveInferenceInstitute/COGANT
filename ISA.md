---
project: cogant
phase: current-readiness
mode: source-grounded
updated: 2026-06-07
---

# COGANT Ideal State Artifact

COGANT is a private working project that pairs an installable Python package
with a manuscript and generated evidence artifacts. The authoritative project
root is `/Users/4d/Documents/GitHub/projects/working/cogant`; the installable
package root is `cogant/`; manuscript source lives in `manuscript/`; generated
manuscript output lives in `output/`; native package evaluation output lives
under `cogant/evaluation/`.

## Current Goal

The project should be defensible as a reproducible codebase-to-GNN research
artifact:

- numeric manuscript claims are injected from `cogant/evaluation/METRICS.yaml`
  and related generated data files;
- the native roundtrip ledger is regenerated from local source fixtures, not
  edited by hand;
- docs point to the working checkout and documented `uv run` commands;
- package behavior is verified by tests and local audit scripts; and
- limitations state the current scope boundary directly: Python roundtrip
  evidence, rule-derived role labels, and role preservation rather than full
  semantic equivalence.

## Source Of Truth

| Surface | Authority |
|---|---|
| Package implementation | `cogant/py/cogant/` |
| Package tests | `cogant/tests/` |
| Project-level audit tests | `tests/` |
| Roundtrip ledger | `cogant/evaluation/dataset/roundtrip_results.jsonl` |
| Aggregate metrics | `cogant/evaluation/METRICS.yaml` |
| Manuscript variables | `tools/manuscript_vars.py` and `output/data/manuscript_variables.json` |
| Manuscript source | `manuscript/*.md`, `manuscript/config.yaml`, `manuscript/references.bib` |
| Rendered manuscript source tree | `output/manuscript/` |
| Figure registry | `manuscript/figures/registry.json` plus generated PNGs under `output/figures/` |
| Pipeline runner | `run_all.py`, `tools/run_all_runner.py`, and `run_all.json` |

## Required Gates

Run these from the project root unless a command says otherwise:

```bash
uv run --directory cogant python ../tools/regenerate_roundtrip_ledger.py
uv run --directory cogant python ../tools/regenerate_metrics.py
uv run python scripts/z_generate_manuscript_variables.py --strict
uv run python tools/check_metrics_fresh.py
uv run python tools/audit_docs_constants.py
uv run python tools/audit_stage_list.py
uv run python tools/audit_manuscript_numbers.py --output /tmp/cogant_number_audit.md
uv run python tools/audit_manuscript_crossrefs.py
uv run python tools/audit_manuscript_citations.py
uv run python tools/claim_ledger.py --manuscript-dir manuscript --output-dir /tmp/cogant_claim_ledger --fail-on-literal-numbers
uv run --directory cogant python docs/verify_doc_links.py
uv run --directory cogant python docs/verify_manuscript_links.py
uv run pytest tests/ -q
uv run --directory cogant pytest tests/ -q
```

The package suite is the expensive gate. Use targeted tests while developing,
then run the full suite before calling the repository ready.

## Claim Policy

- Do not state a metric in manuscript prose unless it is injected from a
  generator or checked by an audit.
- Do not use the roundtrip ledger to claim behavioral equivalence of arbitrary
  Python programs; it measures native role preservation and related diagnostics.
- Do not use JavaScript, TypeScript, Rust, or Go parser existence as evidence
  for reverse-synthesis coverage. Current roundtrip evidence is Python-scoped.
- Treat `control_positive` fixtures with zero source roles as invalid evidence;
  `tools/check_metrics_fresh.py` is responsible for rejecting that case.
- Re-run source-generating commands after modifying fixtures, translation
  rules, metrics logic, manuscript variables, or figure generators.

## Release Boundary

Ready means:

- all gates above pass on the current worktree;
- `METRICS.yaml`, `roundtrip_results.jsonl`, and `output/manuscript/` agree;
- rendered figures are present under `output/figures/`;
- active docs contain no obsolete working-directory paths; and
- remaining limitations are explicit scope boundaries, not hidden defects.

Follow-up work that changes the empirical scope must come with new data:
human-labeled role annotations, a larger roundtrip corpus, non-Python
reverse-synthesis evidence, or a fresh performance benchmark on a graph-large
target.
