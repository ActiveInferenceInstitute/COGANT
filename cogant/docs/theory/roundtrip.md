# Round-Trip Verification: Forward → Reverse → Forward

This page describes COGANT's v0.6 roundtrip contract. The important change is
terminological and behavioral: **role preservation is no longer called strict
isomorphism**. `cogant roundtrip --json` reports a `roundtrip_status` derived
from an invariant ledger, plus the scalar `role_preservation_score` (`s_role`)
as a weaker similarity signal.

## What Is A Roundtrip?

1. **Forward pass** (program code → GNN): `cogant translate` ingests source
   code, builds a typed program graph, applies 22 translation rules, compiles
   A/B/C/D matrices, and emits a GNN package.
2. **Reverse pass** (GNN → program code): `cogant reverse` parses the GNN
   markdown, plans a Python package structure, and synthesizes runnable code
   with matrix functions and an `AgentRuntime`.
3. **Forward-again** (synthesized code → GNN): the synthesized package is
   re-analyzed and compared against the original bundle.

## Status Taxonomy

| Status | Meaning |
| --- | --- |
| `STRUCTURALLY_ISOMORPHIC` | The strict tier: node/edge counts, edge kinds, role preservation, state-space shapes, matrix shapes/values, GNN sections, and generated-code compile checks all pass. |
| `ROLE_PRESERVED` | The original Active Inference role population is preserved above the configured threshold, but at least one stricter structural, matrix, or generated-code invariant drifts. |
| `DRIFT` | The roundtrip completed, but role preservation is below threshold or non-fatal invariants diverge. |
| `FAILED` | The generated code, import/compile check, or re-forward run failed. |

The role-preservation score is:

```text
s_role =
    sum(min(count_original[role], count_resynthesized[role]) for role in roles)
    / max(sum(count_original.values()), sum(count_resynthesized.values()))
```

The default role-preserved threshold is `s_role >= 0.5`. This is a useful
semantic regression signal, but it is intentionally weaker than strict graph
isomorphism, matrix equality, or textual code recovery. Historical evaluation
notes sometimes call out a stricter high-confidence `0.8` line; that is not
the public CLI default.

## JSON Contract

`cogant roundtrip ./my_repo --json` returns fields such as:

```json
{
  "schema_version": "2.0",
  "roundtrip_status": "ROLE_PRESERVED",
  "role_preservation_score": 1.0,
  "role_preserved": true,
  "structurally_isomorphic": false,
  "matrix_preserved": false,
  "gnn_sections_preserved": true,
  "generated_code_ok": true,
  "invariants": {
    "role_preserved": true,
    "graph_node_edge_preserved": false,
    "edge_kinds_preserved": true,
    "matrix_preserved": false,
    "gnn_sections_preserved": true,
    "generated_code_ok": true
  }
}
```

The old `is_isomorphic` and `role_match_score` constructor aliases are accepted
inside Python for compatibility, but new CLI/server JSON emits the v0.6 field
names above.

## Interpreting Drift

Synthesized packages commonly contain scaffolding absent from the original
source: constructors, getters, policy functions, constraint checks, or matrix helper
functions. Those extra nodes can preserve the role distribution while changing
node/edge totals. That is why `ROLE_PRESERVED` is a real success tier but not the
same claim as `STRUCTURALLY_ISOMORPHIC`.

The inspection dashboard and batch dashboard expose the same distinction:
original vs regenerated graph counts, edge-kind deltas, role deltas, GNN-section
diffs, matrix deltas, generated-code status, and the final status badge.

## Further Reading

- [ROUNDTRIP_EVAL.md](../evaluation/ROUNDTRIP_EVAL.md) records the historical
  role-preservation corpus.
- [ROUNDTRIP_IMPROVEMENT.md](../evaluation/ROUNDTRIP_IMPROVEMENT.md) explains
  the policy/context/constraint synthesizer improvements that made the role
  corpus stable.
- [`cogant.reverse` API](../api/reverse.md) documents the reverse synthesizer.
- [GNN format reference](gnn_format.md) describes the GNN sections checked by
  `gnn_sections_preserved`.
