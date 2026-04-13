# Coherence / Version Audit — Wave 19 (coherence-version-agent)

**Date:** 2026-04-11
**Agent:** Wave 19 sub-agent `coherence-version-agent`
**Source of truth:** `cogant/evaluation/METRICS.yaml` (generated 2026-04-11)
**Scope:** `cogant/docs/**/*.md` (manuscript/ explicitly excluded)

## Goal

Find hardcoded numeric metrics in user-facing docs that drifted from the
auto-generated `evaluation/METRICS.yaml` and update them to current values,
adding a header note in each touched doc that points readers at METRICS.yaml
as the canonical source.

## Ground-truth values (from METRICS.yaml)

| Field | Value |
|---|---|
| `cogant_version` | 0.5.0 |
| `test_count_passing` | 4979 |
| `test_count_failing` | 0 |
| `test_count_skipped` | 103 |
| `coverage_percent` | 86.8 |
| `mypy_strict_errors` | 0 |
| `ruff_violations` | 1 |
| `isomorphic_count` | 23 |
| `total_targets` | 23 |
| `mean_epsilon` | 1.0 |
| `python_source_files` | 180 |
| `python_loc` | 56788 |
| `public_modules` | 145 |
| `public_classes` | 303 |
| `public_functions` | 758 |
| `translation_rules` | 19 |
| `stage_count` | 8 |

## Files touched

### 1. `docs/evaluation/V1.0_READINESS.md`
**Header note:** added pointer to `evaluation/METRICS.yaml` as source of truth + last-sync date.
**Numbers updated:**
- Summary verdict: `2,146 passing tests` → `4,979 passing tests (0 failing, 103 skipped)`
- Summary verdict: `87% coverage` → `86.8% coverage`
- Summary verdict: roundtrip `(14/23 ISOMORPHIC at ε ≥ 0.8) ... pre-wave-16 ... not yet re-benchmarked` →
  `23/23 ISOMORPHIC at ε ≥ 0.8 (mean ε = 1.0) ... post-wave-16 re-benchmark`
- Requirements table — `ε-isomorphism metric` row: `14/23 ISOMORPHIC ... pre-wave-16` → `23/23 ISOMORPHIC ... mean ε = 1.0`
- Requirements table — `Test suite` row: `2,146 passing, 0 failing; 87% coverage` → `4,979 passing, 0 failing, 103 skipped; 86.8% coverage`
- Requirements table — coverage rows: `87% total` / `87% vs aspirational 85%` → `86.8%`
- "What's missing" historical row: `87% achieved in v0.5.0` → `86.8% achieved in v0.5.0`
- Recommendation list: `87% in v0.5.0` → `86.8% in v0.5.0`
- Closing paragraph: `2,146 tests, 87% coverage ... 14/23 ISOMORPHIC ... pre-wave-16 ... re-benchmark pending` →
  `4,979 tests, 86.8% coverage ... 23/23 ISOMORPHIC ... mean ε = 1.0 ... post-wave-16 re-benchmark`

### 2. `docs/evaluation/FINAL_REPORT.md`
**Header note:** added pointer to METRICS.yaml + statement that historical sections intentionally
preserve their original numbers as a trajectory record.
**Numbers updated:**
- "End State" table — `Tests passing: 2,146 / 0 failing` → `4,979 / 0 failing / 103 skipped`
- "End State" table — `Coverage: 87%` → `86.8%`
- "End State" table — added `Ruff violations: 1` row
- "Roundtrip ε Evaluation" section — added a new "Current (post-wave-16 re-benchmark)" sub-section
  with `23/23 ISOMORPHIC, mean ε = 1.0` as the head-of-section number, demoting the prior
  `Pre-wave-16 benchmark (JSONL ground truth, current)` block to clearly-labeled `Historical:
  Pre-wave-16 baseline`.
- (The `Roundtrip ε` row of the End State table was already updated to 23/23 by the parallel
  number-audit agent; left as-is.)

