# Manuscript Number Audit

**Generated:** 2026-04-11  
**METRICS.yaml source:** cogant/evaluation/METRICS.yaml  
**Manuscript directory:** manuscript  
**Fuzzy tolerance:** ±0.5% relative (CLOSE tier)  

## Summary

| Status | Count | Description |
|--------|-------|-------------|
| MISMATCH | 1 | Real data drift — update manuscript or METRICS.yaml |
| CLOSE | 0 | Within ±0.5% of METRICS.yaml — likely rounding / stale cache |
| EXPECTED_MISMATCH | 13 | Contextually valid — historical refs, scope differences, threshold definitions |
| MATCH | 7 | Verified exact |
| UNVERIFIED | 6 | No METRICS.yaml entry to compare against |
| STALE_ARCHIVE | 0 | In _archive/ — expected to differ |
| **Total findings** | **27** | |

### Confidence distribution

| Confidence | Count | Meaning |
|------------|-------|---------|
| HIGH | 20 | Exact match (or expected-mismatch with documented rationale) |
| MEDIUM | 0 | Fuzzy match within ±0.5% |
| LOW | 7 | No METRICS.yaml mapping, or drift beyond tolerance |

## Reference Values (from METRICS.yaml / fallback)

| Variable | Path | Value |
|----------|------|-------|
| test_count_passing | `testing.test_count_passing` | `6884` |
| test_count_total | `testing.test_count_total` | `6955` |
| test_count_skipped | `testing.test_count_skipped` | `68` |
| coverage_percent | `testing.coverage_percent` | `90.77` (±0.5) |
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
| translation_rules | `pipeline.translation_rules` | `19` |
| stage_count | `pipeline.stage_count` | `8` |
| python_source_files | `codebase.python_source_files` | `180` |
| python_loc | `codebase.python_loc` | `56788` |
| suite_runtime_s | `benchmark.suite_runtime_s` | `None` |
| shipped_fixture_count | `benchmark.shipped_fixture_count` | `None` |
| node_kind_count | `ir_schema.node_kind_count` | `None` |
| edge_kind_count | `ir_schema.edge_kind_count` | `None` |
| active_inf_role_count | `ir_schema.active_inf_role_count` | `None` |
| cogant_macro_f1 | `evaluation.semantic.cogant_macro_f1` | `None` (±0.01) |
| gpt4_macro_f1 | `evaluation.semantic.gpt4_macro_f1` | `None` (±0.01) |

## Mismatches (action required)

These manuscript claims do not match METRICS.yaml. Update the manuscript or fix the metrics.

| File | Line | Claim | Was | Should be | Δ% | Confidence | Context |
|------|------|-------|-----|-----------|----|------------|---------|
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 76 | `14 / 23 ISOMORPHIC` | 14 | 23 | 39.13% | LOW | 14 / 23 ISOMORPHIC, 6 / 23 APPROXIMATE, 3 / 23 D |

## Close Matches (within tolerance)

These manuscript claims are within ±0.5% of the METRICS.yaml value.
Likely a rounding artefact or a stale cache. Fixing these is typically a one-line update.

_No close matches within the fuzzy tolerance window._

## Matches (verified correct)

