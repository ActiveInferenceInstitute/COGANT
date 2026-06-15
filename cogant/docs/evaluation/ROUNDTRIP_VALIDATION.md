# Roundtrip Validation Contract

**Current source of truth:** [`ROUNDTRIP_EVAL.md`](ROUNDTRIP_EVAL.md), [`evaluation/METRICS.yaml`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/evaluation/METRICS.yaml), and [`evaluation/dataset/roundtrip_results.jsonl`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/evaluation/dataset/roundtrip_results.jsonl).

## Claim Under Test

For each supported Python fixture, COGANT measures whether semantic roles survive:

```text
source repo -> forward bundle -> reverse synthesized package -> forward bundle
```

The primary release metric is `role_preservation_score`, classified by
`roundtrip_status`.

## Current Classification

| Status | Rule |
| --- | --- |
| `ROLE_PRESERVED` | `role_preservation_score >= 0.5` |
| `DRIFT` | `role_preservation_score < 0.5` or role introduction/loss dominates |
| `FAILED` | roundtrip execution fails |

Strict structural isomorphism is tracked separately. It requires zero graph
deltas, preserved edge-kind counts, preserved matrix shapes and values,
preserved GNN sections, and generated-code success.

## Current Result

| Metric | Value |
| --- | ---: |
| Targets | 25 |
| ROLE_PRESERVED | 25 |
| DRIFT | 0 |
| FAILED | 0 |
| Strict structural isomorphism | 1 |
| Mean role-preservation score | 1.0000 |

The single strict row is `roundtrip_strict_minimal`, a deliberately tiny
hand-authored reversible subset with one state carrier, one observation reader,
and one action mutator. It demonstrates the invariant bar; ordinary application
fixtures remain role-preserved but not strictly structurally isomorphic.

## Validation Procedure

```bash
cd cogant
uv run python ../tools/regenerate_roundtrip_ledger.py
uv run python ../tools/regenerate_metrics.py
uv run python ../tools/check_metrics_fresh.py
```

The generated JSONL rows must contain:

- `roundtrip_status`
- `role_preservation_score`
- original and synthesized HIDDEN_STATE / OBSERVATION / ACTION counts
- graph node and edge counts
- generated-code status
- strict structural flags

`tools/check_metrics_fresh.py` re-derives the aggregate counts from the JSONL
and fails if `METRICS.yaml` reports incompatible values.

## Interpretation Boundaries

Roundtrip validation is evidence for role-population preservation on the measured
fixtures. It is not evidence for arbitrary-program semantic equivalence,
reference-device runtime behavior, calibrated probabilities, or strict graph
identity outside the explicitly strict minimal fixture.

## Required Extensions

- Promote the existing held-out pilot into a frozen metrics/claim pipeline selected before any further rule changes.
- Add native JS/TS roundtrip rows or keep cross-language evidence in a separate
  table.
- Track strict graph, matrix, GNN-section, and generated-code deltas as release
  criteria rather than relying on role counts alone.
