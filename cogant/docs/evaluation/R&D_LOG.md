# COGANT Research and Development Status

This page records the current evaluation posture for release-facing readers.

## Current Metrics

| Metric | Value |
| --- | ---: |
| Version | 0.6.0 |
| Tests | 9,697 passing / 0 failing / 5 skipped |
| Coverage | 95.55% |
| mypy strict errors | 0 |
| ruff violations | 0 |
| Runner stages | 10 |
| Translation rules | 22 |
| Roundtrip targets | 25 |
| ROLE_PRESERVED | 25 |
| DRIFT | 0 |
| FAILED | 0 |
| Strict structural isomorphism | 1 |

## Current Gate Status

| Gate | Status |
| --- | --- |
| Forward Python pipeline | Complete for supported fixtures |
| Reverse package synthesis | Complete with role-preservation caveat |
| Roundtrip role ledger | Current native JSONL and generated metrics |
| Strict structural roundtrip | Achieved only by `roundtrip_strict_minimal` |
| Dynamic enrichment | Implemented, operator workflow needs documentation |
| Rust backend | Partial acceleration path, not full parity |
| Documentation link integrity | Verified by `docs/verify_doc_links.py` |
| Manuscript number/citation/crossref checks | Verified by project tools |

## Active Work Needed

1. Promote the existing held-out pilot into a frozen Python repository corpus and rerun the native ledger.
2. Add native JS/TS roundtrip rows or keep cross-language results separate.
3. Reduce graph, matrix, section, and generated-code deltas enough to earn
   strict structural successes beyond the deliberately minimal reversible subset.
4. Document dynamic enrichment end to end with trace fixtures.
5. Build a reviewer-labeled corpus for confidence and matrix calibration.

## Canonical Evidence Pages

- [V1.0 readiness](V1.0_READINESS.md)
- [Evaluation report](FINAL_REPORT.md)
- [Roundtrip evaluation](ROUNDTRIP_EVAL.md)
- [Roundtrip validation contract](ROUNDTRIP_VALIDATION.md)
- [Current reverse-synthesis status](ROUNDTRIP_IMPROVEMENT.md)
- [`evaluation/METRICS.yaml`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/evaluation/METRICS.yaml)