| File | Line | Claim | Value | Pattern | Confidence |
|------|------|-------|-------|---------|------------|
| `manuscript/05_conclusion.md` | 33 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 19 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/06_05_reproducible_recording.md` | 65 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/06_experimental_setup.md` | 204 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/08_03_lenses_and_synthesis.md` | 7 | `v0.5.0` | 0.5.0 | version | HIGH |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 76 | `14 / 23 ISOMORPHIC` | 23 | total_targets | HIGH |
| `manuscript/S03_appendix_galois_sketch.md` | 73 | `19 translation rules` | 19 | translation_rules | HIGH |

## Expected Mismatches (contextually valid — no action required)

These numbers appear to differ from METRICS.yaml but are correct in context:
historical version references, threshold definitions, or different counting scopes.

| File | Line | Claim | Extracted | Metrics Value | Reason |
|------|------|-------|-----------|---------------|--------|
| `manuscript/05_conclusion.md` | 13 | `Ten-stage` | 10 | 8 | Potential discrepancy: manuscript describes 10-stage DAG; METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends. |
| `manuscript/05_conclusion.md` | 19 | `v0.4.0` | 0.4.0 | 0.5.0 | Historical reference: describes v0.4.0 behaviour, not current version |
| `manuscript/05_conclusion.md` | 33 | `v0.2.0` | 0.2.0 | 0.5.0 | Historical reference: describes items shipped in v0.2.0 |
| `manuscript/06_03_performance_and_fixture_metrics.md` | 23 | `v0.1.0` | 0.1.0 | 0.5.0 | Historical reference: describes v0.1.0 behaviour or table label |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 34 | `coverage (same block) | 100%` | 100.0 | 90.77 | Module-level coverage: 100% for cogant.gnn.matrices in Table 9, not overall |
| `manuscript/06_05_reproducible_recording.md` | 12 | `ten-stage` | 10 | 8 | Potential discrepancy: manuscript describes 10-stage DAG; METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends. |
| `manuscript/06_05_reproducible_recording.md` | 64 | `ten-stage` | 10 | 8 | Potential discrepancy: manuscript describes 10-stage DAG; METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends. |
| `manuscript/06_experimental_setup.md` | 132 | `v0.1.0` | 0.1.0 | 0.5.0 | Historical reference: describes v0.1.0 behaviour or table label |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 57 | `ε ≥ 0.5` | 0.5 | 1.0 | Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 58 | `ε < 0.5` | 0.5 | 1.0 | Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 75 | `ε ≥ 0.5` | 0.5 | 1.0 | Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim |
| `manuscript/S02_appendix_ablation.md` | 26 | `coverage 80.0 %` | 80.0 | 90.77 | Ablation metric: 80% is semantic coverage (role precision/recall), not line coverage |
| `manuscript/S03_appendix_galois_sketch.md` | 138 | `ε ≥ 0.5` | 0.5 | 1.0 | Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim |

## Unverified Claims

These numbers were extracted but have no corresponding METRICS.yaml entry to compare against.
Consider adding them to METRICS.yaml for future tracking.

| File | Line | Pattern | Extracted | Context |
|------|------|---------|-----------|---------|
| `manuscript/06_03_performance_and_fixture_metrics.md` | 34 | shipped_fixture_count | 6 | errors and zero warnings. The six fixtures together cover one-to-six fil |
| `manuscript/06_experimental_setup.md` | 143 | shipped_fixture_count | 6 | errors and zero warnings. The six fixtures together cover one-to-six fil |
| `manuscript/S03_appendix_galois_sketch.md` | 11 | node_kind_count | 14 | in the sense of Section 2.2 (14 node kinds, 11 |
| `manuscript/S05_appendix_extended_related_work.md` | 17 | node_kind_count | 14 | ram graph reference; COGANT's 14 node kinds and 11 edge kinds |
| `manuscript/S05_appendix_extended_related_work.md` | 17 | edge_kind_count | 11 | e; COGANT's 14 node kinds and 11 edge kinds |
| `manuscript/S05_appendix_extended_related_work.md` | 131 | node_kind_count | 14 | sification parallels COGANT's 14 node kinds. |

## Stale Archive Claims

These numbers appear in `manuscript/_archive/` files. They reflect an older state
of the codebase and are expected to differ from current METRICS.yaml values.
No action required unless an archive file is being actively used.

| File | Line | Pattern | Extracted | Current Metrics Value | Context |
|------|------|---------|-----------|----------------------|---------|
_No stale archive claims found._

## Action Items

### High priority — fix these mismatches before submission

- **isomorphic_count**: was `14`, should be `23`, confidence `LOW`, Δ=39.13% — update `manuscript/S01_appendix_roundtrip_epsilon.md` (first occurrence line 76)

### Medium priority — add to METRICS.yaml for tracking

- Add `edge_kind_count` to METRICS.yaml so future audits can verify it automatically
- Add `node_kind_count` to METRICS.yaml so future audits can verify it automatically
- Add `shipped_fixture_count` to METRICS.yaml so future audits can verify it automatically

### Low priority — expected mismatches (verify intent)

- **stage_count** = `10` in `manuscript/05_conclusion.md` line 13: Potential discrepancy: manuscript describes 10-stage DAG; METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends.
- **version** = `0.4.0` in `manuscript/05_conclusion.md` line 19: Historical reference: describes v0.4.0 behaviour, not current version
- **version** = `0.2.0` in `manuscript/05_conclusion.md` line 33: Historical reference: describes items shipped in v0.2.0
- **version** = `0.1.0` in `manuscript/06_03_performance_and_fixture_metrics.md` line 23: Historical reference: describes v0.1.0 behaviour or table label
- **coverage_percent** = `100.0` in `manuscript/06_04_tests_mutation_and_benchmarks.md` line 34: Module-level coverage: 100% for cogant.gnn.matrices in Table 9, not overall
- **mean_epsilon** = `0.5` in `manuscript/S01_appendix_roundtrip_epsilon.md` line 57: Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim
- **coverage_percent** = `80.0` in `manuscript/S02_appendix_ablation.md` line 26: Ablation metric: 80% is semantic coverage (role precision/recall), not line coverage

## Injection Commands

For each MISMATCH below, the sed command replaces the manuscript value with the
METRICS.yaml value. **User decision required** before running: verify that the
METRICS.yaml value is authoritative, then apply.

```bash
# File: manuscript/S01_appendix_roundtrip_epsilon.md  line 76
# Manuscript says: '14 / 23 ISOMORPHIC'  (extracted: 14)
# Metrics says:    23
# Fix: (user decision — update metric or keep prose explanation)
sed -i '' 's/14/23/g' manuscript/S01_appendix_roundtrip_epsilon.md
```

---

_This report is generated by `tools/audit_manuscript_numbers.py`._
_Re-run after any manuscript edit or metrics update to keep it current._
