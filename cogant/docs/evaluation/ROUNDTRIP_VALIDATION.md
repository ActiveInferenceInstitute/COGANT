# Round-Trip Validation Report

**Date:** 2026-04-09 (template — updated by `test_roundtrip.py` empirically)  
**Status:** Protocol defined; results PENDING  
**Related:** `ISOMORPHISM_THEOREM.md`, `SCOPING_REPORT.md`

---

## 1. Purpose

This document records the validation protocol and empirical results for testing the Role Isomorphism Theorem stated in `ISOMORPHISM_THEOREM.md` §5.

The theorem claims that for any program graph G:

> |R_dist(G) - R_dist(R(F(G)))| ≤ ε(G)

where F is the COGANT forward pass (`cogant.translate`), R is the COGANT reverse pass (`cogant.reverse`), R_dist is the role distribution vector, and ε(G) is the count of ambiguous nodes. This document provides the empirical estimate of ε(G) for control-positive test repositories.

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

### Step 5: Compute role_match

```python
def role_match(dist1, dist2):
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

| role_match | Classification |
|---|---|
| ≥ 0.8 | ISOMORPHIC |
| 0.5 ≤ · < 0.8 | PARTIALLY_ISOMORPHIC |
| < 0.5 | NON_ISOMORPHIC |

---

## 3. Results

*To be populated by `test_roundtrip.py` — run `uv run pytest tests/infra_tests/test_roundtrip.py -v` to generate.*

| Repo | \|V\| | \|E\| | role_match | matrix_dist | ε(G) | status |
|---|---|---|---|---|---|---|
| calculator | ? | ? | PENDING | PENDING | PENDING | PENDING |
| event_pipeline | ? | ? | PENDING | PENDING | PENDING | PENDING |
| flask_mini | ? | ? | PENDING | PENDING | PENDING | PENDING |
| hand-written GNN (3-node) | 3 | 4 | PENDING | PENDING | PENDING | PENDING |

Expected outcome (from theorem): all repos with well-structured role assignments should be ISOMORPHIC (role_match ≥ 0.8). `flask_mini` may be PARTIALLY_ISOMORPHIC due to its higher ambiguity rate.

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

### Loss Case 3: Ambiguous Nodes (Primary Source of ε)

**Description:** A node matches multiple role-assignment rules with equal priority score. The original tie-break assigns one role; the synthesized code may break the tie differently if the synthesized structural pattern activates a different subset of the matching rules.

**Expected behavior in round-trip:** If the COGANT rule priority table is deterministic and stable, the same rule wins the tie-break on both the original and synthesized node. Role is preserved. If the priority table has changed between invocations (version drift), roles may differ.

**Expected role_match impact:** Contributes directly to ε(G). Measure as: fraction of nodes in G with rule-priority ties.

**Detection signal:** High ε(G) combined with low role_match indicates version drift in the priority table. Freeze rule table hash in `cogant.config.RULE_TABLE_HASH` and assert it is stable across forward-pass invocations.

### Loss Case 4: Zero-Edge (Isolated) Nodes

**Description:** A function with no incoming or outgoing edges. No structural rule fires. Role is assigned by fallback (default: OBSERVATION).

**Expected behavior in round-trip:** R generates an isolated function (no edges in or out, because A and B matrices have zero entries for this node). Running F on the synthesized code: no structural rule fires, fallback assigns OBSERVATION. Role is preserved.

**Expected role_match impact:** None, provided the fallback role in R's synthesized code matches the fallback role in F. Both use OBSERVATION as default.

**Detection signal:** If isolated-node roles differ between original and round-trip, the fallback rule in F has changed. Check `cogant.config.DEFAULT_ROLE`.

---

## 5. Implications

### 5.1 Validity of GNN Metrics as Quality Proxies

If empirical results confirm ISOMORPHIC classification for the calculator and event_pipeline repos (role_match ≥ 0.8, ε ≈ 0), this validates the key claim from `ISOMORPHISM_THEOREM.md` §8.1: that GNN matrix properties (A sparsity, B rank, D entropy, C variance) are valid proxy metrics for codebase quality.

Specifically: a quality score computed from the GNN will rank-order repositories in the same way as a quality score computed from the original program graphs, for all structural properties that depend only on the role distribution and inter-role edge structure.

### 5.2 Bounded Error Guarantee

The Role Isomorphism Theorem provides a worst-case bound: error ≤ ε(G). Empirical measurement of ε(G) for real repositories is necessary to determine whether this bound is tight or loose. If ε(G) is consistently small (< 5% of nodes) across diverse repositories, the theorem justifies using COGANT as a reliable structural analyzer without ground-truth comparison.

### 5.3 Incremental Analysis Validity

If role_match for `flask_mini` (the most complex test corpus) is ISOMORPHIC, this supports the functoriality claim from `ISOMORPHISM_THEOREM.md` §8.3: that COGANT can be run incrementally on changed modules without re-analyzing the full repository. The round-trip results provide the empirical evidence that per-module GNNs compose consistently with the full-repository GNN.

### 5.4 Threshold for Flagging Unreliable Repos

Based on the theorem, we propose the following operational threshold for COGANT users:

- **ε(G) < 5%:** Round-trip is reliable. GNN metrics are valid proxies.
- **5% ≤ ε(G) < 15%:** Round-trip is partially reliable. Metrics should be treated as approximate.
- **ε(G) ≥ 15%:** Round-trip is unreliable. The codebase has pervasive role ambiguity; structural refactoring is recommended before using GNN metrics.

These thresholds are provisional and will be revised based on empirical data from this validation study.

---

## 6. Running the Validation

```bash
# Install dependencies
uv sync

# Run round-trip validation suite
uv run pytest tests/infra_tests/test_roundtrip.py -v --tb=short

# Run with output capture (writes results table to this file)
uv run python scripts/run_roundtrip_validation.py --update-report
```

The `--update-report` flag causes `run_roundtrip_validation.py` to overwrite the PENDING entries in section 3 of this document with measured values.

---

*Document maintained in ``. Theory reference: `ISOMORPHISM_THEOREM.md`. Test implementation: `tests/infra_tests/test_roundtrip.py` (to be written). Script: `scripts/run_roundtrip_validation.py` (to be written).*
