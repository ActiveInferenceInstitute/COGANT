# Manuscript Number Audit

**Generated:** 2026-04-16  
**METRICS.yaml source:** cogant/evaluation/METRICS.yaml  
**Manuscript directory:** manuscript  
**Fuzzy tolerance:** ±0.5% relative (CLOSE tier)  

## Summary

| Status | Count | Description |
|--------|-------|-------------|
| MISMATCH | 0 | Real data drift — update manuscript or METRICS.yaml |
| CLOSE | 0 | Within ±0.5% of METRICS.yaml — likely rounding / stale cache |
| EXPECTED_MISMATCH | 12 | Contextually valid — historical refs, scope differences, threshold definitions |
| MATCH | 20 | Verified exact |
| UNVERIFIED | 0 | No METRICS.yaml entry to compare against |
| STALE_ARCHIVE | 0 | In _archive/ — expected to differ |
| **Total findings** | **32** | |

### Confidence distribution

| Confidence | Count | Meaning |
|------------|-------|---------|
| HIGH | 32 | Exact match (or expected-mismatch with documented rationale) |
| MEDIUM | 0 | Fuzzy match within ±0.5% |
| LOW | 0 | No METRICS.yaml mapping, or drift beyond tolerance |

## Reference Values (from METRICS.yaml / fallback)

| Variable | Path | Value |
|----------|------|-------|
| test_count_passing | `testing.test_count_passing` | `7721` |
| test_count_total | `testing.test_count_total` | `7756` |
| test_count_skipped | `testing.test_count_skipped` | `31` |
| coverage_percent | `testing.coverage_percent` | `90.03` (±0.5) |
| version | `package.version` | `0.5.0` |
| isomorphic_count | `evaluation.roundtrip.isomorphic_count` | `23` |
| total_targets | `evaluation.roundtrip.total_targets` | `23` |
| approximate_count | `evaluation.roundtrip.approximate_count` | `0` |
| divergent_count | `evaluation.roundtrip.divergent_count` | `0` |
| rw_repo_count | `evaluation.roundtrip.rw_repo_count` | `None` |
| zoo_fixture_count | `evaluation.roundtrip.zoo_fixture_count` | `None` |
| rw_lib_count | `evaluation.roundtrip.rw_lib_count` | `None` |
| mean_epsilon | `evaluation.roundtrip.mean_epsilon` | `1.0` (±0.01) |
| median_epsilon | `evaluation.roundtrip.median_epsilon` | `1.0` (±0.01) |
| min_epsilon | `evaluation.roundtrip.min_epsilon` | `1.0` (±0.01) |
| max_epsilon | `evaluation.roundtrip.max_epsilon` | `1.0` (±0.01) |
| translation_rules | `pipeline.translation_rules` | `22` |
| stage_count | `pipeline.stage_count` | `10` |
| python_source_files | `codebase.python_source_files` | `201` |
| python_loc | `codebase.python_loc` | `70333` |
| suite_runtime_s | `benchmark.suite_runtime_s` | `295.8` |
| shipped_fixture_count | `benchmark.shipped_fixture_count` | `6` |
| node_kind_count | `ir_schema.node_kind_count` | `18` |
| edge_kind_count | `ir_schema.edge_kind_count` | `18` |
| active_inf_role_count | `ir_schema.active_inf_role_count` | `7` |
| cogant_macro_f1 | `evaluation.semantic.cogant_macro_f1` | `None` (±0.01) |
| gpt4_macro_f1 | `evaluation.semantic.gpt4_macro_f1` | `None` (±0.01) |

## Mismatches (action required)

These manuscript claims do not match METRICS.yaml. Update the manuscript or fix the metrics.

_No mismatches found._

## Close Matches (within tolerance)

These manuscript claims are within ±0.5% of the METRICS.yaml value.
Likely a rounding artefact or a stale cache. Fixing these is typically a one-line update.

_No close matches within the fuzzy tolerance window._

## Matches (verified correct)

