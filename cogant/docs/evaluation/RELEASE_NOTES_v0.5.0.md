# COGANT Release Evidence

This page remains as a stable link target. Current release-facing evidence lives
in:

- [V1.0 readiness](V1.0_READINESS.md)
- [Evaluation report](FINAL_REPORT.md)
- [Roundtrip evaluation](ROUNDTRIP_EVAL.md)
- [`evaluation/METRICS.yaml`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/evaluation/METRICS.yaml)

## Current Release Metrics

| Metric | Value |
| --- | ---: |
| Version | 0.6.0 |
| Tests | 9,687 passing / 0 failing / 4 skipped |
| Coverage | 95.55% |
| mypy strict errors | 0 |
| ruff violations | 0 |
| Translation rules | 22 |
| Roundtrip targets | 24 |
| ROLE_PRESERVED | 24 |
| DRIFT | 0 |
| FAILED | 0 |
| Strict structural isomorphism | 0 |

## Current Release Claim

COGANT supports a scoped artifact-generation claim for supported Python
repositories and fixture-level role preservation. It does not claim strict
structural isomorphism, arbitrary-program semantic equivalence, calibrated
probabilities, or held-out generalization.

## Release Gates

```bash
uv run --directory cogant pytest tests/ -q
uv run --directory cogant ruff check py/cogant tests
uv run --directory cogant mypy py/cogant
uv run python tools/check_metrics_fresh.py
uv run python tools/audit_docs_constants.py
uv run --directory cogant python docs/verify_doc_links.py
```
