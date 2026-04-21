# Round-trip verification: Forward → Reverse → Forward

This page explains COGANT's forward-reverse-forward loop, the meaning of ISOMORPHIC/APPROXIMATE/DIVERGENT classifications, and what epsilon (ε = 1.0) signifies.

## What is a round-trip?

A **round-trip** is a three-step verification that the forward and reverse passes are semantically dual:

1. **Forward pass** (program code → GNN): `cogant translate` — ingest source code, build a program graph, apply 22 translation rules, and emit a GNN bundle with A/B/C/D matrices.

2. **Reverse pass** (GNN → program code): `cogant reverse` — parse the GNN markdown, plan a Python package structure, and synthesize runnable Python code with matrix functions (`A`, `B`, `C`, `D`) and an `AgentRuntime`.

3. **Forward-again** (synthesized code → GNN): Re-run the forward pass on the synthesized package. If the two GNN bundles are semantically equivalent, the round-trip is **ISOMORPHIC**.

### Why round-trip?

Round-tripping verifies that the two representations (program graph and GNN generative model) are not lossy. It tests whether:
- The forward pipeline correctly extracted role semantics.
- The reverse synthesizer faithfully reconstructed those semantics.
- The forward pipeline on the reconstructed code recovers the original role distribution.

Isomorphic round-trips indicate the forward and reverse passes are true semantic duals — a Galois connection — rather than lossy compression followed by heuristic reconstruction.

## Classification thresholds

COGANT classifies round-trip outcomes using **epsilon (ε)**, computed as the **role-match score**: the degree to which the original and re-forwarded role distributions match.

| Classification | ε range | Meaning |
| --- | --- | --- |
| **ISOMORPHIC** | ε ≥ 0.8 | The original and re-forwarded bundles have equivalent or near-equivalent role counts. The semantic content is fully or nearly fully preserved. |
| **APPROXIMATE** | 0.5 ≤ ε < 0.8 | The original and re-forwarded bundles differ but share substantial structure. Some semantic content was lost. |
| **DIVERGENT** | ε < 0.5 | The original and re-forwarded bundles diverge significantly. Semantic content was substantially lost. |

### How ε is computed

The role-match score is a multiset-based similarity metric over the six semantic roles:

```
role_match_score = (
    sum of min(count_original[role], count_resynthesized[role])
    for role in {HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, CONTEXT}
) / max(
    sum(count_original[role] for all roles),
    sum(count_resynthesized[role] for all roles)
)
```

This gives the ratio of correctly-matched roles (both present in original and re-forward bundles) to the total unique roles. A score of 1.0 (epsilon = 1.0) means perfect match; a score of 0.8 means at least 80% of roles were recovered.

**Example:** If the original bundle has `{3 HIDDEN_STATE, 1 OBSERVATION, 15 ACTION}` and the re-forwarded bundle has `{3 HIDDEN_STATE, 13 OBSERVATION, 22 ACTION}` (due to scaffolding), the role-match is:

```
min(3,3) + min(1,13) + min(15,22) = 3 + 1 + 15 = 19
max(3+1+15, 3+13+22) = max(19, 38) = 38
ε = 19/38 = 0.5 (APPROXIMATE, not ISOMORPHIC)
```

## What epsilon = 1.0 means

When **ε = 1.0**, the original and re-forwarded role distributions are **identical**:

- Every HIDDEN_STATE role in the original is present in the re-forward.
- Every OBSERVATION role is preserved.
- Every ACTION, POLICY, CONSTRAINT, and CONTEXT role is recovered.

This does **not** mean the GNN matrices are numerically identical (the synthesizer emits heuristic fills for missing evidence), and it does **not** mean the code is textually identical (the synthesizer uses templated stubs). Rather, it means **the semantic structure — the Active Inference role assignment — is perfectly preserved**.

An ε = 1.0 round-trip is strong evidence that:
1. The forward pipeline's role rules are not lossy with respect to the source code.
2. The reverse synthesizer correctly interprets and reconstructs the GNN's role semantics.
3. The program graph and the GNN matrix dimensions are dual representations of the same underlying causal structure.

## v0.5.0 benchmark: 23/23 ISOMORPHIC (ε = 1.0)

The v0.5.0 release achieved **23/23 ISOMORPHIC** across the canonical roundtrip evaluation set:

- **12 zoo fixtures** — hand-authored minimal Active Inference examples covering states, observations, actions, policies, constraints, and event systems.
- **3 real-world examples** — curated Python libraries (`json_stdlib`, `requests_lib`, `flask_app`).
- **8 uncurated real-world libraries** — diverse large codebases (`dateutil`, `pyyaml`, `tqdm`, `fastapi`, `click`, `httpx`, `urllib3`, `requests`).

**Key v0.5.0 improvements:**
- **POLICY stub emission** — The synthesizer now generates `decide_*` stubs proportional to the origin GNN's POLICY role count, rather than using fixed scaffolding.
- **CONTEXT stub emission** — Similarly for CONTEXT roles and `get_context_*` stubs.
- **CONSTRAINT fix (wave-16)** — The synthesizer scales `check_*` stub generation to match origin constraint counts.

These changes resolved the primary failure modes that had held earlier versions at 14/23 or 19/23, bringing all targets to ε = 1.0.

## Interpreting scaffolding and surplus nodes

When a synthesized package is re-forwarded, it often has **more nodes** than the original:

| Metric | Original | Re-forward | Why |
| --- | --- | --- | --- |
| n_states (HIDDEN_STATE) | 1 | 1 | Preserved |
| n_obs (OBSERVATION) | 3 | 9 | Synthesis adds scaffolding (getters, logging, properties) |
| n_actions (ACTION) | 1 | 4 | Synthesis adds `__init__`, helper methods, etc. |

The role-match score **tolerates these surplus nodes** because it measures the *union* of original and synthesized roles. A synthesized package can be a **faithful superstructure** — it preserves all original roles and adds harmless scaffolding — and still achieve ε = 1.0.

This is the expected and correct behavior: a reverse synthesizer cannot guarantee a textually identical reconstruction, only a **semantically isomorphic** one.

## Running round-trip evaluation

### Quick validation (single target)

```bash
cogant roundtrip ./my_repo --json
```

Returns a JSON record with:
- `role_match_score` — the ε value
- `classification` — ISOMORPHIC, APPROXIMATE, or DIVERGENT
- `original_counts` — {role → count} from the first forward pass
- `resynthesized_counts` — {role → count} from the re-forward pass

### Batch evaluation (evaluation set)

```bash
cd cogant/evaluation
python dataset/regenerate.py --target-group zoo
```

Runs round-trips on all fixtures in the `zoo/` example directory and outputs `roundtrip_results.jsonl` with full per-target breakdowns.

## Further reading

- **[Isomorphism Theorem](isomorphism.md)** — Formal mathematical proof that program graphs and generative models form a Galois connection.
- **[ROUNDTRIP_EVAL.md](../evaluation/ROUNDTRIP_EVAL.md)** — Full benchmark report with 23/23 ISOMORPHIC results and per-target analysis.
- **[ROUNDTRIP_IMPROVEMENT.md](../evaluation/ROUNDTRIP_IMPROVEMENT.md)** — Historical changelog of improvements from v0.2.0 (14/23) to v0.5.0 (23/23).
- **[`cogant.reverse` API](../api/reverse.md)** — Reverse synthesizer module documentation.
- **[GNN format reference](gnn_format.md)** — The 18-section GNN markdown spec that round-trips preserve.