| File | Line | Claim | Value | Pattern | Confidence |
|------|------|-------|-------|---------|------------|
| `manuscript/02_04_gnn_export_and_error_handling.md` | 56 | `six shipped fixtures` | 6 | shipped_fixture_count | HIGH |
| `manuscript/03_api_and_workflows.md` | 51 | `10 stage` | 10 | stage_count | HIGH |
| `manuscript/05_conclusion.md` | 13 | `Ten-stage` | 10 | stage_count | HIGH |
| `manuscript/05_conclusion.md` | 33 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/06_03_performance_and_fixture_metrics.md` | 34 | `six fixtures` | 6 | shipped_fixture_count | HIGH |
| `manuscript/06_05_reproducible_recording.md` | 57 | `ten-stage` | 10 | stage_count | HIGH |
| `manuscript/06_05_reproducible_recording.md` | 58 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/06_experimental_setup.md` | 143 | `six fixtures` | 6 | shipped_fixture_count | HIGH |
| `manuscript/07_reproducibility.md` | 14 | `ten-stage` | 10 | stage_count | HIGH |
| `manuscript/08_03_lenses_and_synthesis.md` | 7 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/09_ablation.md` | 16 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/09_ablation.md` | 23 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/09_ablation.md` | 64 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/09_ablation.md` | 68 | `six fixtures` | 6 | shipped_fixture_count | HIGH |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 24 | `23 / 23 ISOMORPHIC` | 23 | isomorphic_count | HIGH |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 24 | `23 / 23 ISOMORPHIC` | 23 | total_targets | HIGH |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 88 | `14 / 23 ISOMORPHIC` | 23 | total_targets | HIGH |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 89 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/supplementary.md` | 18 | `23/23 ISOMORPHIC` | 23 | isomorphic_count | HIGH |
| `manuscript/supplementary.md` | 18 | `23/23 ISOMORPHIC` | 23 | total_targets | HIGH |

## Expected Mismatches (contextually valid — no action required)

These numbers appear to differ from METRICS.yaml but are correct in context:
historical version references, threshold definitions, or different counting scopes.

| File | Line | Claim | Extracted | Metrics Value | Reason |
|------|------|-------|-----------|---------------|--------|
| `manuscript/05_conclusion.md` | 19 | `v0.4.0` | 0.4.0 | 0.5.0 | Historical reference: describes v0.4.0 behaviour, not current version |
| `manuscript/05_conclusion.md` | 33 | `v0.2.0` | 0.2.0 | 0.5.0 | Historical reference: describes items shipped in v0.2.0 |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 28 | `ε ≥ 0.8` | 0.8 | 1.0 | Threshold definition: ε ≥ 0.8 defines ISOMORPHIC tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 28 | `ε < 0.5` | 0.5 | 1.0 | Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 67 | `ε ≥ 0.8` | 0.8 | 1.0 | Threshold definition: ε ≥ 0.8 defines ISOMORPHIC tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 68 | `ε < 0.5` | 0.5 | 1.0 | Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 86 | `ε ≥ 0.8` | 0.8 | 1.0 | Threshold definition: ε ≥ 0.8 defines ISOMORPHIC tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 87 | `ε = 0.7778` | 0.7778 | 1.0 | Historical wave-14 appendix row: per-target ε, not METRICS mean_epsilon |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 88 | `14 / 23 ISOMORPHIC` | 14 | 23 | Historical wave-14 S01 appendix: 14/23 ISOMORPHIC before wave-16; METRICS canonical is 23/23 |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 88 | `ε = 0.6667` | 0.6667 | 1.0 | Historical wave-14 appendix row: per-target ε, not METRICS mean_epsilon |
| `manuscript/S02_appendix_ablation.md` | 26 | `coverage 80.0 %` | 80.0 | 90.03 | Ablation metric: 80% is semantic coverage (role precision/recall), not line coverage |
| `manuscript/S03_appendix_galois_sketch.md` | 140 | `ε ≥ 0.8` | 0.8 | 1.0 | Threshold definition: ε ≥ 0.8 defines ISOMORPHIC tier boundary, not a data claim |

## Unverified Claims

These numbers were extracted but have no corresponding METRICS.yaml entry to compare against.
Consider adding them to METRICS.yaml for future tracking.

| File | Line | Pattern | Extracted | Context |
|------|------|---------|-----------|---------|
_No unverified claims._

## Stale Archive Claims

These numbers appear in `manuscript/_archive/` files. They reflect an older state
of the codebase and are expected to differ from current METRICS.yaml values.
No action required unless an archive file is being actively used.

| File | Line | Pattern | Extracted | Current Metrics Value | Context |
|------|------|---------|-----------|----------------------|---------|
_No stale archive claims found._

## Action Items

### Low priority — expected mismatches (verify intent)

- **version** = `0.4.0` in `manuscript/05_conclusion.md` line 19: Historical reference: describes v0.4.0 behaviour, not current version
- **version** = `0.2.0` in `manuscript/05_conclusion.md` line 33: Historical reference: describes items shipped in v0.2.0
- **mean_epsilon** = `0.8` in `manuscript/S01_appendix_roundtrip_epsilon.md` line 28: Threshold definition: ε ≥ 0.8 defines ISOMORPHIC tier boundary, not a data claim
- **mean_epsilon** = `0.5` in `manuscript/S01_appendix_roundtrip_epsilon.md` line 28: Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim
- **mean_epsilon** = `0.7778` in `manuscript/S01_appendix_roundtrip_epsilon.md` line 87: Historical wave-14 appendix row: per-target ε, not METRICS mean_epsilon
- **isomorphic_count** = `14` in `manuscript/S01_appendix_roundtrip_epsilon.md` line 88: Historical wave-14 S01 appendix: 14/23 ISOMORPHIC before wave-16; METRICS canonical is 23/23
- **mean_epsilon** = `0.6667` in `manuscript/S01_appendix_roundtrip_epsilon.md` line 88: Historical wave-14 appendix row: per-target ε, not METRICS mean_epsilon
- **coverage_percent** = `80.0` in `manuscript/S02_appendix_ablation.md` line 26: Ablation metric: 80% is semantic coverage (role precision/recall), not line coverage

_All extracted numbers are verified. Manuscript is consistent with METRICS.yaml._

## Injection Commands

For each MISMATCH below, the sed command replaces the manuscript value with the
METRICS.yaml value. **User decision required** before running: verify that the
METRICS.yaml value is authoritative, then apply.

_No mismatches — no injection commands needed._

---

_This report is generated by `tools/audit_manuscript_numbers.py`._
_Re-run after any manuscript edit or metrics update to keep it current._
