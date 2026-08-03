# COGANT docs-deep review log — 2026-08-02

Fleet docs-deep pass on `ActiveInferenceInstitute/COGANT` (default branch `main`).

## Phase 0 — Preflight

- Fetched origin; checked out `main` (was detached at `062e7e1`); fast-forwarded to
  HEAD `6123226` ("Resolve Major red-team findings (M1-M7)").
- Baseline verified: repo's own gates all pass at HEAD —
  `docs/verify_doc_links.py` (381 files, 1561 links, 0 broken),
  `tools/audit_folder_docs.py`, `tools/audit_docs_constants.py`,
  `tools/audit_stage_list.py`, `tools/audit_test_names.py`.
- Scope: ~728 markdown files repo-wide; ~399 under `cogant/docs/` (MkDocs site).
  The review fanned out to 3 leaf subagents (architecture/api completed; the other
  two hit an upstream billing error and were re-covered by direct greps here).

## Phase 1 — Review findings

Counts after verification against the live code/CLI/registry:

- **Major: 6 → 0 remaining.** All six were wrong language-support claims
  (Java/C++/C#/Ruby/PHP advertised as parsed) plus one stale module import
  (`cogant.semantics`); all fixed.
- **Medium: 20 → 0 remaining.** Stale rule counts ("8 concrete rules" vs 22),
  obsolete `/sessions/...` sandbox paths, dead `translate/rules.py` paths, stale
  FAQ/roadmap language claims, `docs/changelog.md` drift (222 vs 436 lines) that
  broke `mkdocs build --strict`, 78 dead absolute GitHub source links, missing
  `SECURITY.md`, stale `.github/README.md` server-auth claim, stale `CI.md`
  workflow references, orphaned pages missing from the MkDocs nav, stale version
  strings (0.5.0), a nonexistent `PipelineConfig.plugins` example, and RFC 0001
  defining GNN as "graph neural network".
- **Minor: 9 → 0 remaining.** Broken/absent markdown fences in 5 architecture
  pages, a stale "not linked from nav" statement in `playground.md`, missing
  `theory/roundtrip.md` row in `theory/AGENTS.md`, missing reference-module
  README rows, `cogant/README.md` fixture-breakdown wording.

## Phase 2 — Scope

Top-level `TODO.md` updated with a dated docs-pass section (completed items carry
commit refs; open items are listed at the end).

## Phase 3 — Implementation (commits)

1. `d86528c` — docs: stale language/rule-count/path/version claims in
   architecture + API docs; FAQ + known-limitations language statements; broken
   fences; `docs/changelog.md` sync; MkDocs nav additions (11 orphaned content
   pages + learning-paths section index); `cogant/README.md` fixture counts;
   `CI.md` rewrite to match the real workflow.
2. `d2d7156` — 78 dead GitHub blob/raw links repaired; `cogant/SECURITY.md`
   added; `tools/audit_docs_constants.py` scoped to treat the changelog mirror as
   dated history (the documented `cp CHANGELOG.md docs/changelog.md` convention
   was tripping historical-claim false positives); `.github/README.md` auth and
   language claims; RFC 0001 GNN definition; reference-module README rows.
3. (final) — review log + TODO.md pass section.

## Phase 4 — Verification

- `uv run python docs/verify_doc_links.py` — 0 broken (381 files / 1564 links).
- `uv run mkdocs build --strict` — clean (previously aborted on the changelog
  `../CHANGELOG.md` link).
- `tools/audit_docs_constants.py`, `tools/audit_folder_docs.py`,
  `tools/audit_stage_list.py` — pass.
- `tools/audit_docs_constants.py` targeted pytest run: 4/5 pass; the failing test
  (`test_roundtrip_claim_audit_accepts_current_ledger_claim`) fails identically
  at HEAD without this pass's changes — pre-existing, logged, not caused here.
- Full pytest suite not run (heavy; this pass touched no package code except the
  audit tool, which was lint-clean and test-verified).
- `METRICS.yaml` regeneration intentionally not run: metrics-fresh stays red until
  `tools/regenerate_metrics.py` is executed against the new HEAD (evidence
  pipeline, out of scope for a docs pass; matches the existing `cog-p0-04` note).

## Open / deferred

- `cogant/docs/notebooks/*` (12 pages): deliberate "(planned)" stubs with
  one-line descriptions; filling them requires the Jupyter toolchain and is a
  major effort — deferred.
- Pre-existing failing audit test (see above) — flag for the owner.
- METRICS regeneration + release-gate rerun after this pass.