### 3. `docs/evaluation/ROUNDTRIP_EVAL.md`
**Header note:** added pointer to METRICS.yaml; clarified that the per-target table is the
canonical post-wave-16 re-run while pre-wave-16 figures are historical.
**Numbers updated:**
- `Tool: cogant roundtrip (v0.4.0)` → `(v0.5.0)`
- "Generated" line: appended `numbers re-verified 2026-04-11`.
- (The body table was already post-wave-16 / 23/23; left as-is.)

### 4. `docs/evaluation/R&D_LOG.md`
**Header note:** added a current-state banner near the top:
- v0.5.0 · 4,979 tests passing · 0 failing · 103 skipped · 86.8% coverage · 0 mypy strict errors
  · 1 ruff violation · roundtrip 23/23 ISOMORPHIC at ε ≥ 0.8 (mean ε = 1.0) · 8 stages · 19
  rules · 180 source files (56,788 LOC) · 145 modules / 303 classes / 758 functions.
- Explicit policy: per-wave snapshots below intentionally preserve their original numbers
  (e.g. wave-15 with 1873 tests / 82.6% coverage / v0.4.0). Do not modernise historical
  wave entries — that erases the R&D trajectory.

### 5. `docs/evaluation/RELEASE_NOTES_v0.5.0.md`
**Header note:** added pointer to METRICS.yaml and explicit statement that this is a frozen
release artifact for v0.5.0 and that v0.4.0 references are intentional historical context.
**No body numbers changed** — release notes are accurate as-is.

## Files inspected and intentionally NOT touched

| File | Reason |
|---|---|
| `docs/changelog.md` | Marked canonical-source = `CHANGELOG.md` at repo root. The mirror header instructs writers to edit the root file then `cp` here. All `14/23` and `19/23` mentions are inside historical `[0.4.0]` change-log entries and accurately describe the state at that release. |
| `docs/concepts/roundtrip.md` | Match was `epsilon = 0` (formal definition of perfect roundtrip). Not a stale metric. |
| `docs/evaluation/ISOMORPHISM_THEOREM.md` | Matches were `ε_max(v0.1.0) = 0.6` etc. — Galois-connection theory examples for v0.1.0 rule table, not v0.5.0 status claims. |
| `docs/evaluation/ROUNDTRIP_IMPROVEMENT.md` | Already accurate (`23/23 ISOMORPHIC` in summary; pre/post tables and `Wave 14 lifted 5 targets across the ε = 0.8 line (14 → 19 ISOMORPHIC)` are correct historical wave-14 narrative). |
| `docs/roadmap/version_020_planned.md` | Match was `v0.2.0` planning doc context. Not a current-version claim. |
| `docs/evaluation/R&D_LOG.md` (per-wave snapshots after the new banner) | Historical wave snapshots — 1873 tests / 82.6% coverage / v0.4.0 are correct as the wave-15 closeout state, and now explicitly framed as historical by the new banner. |
| `manuscript/**` | Excluded by binding rule. |

## Method notes

- All edits were verified by re-reading the file region first; no number was guessed.
- Where a parallel agent had already updated a row (`FINAL_REPORT.md` line 56), the existing
  edit was respected and not reverted.
- Historical context (wave-9 baseline, wave-14 intermediate, pre-wave-16 ground truth) was
  preserved everywhere so readers can still see the trajectory; only "this is the current
  state" claims were updated.

## Verification queries that returned nothing-to-fix

After this pass, the following queries return only historical / theory / canonical-mirror
contexts (no live current-state claims with stale numbers):

```text
grep "2,?146\|2,?129\|1873\|1945\|1943\|2,?230\|87% coverage\|82\.6% coverage\|14/23"
```

All remaining matches are documented in the "intentionally NOT touched" table above.

## Summary

- **5 docs touched** (4 with body number updates + 1 with header note only)
- **6 docs inspected and left as-is** with documented reasons
- **0 manuscript edits** (binding rule respected)
- **Every numeric edit traceable to METRICS.yaml**
- **Every touched doc now has a header pointer to METRICS.yaml as source of truth**
