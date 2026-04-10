# Manuscript Number Audit

**Generated:** 2026-04-10  
**METRICS.yaml source:** cogant/evaluation/METRICS.yaml  
**Manuscript directory:** manuscript  

## Summary

| Status | Count | Description |
|--------|-------|-------------|
| MISMATCH | 9 | Real data drift — update manuscript or METRICS.yaml |
| EXPECTED_MISMATCH | 14 | Contextually valid — historical refs, scope differences, threshold definitions |
| MATCH | 23 | Verified correct |
| UNVERIFIED | 0 | No METRICS.yaml entry to compare against |
| STALE_ARCHIVE | 17 | In _archive/ — expected to differ |
| **Total findings** | **63** | |

## Reference Values (from METRICS.yaml / fallback)

| Variable | Path | Value |
|----------|------|-------|
| test_count_passing | `testing.test_count_passing` | `0` |
| test_count_total | `testing.test_count_total` | `2160` |
| coverage_percent | `testing.coverage_percent` | `0.0` (±0.5) |
| version | `package.version` | `0.5.0` |
| isomorphic_count | `evaluation.roundtrip.isomorphic_count` | `14` |
| total_targets | `evaluation.roundtrip.total_targets` | `23` |
| approximate_count | `evaluation.roundtrip.approximate_count` | `6` |
| divergent_count | `evaluation.roundtrip.divergent_count` | `3` |
| mean_epsilon | `evaluation.roundtrip.mean_epsilon` | `0.8092` (±0.01) |
| median_epsilon | `evaluation.roundtrip.median_epsilon` | `0.8638` (±0.01) |
| min_epsilon | `evaluation.roundtrip.min_epsilon` | `0.4147` (±0.01) |
| max_epsilon | `evaluation.roundtrip.max_epsilon` | `1.0` (±0.01) |
| translation_rules | `pipeline.translation_rules` | `19` |
| stage_count | `pipeline.stage_count` | `8` |
| python_source_files | `codebase.python_source_files` | `179` |
| python_loc | `codebase.python_loc` | `56481` |

## Mismatches (action required)

These manuscript claims do not match METRICS.yaml. Update the manuscript or fix the metrics.

