# Appendix A — Roundtrip Role Preservation {#sec:S01-appendix-roundtrip-epsilon}

This appendix reports the native v{{VERSION}} roundtrip ledger used by the main
text. The authoritative aggregate values are injected from
[`../cogant/evaluation/METRICS.yaml`](../cogant/evaluation/METRICS.yaml); the
per-target rows are checked in at
[`../cogant/evaluation/dataset/roundtrip_results.jsonl`](../cogant/evaluation/dataset/roundtrip_results.jsonl).

## A.1 Current aggregate ledger

| Metric | Value |
|---|---:|
| Total targets | {{TOTAL_TARGETS}} |
| `ROLE_PRESERVED` targets | {{ROLE_PRESERVED_COUNT}} |
| `DRIFT` targets | {{DRIFT_COUNT}} |
| `FAILED` targets | {{FAILED_COUNT}} |
| `STRUCTURALLY_ISOMORPHIC` targets | {{STRICT_ISOMORPHISM_COUNT}} |
| Mean role-preservation score | {{MEAN_ROLE_PRESERVATION_SCORE}} |
| Median role-preservation score | {{MEDIAN_ROLE_PRESERVATION_SCORE}} |
| Minimum role-preservation score | {{MIN_ROLE_PRESERVATION_SCORE}} |
| Maximum role-preservation score | {{MAX_ROLE_PRESERVATION_SCORE}} |
| Score source | `{{ROLE_PRESERVATION_SCORE_SOURCE}}` |

: Native v{{VERSION}} roundtrip aggregate ledger. {#tbl:fresh-v06-roundtrip}

The current ledger supports a role-preservation claim for
{{ROLE_PRESERVED_COUNT}} of {{TOTAL_TARGETS}} targets at the configured threshold.
The strict structural-isomorphism count is {{STRICT_ISOMORPHISM_COUNT}}; no
current native ledger row meets that stronger contract. Threshold acceptance
does not imply identical role counts.

## A.2 Per-target status

| Target | Group | `s_role` | Status | Strict structural? |
|---|---|---:|---|---|
{{ROUNDTRIP_TARGET_ROWS}}

: Native v{{VERSION}} per-target roundtrip status. {#tbl:roundtrip-per-target-current}

The previous drift rows, `cli_tool` and `notebook_module`, now carry source
roles and roundtrip as `ROLE_PRESERVED`. They should still be treated as
controls for metric laundering: `tools/check_metrics_fresh.py` rejects
zero-origin control-positive rows before generated scaffolding can be counted
as recovered evidence.

## A.3 Status definitions

| Status | Meaning in this manuscript |
|---|---|
| `STRUCTURALLY_ISOMORPHIC` | Role population, graph size, edge-kind distribution, matrices, GNN sections, and generated-code checks all pass. |
| `ROLE_PRESERVED` | The Active Inference role-overlap score meets the public threshold, while one or more stricter invariants may drift. |
| `DRIFT` | The roundtrip completed, but role preservation is below threshold or non-fatal invariants diverge. |
| `FAILED` | The roundtrip did not complete successfully. |

The public role-preservation threshold is
`s_role >= {{THRESHOLD_ROLE_PRESERVED}}`. Strict structural isomorphism is
reported separately because role preservation alone does not imply equal node
counts, edge counts, matrix values, or generated source.

## A.4 Reproducibility

Run the current freshness and manuscript-facing checks from the project root:

```bash
uv run python tools/check_metrics_fresh.py
uv run python tools/audit_manuscript_numbers.py
uv run python tools/claim_ledger.py --manuscript-dir manuscript \
  --output-dir output/claim_ledger --fail-on-literal-numbers
```

When the ledger changes, regenerate `METRICS.yaml`, refresh the manuscript
variables, and rerun the docs/manuscript link audits before relying on the new
counts.
