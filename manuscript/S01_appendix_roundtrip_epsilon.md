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
{{ROLE_PRESERVED_COUNT}} of {{TOTAL_TARGETS}} targets. It supports a strict
structural-isomorphism claim only for the deliberately minimal reversible
fixture `roundtrip_strict_minimal`: `STRUCTURALLY_ISOMORPHIC` is
{{STRICT_ISOMORPHISM_COUNT}} in the checked-in metrics, and ordinary application
fixtures remain role-preserved rather than graph-isomorphic.

## A.2 Per-target status

| Target | Group | `s_role` | Status | Strict structural? |
|---|---|---:|---|---|
| `async_service` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `calculator` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `cli_tool` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `data_pipeline` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `event_pipeline` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `flask_mini` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `multi_package_workspace` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `notebook_module` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `plugin_architecture` | control_positive | 1.0 | `ROLE_PRESERVED` | no |
| `roundtrip_strict_minimal` | control_positive | 1.0 | `STRUCTURALLY_ISOMORPHIC` | yes |
| `flask_app` | real_world | 1.0 | `ROLE_PRESERVED` | no |
| `json_stdlib` | real_world | 1.0 | `ROLE_PRESERVED` | no |
| `requests_lib` | real_world | 1.0 | `ROLE_PRESERVED` | no |
| `01_simple_state` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `02_observer` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `03_actor` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `04_pomdp_minimal` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `05_multi_factor` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `06_hierarchical` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `07_event_driven` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `08_preferences` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `09_policy` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `10_constraint` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `11_sensor_fusion` | zoo | 1.0 | `ROLE_PRESERVED` | no |
| `12_full_pomdp` | zoo | 1.0 | `ROLE_PRESERVED` | no |

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
| `ROLE_PRESERVED` | The original Active Inference role population survives above the public threshold, while one or more stricter invariants may drift. |
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
uv run python tools/claim_ledger.py --manuscript-dir manuscript --output-dir /tmp/cogant_claim_ledger --fail-on-literal-numbers
```

When the ledger changes, regenerate `METRICS.yaml`, refresh the manuscript
variables, and rerun the docs/manuscript link audits before relying on the new
counts.