| File | Line | Claim | Extracted | Metrics Value | Context |
|------|------|-------|-----------|---------------|---------|
| `manuscript/00_abstract.md` | 7 | `23 / 23 ISOMORPHIC` | 23 | 14 | erse--forward round-trip is **23 / 23 ISOMORPHIC** ($\varepsilon \geq 0.8$) on |
| `manuscript/00_abstract.md` | 9 | `2146 passing` | 2146 | 0 | ere. The test suite reports **2146 passing** tests, **11 skips**, 2 expe |
| `manuscript/00_abstract.md` | 9 | `coverage is about 86.5%` | 86.5 | 0.0 | `xpass`; **`py/cogant/` line coverage is about 86.5%** (last aligned measurement * |
| `manuscript/00_abstract.md` | 9 | `~86.45%` | 86.45 | 0.0 | * (last aligned measurement **~86.45%**) under `pytest --cov` on th |
| `manuscript/05_conclusion.md` | 19 | `23 / 23 ISOMORPHIC` | 23 | 14 | d-reverse-forward round-trip: 23 / 23 ISOMORPHIC.** The v0.5.0 reverse synthes |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 5 | `2146 passing` | 2146 | 0 | cov=py/cogant` run, reports **2146 passing** tests with **11 skips** for |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 5 | `coverage of `py/cogant/` is **86.45%` | 86.45 | 0.0 | onical run); the overall line coverage of `py/cogant/` is **86.45%** on that run, measured acros |
| `manuscript/06_experimental_setup.md` | 192 | `2146 passing tests` | 2146 | 0 | ation ships a test suite of **2146 passing tests** with **11 skips** for optio |
| `manuscript/06_experimental_setup.md` | 192 | `coverage of `py/cogant/` is **86.45%` | 86.45 | 0.0 | .0 run), and the overall line coverage of `py/cogant/` is **86.45%**, measured against the 20 30 |

## Matches (verified correct)

| File | Line | Claim | Value | Pattern |
|------|------|-------|-------|---------|
| `manuscript/00_abstract.md` | 7 | `v0.5.0` | 0.5.0 | version |
| `manuscript/00_abstract.md` | 7 | `23 / 23 ISOMORPHIC` | 23 | total_targets |
| `manuscript/00_abstract.md` | 7 | `19 declarative rules` | 19 | translation_rules |
| `manuscript/00_abstract.md` | 9 | `v0.5.0` | 0.5.0 | version |
| `manuscript/05_conclusion.md` | 7 | `v0.5.0` | 0.5.0 | version |
| `manuscript/05_conclusion.md` | 19 | `v0.5.0` | 0.5.0 | version |
| `manuscript/05_conclusion.md` | 19 | `23 / 23 ISOMORPHIC` | 23 | total_targets |
| `manuscript/05_conclusion.md` | 25 | `19 shipped rules` | 19 | translation_rules |
| `manuscript/05_conclusion.md` | 33 | `v0.5.0` | 0.5.0 | version |
| `manuscript/05_conclusion.md` | 35 | `v0.5.0` | 0.5.0 | version |
| `manuscript/05_conclusion.md` | 37 | `v0.5.0` | 0.5.0 | version |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 5 | `v0.5.0` | 0.5.0 | version |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 5 | `179 source files` | 179 | python_source_files |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 19 | `v0.5.0` | 0.5.0 | version |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 47 | `v0.5.0` | 0.5.0 | version |
| `manuscript/06_05_reproducible_recording.md` | 65 | `v0.5.0` | 0.5.0 | version |
| `manuscript/06_experimental_setup.md` | 192 | `v0.5.0` | 0.5.0 | version |
| `manuscript/06_experimental_setup.md` | 204 | `v0.5.0` | 0.5.0 | version |
| `manuscript/08_03_lenses_and_synthesis.md` | 7 | `v0.5.0` | 0.5.0 | version |
| `manuscript/08_scope_and_related_work.md` | 83 | `v0.5.0` | 0.5.0 | version |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 76 | `14 / 23 ISOMORPHIC` | 14 | isomorphic_count |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 76 | `14 / 23 ISOMORPHIC` | 23 | total_targets |
| `manuscript/S03_appendix_galois_sketch.md` | 73 | `19 translation rules` | 19 | translation_rules |

## Expected Mismatches (contextually valid — no action required)

These numbers appear to differ from METRICS.yaml but are correct in context:
historical version references, threshold definitions, or different counting scopes.

| File | Line | Claim | Extracted | Metrics Value | Reason |
|------|------|-------|-----------|---------------|--------|
| `manuscript/05_conclusion.md` | 13 | `Ten-stage` | 10 | 8 | Potential discrepancy: manuscript describes 10-stage DAG (CLAUDE.md); METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends. |
| `manuscript/05_conclusion.md` | 19 | `v0.4.0` | 0.4.0 | 0.5.0 | Historical reference: describes v0.4.0 behaviour, not current version |
| `manuscript/05_conclusion.md` | 33 | `v0.2.0` | 0.2.0 | 0.5.0 | Historical reference: describes items shipped in v0.2.0 |
| `manuscript/06_03_performance_and_fixture_metrics.md` | 23 | `v0.1.0` | 0.1.0 | 0.5.0 | Historical reference: describes v0.1.0 behaviour or table label |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 5 | `20,307 statements` | 20307 | 56481 | Scope difference: manuscript counts py/cogant/ statements (20,307); METRICS.yaml counts full-repo Python LOC (56,481) |
| `manuscript/06_04_tests_mutation_and_benchmarks.md` | 34 | `coverage (same block) | 100%` | 100.0 | 0.0 | Module-level coverage: 100% for cogant.gnn.matrices in Table 9, not overall |
| `manuscript/06_05_reproducible_recording.md` | 12 | `ten-stage` | 10 | 8 | Potential discrepancy: manuscript describes 10-stage DAG (CLAUDE.md); METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends. |
| `manuscript/06_05_reproducible_recording.md` | 64 | `ten-stage` | 10 | 8 | Potential discrepancy: manuscript describes 10-stage DAG (CLAUDE.md); METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends. |
| `manuscript/06_experimental_setup.md` | 132 | `v0.1.0` | 0.1.0 | 0.5.0 | Historical reference: describes v0.1.0 behaviour or table label |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 57 | `ε ≥ 0.5` | 0.5 | 0.8092 | Threshold definition: ε ≥ 0.5 defines ISOMORPHIC tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 58 | `ε < 0.5` | 0.5 | 0.8092 | Threshold definition: ε ≥ 0.5 defines ISOMORPHIC tier boundary, not a data claim |
| `manuscript/S01_appendix_roundtrip_epsilon.md` | 75 | `ε ≥ 0.5` | 0.5 | 0.8092 | Threshold definition: ε ≥ 0.5 defines ISOMORPHIC tier boundary, not a data claim |
| `manuscript/S02_appendix_ablation.md` | 26 | `coverage 80.0 %` | 80.0 | 0.0 | Ablation metric: 80% is semantic coverage (role precision/recall), not line coverage |
| `manuscript/S03_appendix_galois_sketch.md` | 138 | `ε ≥ 0.5` | 0.5 | 0.8092 | Threshold definition: ε ≥ 0.5 defines ISOMORPHIC tier boundary, not a data claim |

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
| `manuscript/_archive/cogant_paper_monolith.md` | 9 | test_count_passing | 1945 | 0 | rectly. The system ships with 1945 passing tests across Python 3.11--3.13 and |
| `manuscript/_archive/cogant_paper_monolith.md` | 9 | coverage_percent | 86.0 | 0.0 | across Python 3.11--3.13 and 86% line coverage; forward and reverse pipeline |
| `manuscript/_archive/cogant_paper_monolith.md` | 78 | translation_rules | 19 | 19 | The 19 translation rules are organized into five famil |
| `manuscript/_archive/cogant_paper_monolith.md` | 158 | version | 0.4.0 | 0.5.0 | evel pipeline metrics (COGANT v0.4.0).** |
| `manuscript/_archive/cogant_paper_monolith.md` | 183 | version | 0.4.0 | 0.5.0 | worst-case epsilon for COGANT v0.4.0 is epsilon_max = 0.6, arising |
| `manuscript/_archive/cogant_paper_monolith.md` | 194 | mean_epsilon | 0.8 | 0.8092 | \| ISOMORPHIC (ε ≥ 0.80) \| 14 (61%) \| 0.80–1.00 \| zoo |
| `manuscript/_archive/cogant_paper_monolith.md` | 195 | mean_epsilon | 0.8 | 0.8092 | \| APPROXIMATE (0.50 ≤ ε < 0.80) \| 6 \| 0.51–0.79 \| tqdm (0.57 |
| `manuscript/_archive/cogant_paper_monolith.md` | 196 | mean_epsilon | 0.5 | 0.8092 | \| DIVERGENT (ε < 0.50) \| 3 \| 0.00–0.49 \| httpx, url |
| `manuscript/_archive/cogant_paper_monolith.md` | 198 | mean_epsilon | 0.8 | 0.8092 | ve ISOMORPHIC classification (ε ≥ 0.80), including zoo fixtures zoo/ |
| `manuscript/_archive/cogant_paper_monolith.md` | 198 | mean_epsilon | 0.8638 | 0.8092 | eal-world libraries dateutil (ε=0.8638) and pyyaml (ε=0.8520). DIVER |
| `manuscript/_archive/cogant_paper_monolith.md` | 198 | mean_epsilon | 0.852 | 0.8092 | teutil (ε=0.8638) and pyyaml (ε=0.8520). DIVERGENT real-world reposi |
| `manuscript/_archive/cogant_paper_monolith.md` | 244 | coverage_percent | 19.0 | 0.0 | lask_app` recall from 100% to ~19%. The structural family is ess |
| `manuscript/_archive/cogant_paper_monolith.md` | 307 | version | 0.1.0 | 0.5.0 | nstant (epsilon_max = 0.6 for v0.1.0) that depends only on the rul |
| `manuscript/_archive/cogant_paper_monolith.md` | 309 | version | 0.2.0 | 0.5.0 | d drive epsilon_max to 0.2 in v0.2.0. |
| `manuscript/_archive/cogant_paper_monolith.md` | 343 | test_count_passing | 1945 | 0 | models. The system ships with 1945 passing tests across Python 3.11--3.13 and |
| `manuscript/_archive/cogant_paper_monolith.md` | 343 | coverage_percent | 86.0 | 0.0 | across Python 3.11--3.13 and 86% line coverage, with forward and reverse pip |
| `manuscript/_archive/cogant_paper_monolith.md` | 343 | mean_epsilon | 0.8 | 0.8092 | world libraries) demonstrates ε ≥ 0.80 (ISOMORPHIC) on 19 targets (8 |

## Action Items

### High priority — fix these mismatches before submission

- **isomorphic_count**: manuscript says `23`, METRICS.yaml says `14` — update `manuscript/00_abstract.md` (first occurrence line 7)
- **test_count_passing**: manuscript says `2146`, METRICS.yaml says `0` — update `manuscript/00_abstract.md` (first occurrence line 9)
- **coverage_percent**: manuscript says `86.5`, METRICS.yaml says `0.0` — update `manuscript/00_abstract.md` (first occurrence line 9)
- **coverage_percent**: manuscript says `86.45`, METRICS.yaml says `0.0` — update `manuscript/00_abstract.md` (first occurrence line 9)

### Low priority — expected mismatches (verify intent)

- **stage_count** = `10` in `manuscript/05_conclusion.md` line 13: Potential discrepancy: manuscript describes 10-stage DAG (CLAUDE.md); METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends.
- **version** = `0.4.0` in `manuscript/05_conclusion.md` line 19: Historical reference: describes v0.4.0 behaviour, not current version
- **version** = `0.2.0` in `manuscript/05_conclusion.md` line 33: Historical reference: describes items shipped in v0.2.0
- **version** = `0.1.0` in `manuscript/06_03_performance_and_fixture_metrics.md` line 23: Historical reference: describes v0.1.0 behaviour or table label
- **python_loc** = `20307` in `manuscript/06_04_tests_mutation_and_benchmarks.md` line 5: Scope difference: manuscript counts py/cogant/ statements (20,307); METRICS.yaml counts full-repo Python LOC (56,481)
- **coverage_percent** = `100.0` in `manuscript/06_04_tests_mutation_and_benchmarks.md` line 34: Module-level coverage: 100% for cogant.gnn.matrices in Table 9, not overall
- **mean_epsilon** = `0.5` in `manuscript/S01_appendix_roundtrip_epsilon.md` line 57: Threshold definition: ε ≥ 0.5 defines ISOMORPHIC tier boundary, not a data claim
- **coverage_percent** = `80.0` in `manuscript/S02_appendix_ablation.md` line 26: Ablation metric: 80% is semantic coverage (role precision/recall), not line coverage

---

_This report is generated by `tools/audit_manuscript_numbers.py`._
_Re-run after any manuscript edit or metrics update to keep it current._
