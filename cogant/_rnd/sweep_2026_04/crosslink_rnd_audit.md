# Wave 19 — R&D ↔ Published Docs Crosslink Audit

Date: 2026-04-10
Agent: `crosslink-rnd-to-docs-agent`
Working dir: `/Users/4d/Documents/GitHub/template/projects_in_progress/cogant/cogant`

## Goal

Every R&D doc must link back to the corresponding published docs page **and** to the
implementing Python module(s). Refresh stale benchmark data where it lingered
(14/23 → 23/23) so the audit also re-grounds numeric facts.

## Files updated

| File | Action |
|---|---|
| `docs/evaluation/V1.0_READINESS.md` | Marked the "roundtrip re-benchmark" and "POLICY/CONTEXT synthesis" rows as DONE; removed the broken `.github/workflows/ci.yml` link from the See-also block; added See-also section linking to METRICS.yaml, ROUNDTRIP_EVAL, R&D_LOG, ACTIVE_INFERENCE_MAPPING, CONSTRAINT_FIX, and the implementing reverse/translate/gnn modules. |
| `docs/evaluation/ROUNDTRIP_EVAL.md` | Added See-also section linking to `docs/concepts/roundtrip.md`, CONSTRAINT_FIX, V1.0_READINESS, METRICS.yaml, the dataset directory, the regenerate.py driver, and the four reverse-pipeline implementing modules. (Header/numbers were already current at 23/23, mean ε = 1.0; the parallel-running coherence agent had refreshed them.) |
| `docs/evaluation/CALIBRATION.md` | Added See-also section linking to `docs/rnd/calibration.md`, ACTIVE_INFERENCE_MAPPING, `docs/reference/translation_rules.md`, and eight implementing modules (confidence, engine, rules/, gnn/matrices, gnn/validator, statespace/compiler, statespace/temporal, scoring/metrics). |
| `docs/evaluation/BENCHMARK_VS_PRIOR.md` | Added See-also section linking to ROUNDTRIP_EVAL, CALIBRATION, ACTIVE_INFERENCE_MAPPING, `docs/concepts/roundtrip.md`, `docs/reference/translation_rules.md`, and the five rule-family modules + gnn/matrices + gnn/validator. |
| `docs/evaluation/ACTIVE_INFERENCE_MAPPING.md` | Added See-also section linking to `docs/concepts/active_inference.md`, `docs/concepts/markov_blanket.md`, `docs/rnd/active_inference_mapping.md`, CALIBRATION, ROUNDTRIP_EVAL, and 9 implementing modules across translate/rules, markov, statespace, gnn. |
| `docs/evaluation/MUTATION_REPORT.md` | Added See-also section linking to `_rnd/sweep_2026_04/mutation_testing_result.md`, CALIBRATION, ACTIVE_INFERENCE_MAPPING, V1.0_READINESS, two existing mutation test files (`test_mutation_killers_w18.py` + `test_mutation_hardening.py`), and 6 modules under test. |
| `docs/evaluation/CONSTRAINT_FIX.md` | Added See-also section linking to `docs/reference/translation_rules.md`, ROUNDTRIP_EVAL, `_rnd/sweep_2026_04/benchmark_refresh_result.md`, V1.0_READINESS, and the three implementing modules (synthesizer, planner, semantic.py PreferenceRule). |
| `docs/evaluation/R&D_LOG.md` | Added See-also section at the bottom linking to all sister evaluation docs, sweep_2026_04 notes, METRICS.yaml, and the major forward+reverse module trees. |
| `docs/rnd/active_inference_mapping.md` | Added See-also section linking back to `docs/evaluation/ACTIVE_INFERENCE_MAPPING.md`, the published concept pages, CALIBRATION, and 8 implementing modules. |
| `docs/rnd/calibration.md` | Added See-also section linking to `docs/evaluation/CALIBRATION.md`, the R&D AI mapping mirror, `docs/reference/translation_rules.md`, and 6 implementing modules. |
| `_rnd/sweep_2026_04/benchmark_refresh_result.md` | Added See-also section linking to ROUNDTRIP_EVAL, CONSTRAINT_FIX, V1.0_READINESS, METRICS.yaml, regenerate.py driver, the JSONL results file, and the four reverse-pipeline implementing modules. |
| `_rnd/sweep_2026_04/mutation_testing_result.md` | Added See-also section linking to MUTATION_REPORT, CALIBRATION, V1.0_READINESS, the two existing mutation test suites, and the four modules under test. |

