# COGANT Roundtrip Synthesis Status

**Current source of truth:** [`evaluation/METRICS.yaml`](https://github.com/docxology/cogant/blob/main/evaluation/METRICS.yaml) and [`evaluation/dataset/roundtrip_results.jsonl`](https://github.com/docxology/cogant/blob/main/evaluation/dataset/roundtrip_results.jsonl).

This page describes the current reverse-synthesis status, not a dated change log.

## Current Result

| Metric | Value |
| --- | ---: |
| Targets | 24 |
| ROLE_PRESERVED | 24 |
| DRIFT | 0 |
| FAILED | 0 |
| Strict structural isomorphism | 0 |
| Mean role-preservation score | 1.0000 |
| Median role-preservation score | 1.0000 |

The reverse synthesizer preserves semantic-role populations for all shipped native
fixtures, but no target currently clears the stricter structural-isomorphism
contract. Release-facing language should therefore say **role-preserved**, not
**isomorphic**.

## Current Reverse-Synthesis Mechanism

The reverse path is:

```text
parse_gnn -> plan_package -> synthesize_package -> forward COGANT bundle
```

The synthesizer emits:

- state, observation, action, policy, constraint, matrix, context, and main
  modules for the generated package;
- POLICY / CONTEXT / CONSTRAINT scaffolds proportional to the origin role counts;
- generated-code metadata consumed by the roundtrip ledger; and
- enough package structure for the second forward pass to recover semantic-role
  populations when the source GNN carries usable role evidence.

## Current Failure Modes

The previous DRIFT rows, `cli_tool` and `notebook_module`, now carry source
HIDDEN_STATE, OBSERVATION, and ACTION roles and roundtrip as `ROLE_PRESERVED`.
They remain useful controls because `tools/check_metrics_fresh.py` still rejects
zero-origin control-positive rows that would otherwise launder generated
scaffolding into a saturated pass rate.

## Validation Commands

```bash
cd cogant
uv run python ../tools/regenerate_roundtrip_ledger.py
uv run python ../tools/regenerate_metrics.py
uv run python ../tools/check_metrics_fresh.py
```

For local smoke checks:

```bash
uv run pytest tests/integration/test_reverse_roundtrip.py -q --no-cov
uv run pytest tests/integration/test_reverse_roundtrip_fixtures.py -q --no-cov
uv run pytest tests/unit/test_metrics_api.py -q --no-cov
```

## What Remains

- Promote the existing held-out pilot into a frozen metrics/claim pipeline with no rule tuning after selection.
- Add JS/TS targets to the native roundtrip ledger, or keep cross-language
  evidence separate from Python-front-end release claims.
- Add one more small permissively licensed held-out fixture to stress the now-saturated in-sample ledger.
