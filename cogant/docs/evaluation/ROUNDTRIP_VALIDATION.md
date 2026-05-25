# Round-Trip Validation Report

**Date:** 2026-04-09 (historical protocol), refreshed for v0.6 terminology
**Status:** Superseded by `ROUNDTRIP_EVAL.md` and `evaluation/METRICS.yaml`
**Related:** `ROUNDTRIP_EVAL.md`, `docs/theory/roundtrip.md`, `SCOPING_REPORT.md`

---

## 1. Purpose

This document records the original validation protocol for testing whether semantic roles survive a forward-reverse-forward loop. It is retained as a historical design note; current results and the public schema live in `ROUNDTRIP_EVAL.md`, `docs/theory/roundtrip.md`, and `evaluation/METRICS.yaml`.

The historical theorem stated that for any program graph G:

> |R_dist(G) - R_dist(R(F(G)))| ≤ ε(G)

where F is the COGANT forward pass (`cogant.translate`), R is the COGANT reverse pass (`cogant.reverse`), R_dist is the role distribution vector, and ε(G) is the count of ambiguous nodes. The current implementation exposes the higher-is-better `role_preservation_score` (`s_role`) and a `roundtrip_status` enum instead of treating this as strict graph isomorphism.

---

## 2. Protocol

### Step 1: Select test corpora

Three control-positive repositories of known structure are used:

| Corpus | Description | Expected |V|| Expected roles |
|---|---|---|---|
| `calculator` | Simple arithmetic pipeline | 8–12 | clear HIDDEN_STATE, OBSERVATION |
| `event_pipeline` | Event bus with producers/consumers | 15–25 | clear ACTION, POLICY |
| `flask_mini` | Minimal Flask web app | 20–40 | mixed roles, some ambiguity |

One hand-crafted minimal GNN is used as a synthetic baseline (3 hidden states, 2 observations, 2 actions).

### Step 2: Forward pass

For each test repo i, run:

```bash
python -m cogant.translate --repo repos/calculator/ --output /tmp/cogant-rt-calculator/gnn.json
```

Extract role distribution from the output:

```python
R_dist_original = {
    "HIDDEN_STATE": gnn["num_hidden_states"],
    "OBSERVATION": gnn["num_observations"],
    "ACTION": len(gnn["action_names"]),
    "POLICY": count_role(gnn, "POLICY"),
    "CONSTRAINT": count_role(gnn, "CONSTRAINT"),
}
```

### Step 3: Reverse pass

For each GNN output from Step 2, run:

```bash
python -m cogant.reverse --gnn /tmp/cogant-rt-calculator/gnn.json --output /tmp/cogant-roundtrip-calculator/
```

This synthesizes a Python package at `/tmp/cogant-roundtrip-{i}/`.

### Step 4: Forward pass on synthesized code

Run the forward pass on the synthesized code:

```bash
python -m cogant.translate --repo /tmp/cogant-roundtrip-calculator/ --output /tmp/cogant-rt-calculator/gnn_prime.json
```

Extract role distribution R_dist_roundtrip from `gnn_prime.json`.

### Step 5: Compute role preservation

```python
def role_preservation_score(dist1, dist2):
    """Intersection-over-max similarity for role distribution vectors."""
    intersection = sum(min(dist1[r], dist2[r]) for r in ROLES)
    max_total = max(sum(dist1.values()), sum(dist2.values()))
    return intersection / max_total if max_total > 0 else 1.0
```

### Step 6: Compute matrix_distance

```python
import numpy as np

def matrix_distance(gnn1, gnn2):
    """Frobenius norm of A-matrix difference + L2 norm of D-vector difference."""
    A1 = np.array(gnn1["A_matrix"])
    A2 = np.array(gnn2["A_matrix"])
    D1 = np.array(gnn1["D_vector"])
    D2 = np.array(gnn2["D_vector"])
    # Pad to same size if dimensions differ
    A1, A2 = pad_to_same(A1, A2)
    D1, D2 = pad_to_same(D1, D2)
    return np.linalg.norm(A1 - A2, 'fro') + np.linalg.norm(D1 - D2)
```

Note: if A-matrix dimensions differ (|S| or |O| changed), padding with zeros before computing distance ensures a well-defined metric that captures both dimension and value differences.

### Step 7: Classify

| Condition | Current classification |
|---|---|
| `role_preservation_score >= 0.5` | ROLE_PRESERVED |
| `role_preservation_score < 0.5` | DRIFT |
| Generated-code, import, or re-forward failure | FAILED |

Strict `STRUCTURALLY_ISOMORPHIC` status is a separate v0.6 invariant-ledger result:
it additionally requires node/edge deltas, edge-kind deltas, GNN section diffs,
matrix shape/value deltas, and generated-code compile/smoke checks to pass.

---

## 3. Results

This protocol page no longer carries hand-maintained result cells. Current,
machine-readable results live in `evaluation/METRICS.yaml` and are summarized
in `ROUNDTRIP_EVAL.md`. The current public contract reports:

| Metric | Current source |
|---|---|
| Role-preserved target count | `evaluation.roundtrip.role_preserved_count` |
| Strict structural-isomorphism count | `evaluation.roundtrip.strict_isomorphism_count` |
| Drift / failed counts | `evaluation.roundtrip.drift_count`, `evaluation.roundtrip.failed_count` |
| Per-target invariant ledger | each generated `roundtrip/metrics.json` |

Expected outcome (from the historical theorem): well-structured role assignments
should land in the `ROLE_PRESERVED` tier (`s_role >= 0.5`). Strict
`STRUCTURALLY_ISOMORPHIC` status is intentionally narrower and requires the
full v0.6 invariant ledger.

