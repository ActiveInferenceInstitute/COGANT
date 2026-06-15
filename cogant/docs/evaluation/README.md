# Evaluation

Current evidence for COGANT's release-facing claims.

Machine-readable artifacts live under the repository-level `evaluation/`
directory. The most important files are:

- [`evaluation/METRICS.yaml`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/evaluation/METRICS.yaml)
- [`evaluation/dataset/roundtrip_results.jsonl`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/evaluation/dataset/roundtrip_results.jsonl)

## Current Status

| Page | Purpose |
| --- | --- |
| [V1.0 readiness](V1.0_READINESS.md) | Scope, claim boundaries, and remaining release work |
| [Evaluation report](FINAL_REPORT.md) | Current evidence summary |
| [R&D status](R&D_LOG.md) | Current gate status and active work |
| [Roundtrip evaluation](ROUNDTRIP_EVAL.md) | Native 25-target role-preservation ledger with one strict minimal fixed point |
| [Roundtrip validation contract](ROUNDTRIP_VALIDATION.md) | How roundtrip results are classified |
| [Current reverse-synthesis status](ROUNDTRIP_IMPROVEMENT.md) | Reverse-package mechanism and failure modes |
| [Empirical claim](EMPIRICAL_CLAIM.md) | Claim wording and evidence limits |
| [Calibration](CALIBRATION.md) | Confidence and matrix calibration backlog |
| [Scaling analysis](SCALING_ANALYSIS.md) | Current scaling constraints and regression targets |
| [Cross-language roundtrip](CROSS_LANG_ROUNDTRIP.md) | Language-pair evidence outside the Python native ledger |
| [GNN validation report](GNN_VALIDATION_REPORT.md) | Structural validation of emitted GNN packages |
| [GNN v2 audit surface](GNN_V2_AUDIT_SURFACE.md) | Version, bridge, upstream-step, and supply-chain claim boundary |
| [Mutation report](MUTATION_REPORT.md) | Mutation-testing results |
| [Literature](LITERATURE.md) | Research sources |
| [Related work](RELATED_WORK.md) | Tool and method comparison |

## Reading Order

1. [V1.0 readiness](V1.0_READINESS.md)
2. [Evaluation report](FINAL_REPORT.md)
3. [Roundtrip evaluation](ROUNDTRIP_EVAL.md)
4. [Roundtrip validation contract](ROUNDTRIP_VALIDATION.md)
5. [Calibration](CALIBRATION.md)
6. [GNN v2 audit surface](GNN_V2_AUDIT_SURFACE.md)
7. [Scaling analysis](SCALING_ANALYSIS.md)
8. [Literature](LITERATURE.md) and [Related work](RELATED_WORK.md)

## Required Gates

```bash
uv run --directory cogant pytest tests/ -q
uv run --directory cogant ruff check py/cogant tests
uv run --directory cogant mypy py/cogant
uv run python tools/check_metrics_fresh.py
uv run python tools/audit_docs_constants.py
uv run --directory cogant python docs/verify_doc_links.py
```