## Numbers updated

- `docs/evaluation/V1.0_READINESS.md` "What's missing" gap-table: marked
  *Roundtrip re-benchmark after wave-16* and *POLICY/CONTEXT synthesis in reverse*
  as DONE (the fixes landed in wave 16/18 and the full re-run is captured in the
  refreshed ROUNDTRIP_EVAL.md and `_rnd/sweep_2026_04/benchmark_refresh_result.md`).
- `docs/evaluation/ROUNDTRIP_EVAL.md` was already 23/23 ISOMORPHIC at the start of
  this agent's run (refreshed by another wave-19 agent in parallel), so no further
  numeric edits were needed. The benchmark table already shows ε = 1.0000 for all
  23 targets and the distribution row reads "ISOMORPHIC: 23/23 (100%)".

## Link-resolution audit

All `[label](path)` and inline-code paths added by this agent were spot-checked
with `ls`. The full set of unique link targets touched:

- `docs/evaluation/{V1.0_READINESS,ROUNDTRIP_EVAL,CALIBRATION,BENCHMARK_VS_PRIOR,ACTIVE_INFERENCE_MAPPING,MUTATION_REPORT,CONSTRAINT_FIX,R&D_LOG}.md` — present
- `docs/rnd/{active_inference_mapping,calibration}.md` — present
- `docs/concepts/{active_inference,markov_blanket,roundtrip}.md` — present
- `docs/reference/translation_rules.md` — present
- `evaluation/METRICS.yaml`, `evaluation/dataset/regenerate.py`, `evaluation/dataset/roundtrip_results.jsonl` — present
- `_rnd/sweep_2026_04/{benchmark_refresh_result,mutation_testing_result}.md` — present
- `py/cogant/reverse/{synthesizer,idempotency,planner,parser}.py` — present
- `py/cogant/translate/confidence.py`, `py/cogant/translate/engine.py` — present
- `py/cogant/translate/rules/{semantic,structural,behavioral,control,resilience}.py` — present
- `py/cogant/gnn/{matrices,validator}.py` — present
- `py/cogant/markov/{extractor,blanket}.py` — present
- `py/cogant/statespace/{compiler,temporal}.py` — present
- `py/cogant/scoring/metrics.py`, `py/cogant/static/dataflow.py` — present
- `tests/unit/test_mutation_killers_w18.py`, `tests/unit/test_mutation_hardening.py` — present

### Removed broken link

- `docs/evaluation/V1.0_READINESS.md`: removed `.github/workflows/ci.yml` from the
  See-also block. The CI workflow lives at `projects_in_progress/cogant/.github/`
  (parent of the `cogant/cogant/` subrepo) and is not reachable via a relative path
  from inside `docs/evaluation/`. Mentioned in the prose as a fact, not a link.

### Corrected dangling link before publishing

- Initial draft of `MUTATION_REPORT.md`'s See-also block listed three hardening
  test files (`test_gnn_matrices_mutation_hardening.py`, `test_markov_mutation_hardening.py`,
  `test_statespace_compiler_mutation_hardening.py`) — none of those filenames exist
  in the repo (`find` confirmed only `test_mutation_killers_w18.py` and
  `test_mutation_hardening.py` are present). The block was rewritten to point to
  the two real files only. Note: the body of MUTATION_REPORT.md still mentions
  the hardening filenames in prose; that prose is historical and was not edited
  in this pass to avoid scope creep beyond the See-also requirement.

## Manuscript exclusion

No file under `manuscript/` was opened, read, or written by this agent. Confirmed
by limiting all Edit calls to `docs/`, `_rnd/`, and (read-only) the `py/`,
`tests/`, and `evaluation/` trees.

## Commit

Commit message: `docs(w19/crosslink): R&D docs → published docs + module cross-references`