---

## 4. Known Loss Cases

The following four loss case categories are documented in `ISOMORPHISM_THEOREM.md` §6. This section records their expected empirical impact.

### Loss Case 1: Name-Only Keyword Rules

**Description:** A node was assigned its role solely because its name contained a triggering keyword (e.g., "dispatch" → ACTION, "observe" → OBSERVATION).

**Expected behavior in round-trip:** The synthesized code uses R's naming templates, which incorporate the original role-token. For example, an ACTION node named "dispatch_event" is synthesized as "act_dispatch_event" (prefix + original stem). The keyword "dispatch" is still present. The keyword rule fires on the synthesized code and assigns ACTION again.

**Expected role_match impact:** None (role preserved). Possible matrix_dist impact: small (if the keyword heuristic also affects probability assignment).

**Detection signal:** If role_match drops in a repo where most role assignments are keyword-based, investigate whether R's naming templates are stripping the triggering tokens.

### Loss Case 2: Complex Dataflow Rules

**Description:** A HIDDEN_STATE was assigned because it receives exactly N incoming WRITES edges from other state nodes (an in-degree threshold rule).

**Expected behavior in round-trip:** R generates the correct number of WRITES edges by reading the B-matrix. For each (s', s, a) triple with B[s', s, a] > threshold, R generates a WRITES edge from a to s'. The in-degree of the synthesized hidden-state node matches the original.

**Expected role_match impact:** None (role preserved), assuming the threshold used in F is stable between the two forward-pass invocations.

**Detection signal:** Discrepancy here indicates a threshold parameter mismatch between the F and R configurations. Check `cogant.config.EDGE_THRESHOLD`.

### Loss Case 3: Ambiguous Nodes

**Description:** A node matches multiple role-assignment rules with equal priority score. The original tie-break assigns one role; the synthesized code may break the tie differently if the synthesized structural pattern activates a different subset of the matching rules.

**Expected behavior in round-trip:** If the COGANT rule priority table is deterministic and stable, the same rule wins the tie-break on both the original and synthesized node. Role is preserved. If the priority table has changed between invocations (version drift), roles may differ.

**Expected role-preservation impact:** Contributes directly to the ambiguity estimate. Measure as: fraction of nodes in G with rule-priority ties.

**Detection signal:** High ambiguity combined with low `s_role` indicates version drift in the priority table. Freeze rule table hash in `cogant.config.RULE_TABLE_HASH` and assert it is stable across forward-pass invocations.

### Loss Case 4: Zero-Edge (Isolated) Nodes

**Description:** A function with no incoming or outgoing edges. No structural rule fires. Role is assigned by fallback (default: OBSERVATION).

**Expected behavior in round-trip:** R generates an isolated function (no edges in or out, because A and B matrices have zero entries for this node). Running F on the synthesized code: no structural rule fires, fallback assigns OBSERVATION. Role is preserved.

**Expected role_match impact:** None, provided the fallback role in R's synthesized code matches the fallback role in F. Both use OBSERVATION as default.

**Detection signal:** If isolated-node roles differ between original and round-trip, the fallback rule in F has changed. Check `cogant.config.DEFAULT_ROLE`.

---

## 5. Implications

### 5.1 Validity of GNN Metrics as Quality Proxies

If empirical results confirm ROLE_PRESERVED classification for the calculator and event_pipeline repos (`s_role >= 0.5`), this supports the narrower claim that semantic-role populations survive regeneration. Matrix properties (A sparsity, B rank, D entropy, C variance) still require their own validation before they are used as codebase-quality proxies.

Specifically: a quality score computed from the GNN will rank-order repositories in the same way as a quality score computed from the original program graphs, for all structural properties that depend only on the role distribution and inter-role edge structure.

### 5.2 Bounded Role-Preservation Error

The historical theorem provides a worst-case role-preservation bound. Empirical measurement of ambiguity for real repositories is necessary to determine whether this bound is tight or loose. Strict structural claims require the v0.6 invariant ledger, not the role score alone.

### 5.3 Incremental Analysis Validity

If `s_role` for `flask_mini` (the most complex test corpus) is ROLE_PRESERVED, this supports the practical claim that incremental runs preserve semantic-role populations. It does not by itself prove full functoriality or strict graph composition.

### 5.4 Threshold for Flagging Unreliable Repos

Based on the theorem, we propose the following operational threshold for COGANT users:

- **s_role >= 0.5:** Role preservation clears the public default threshold for inspection and regression tracking.
- **s_role < 0.5:** Treat the roundtrip as drift; inspect the visual diff and invariant ledger.
- **FAILED status:** Treat generated-code or re-forward failures as blockers for downstream model claims.

These thresholds are provisional and will be revised based on empirical data from this validation study.

---

## 6. Running the Validation

```bash
# From the package root
uv sync
uv run pytest tests/unit/test_reverse_cli_commands.py tests/integration/test_roundtrip.py -q
uv run cogant roundtrip examples/control_positive/calculator --output output/calculator/roundtrip --keep-tmp
```

The historical `--update-report` path is retired for this page. Refresh
`evaluation/METRICS.yaml` and generated `roundtrip/metrics.json` artifacts
instead, then regenerate the manuscript variables if those values are cited.

---

*Historical protocol note. Current theory reference: `docs/theory/roundtrip.md`; current metrics source: `evaluation/METRICS.yaml` and generated `roundtrip/metrics.json` artifacts.*
