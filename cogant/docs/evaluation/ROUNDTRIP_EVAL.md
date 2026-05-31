# COGANT Roundtrip Evaluation

Generated: 2026-04-10 (historical benchmark), refreshed for v0.6 taxonomy
Tool: `cogant roundtrip`
Threshold convention: s_role >= 0.8 = ROLE_PRESERVED, 0.5 <= s_role < 0.8 = DRIFT, s_role < 0.5 = FAILED

> **Source of truth for headline numbers:** [`evaluation/METRICS.yaml`](https://github.com/docxology/cogant/blob/main/evaluation/METRICS.yaml)
> (auto-generated). Current v0.6 release metrics classify the checked-in 23-row
> JSONL ledger as `STALE_LEGACY`: `role_preserved_count: 0`,
> `stale_legacy_count: 23`, nullable native aggregate scores, and
> `role_preservation_score_source: legacy_without_native_score`. The per-target
> table below is a historical post-wave benchmark, not fresh v0.6 release
> evidence, until the ledger is regenerated with per-row
> `role_preservation_score` and invariant status fields.

**Historical note:** The CONSTRAINT, POLICY, and CONTEXT scaffold changes dramatically
improved reverse-synthesizer role preservation. The table below reflects a historical
full re-run of all 23 targets after those changes, which reported all targets as
role-preserved (`s_role = 1.0000`). Earlier buckets (14 role-preserved, 6 drift,
3 failed) are kept only as release history; neither historical bucket is current
native v0.6 evidence or strict graph-isomorphism evidence.

> **Reproducibility and consistency warning.** The per-target `s_role = 1.0000`
> values in the table below are **not regenerable from any checked-in artifact**
> and are **internally inconsistent with the v0.6 scorer** documented in
> @sec:S01-appendix-roundtrip-epsilon. That scorer is the per-role mean of
> $\min/\max$ multiset similarity, which penalizes hallucinated roles: for row 1
> (`orig 1/1/2` vs `synth 1/7/5`) it would score the OBSERVATION role at
> $1/7 \approx 0.14$ and the ACTION role at $2/5 = 0.40$, **not** 1.0. The
> 1.0000 values were therefore produced by a different (legacy v0.5) procedure
> that did not penalize role-count inflation, and the shipped
> `roundtrip_results.jsonl` carries no `role_preservation_score` column to
> recompute them. Treat this entire table as **unverified release history**, not
> as a measured v0.6 result. The authoritative live figures are the
> `role_preserved_count: 0` / `strict_isomorphism_count: 0` reported by
> `METRICS.yaml`.

## Summary Table

In this historical run, all 23 targets round-tripped without runtime failure. Shape match (n_states, n_obs, n_actions each non-empty on both sides) is TRUE for all 23 targets.

| # | Group | Repo / Fixture | s_role (role_preservation_score) | Classification | Orig n_s / n_o / n_a | Synth n_s / n_o / n_a | Elapsed (s) |
|---|-------|----------------|---------------:|----------------|:--------------------:|:---------------------:|------------:|
|  1 | zoo  | 01_simple_state  | 1.0000 | ROLE_PRESERVED |   1 /    1 /   2 |   1 /    7 /   5 |   0.08 |
|  2 | zoo  | 02_observer      | 1.0000 | ROLE_PRESERVED |   1 /    3 /   1 |   1 /    9 /   4 |   0.08 |
|  3 | zoo  | 03_actor         | 1.0000 | ROLE_PRESERVED |   1 /    1 /   3 |   1 /    7 /   6 |   0.08 |
|  4 | zoo  | 04_pomdp_minimal | 1.0000 | ROLE_PRESERVED |   1 /    3 /   2 |   1 /    9 /   5 |   0.08 |
|  5 | zoo  | 05_multi_factor  | 1.0000 | ROLE_PRESERVED |   1 /    2 /   3 |   1 /    8 /   6 |   0.08 |
|  6 | zoo  | 06_hierarchical  | 1.0000 | ROLE_PRESERVED |   2 /    2 /   4 |   2 /   10 /   9 |   0.08 |
|  7 | zoo  | 08_preferences   | 1.0000 | ROLE_PRESERVED |   1 /    1 /   1 |   1 /    7 /   4 |   0.08 |
|  8 | zoo  | 11_sensor_fusion | 1.0000 | ROLE_PRESERVED |   3 /    3 /   6 |   3 /   14 /  13 |   0.08 |
|  9 | rwex | json_stdlib      | 1.0000 | ROLE_PRESERVED |   3 /    1 /  15 |   3 /   13 /  22 |   0.10 |
| 10 | rwex | requests_lib     | 1.0000 | ROLE_PRESERVED |   9 /   24 /  16 |  11 /   58 /  39 |   0.14 |
| 11 | zoo  | 12_full_pomdp    | 1.0000 | ROLE_PRESERVED |   5 /    4 /   8 |   5 /   22 /  18 |   0.09 |
| 12 | rw   | dateutil         | 1.0000 | ROLE_PRESERVED |  38 /  796 / 172 | 131 / 1198 / 430 |  20.52 |
| 13 | rw   | pyyaml           | 1.0000 | ROLE_PRESERVED |  48 /  173 / 167 |  58 /  352 / 282 |   7.98 |
| 14 | rwex | flask_app        | 1.0000 | ROLE_PRESERVED |  13 /   17 /  25 |  14 /   62 /  57 |   0.36 |
| 15 | zoo  | 07_event_driven  | 1.0000 | ROLE_PRESERVED |   0 /    4 /   3 |   1 /    6 /   7 |   0.23 |
| 16 | zoo  | 10_constraint    | 1.0000 | ROLE_PRESERVED |   1 /    1 /   1 |   1 /    7 /   3 |   0.41 |
| 17 | zoo  | 09_policy        | 1.0000 | ROLE_PRESERVED |   1 /    1 /   3 |   1 /    7 /   7 |   0.24 |
| 18 | rw   | tqdm             | 1.0000 | ROLE_PRESERVED |  33 /   81 /  78 |  40 /  204 / 161 |   3.11 |
| 19 | rw   | fastapi          | 1.0000 | ROLE_PRESERVED |  75 / 1703 / 266 | 101 / 2019 / 511 |  50.29 |
| 20 | rw   | click            | 1.0000 | ROLE_PRESERVED |  54 /  252 /  91 |  55 /  420 / 202 |   4.46 |
| 21 | rw   | httpx            | 1.0000 | ROLE_PRESERVED |  56 /  265 / 136 |  64 /  463 / 262 |   5.67 |
| 22 | rw   | urllib3          | 1.0000 | ROLE_PRESERVED |  77 /  318 / 167 | 100 /  627 / 375 |  12.62 |
| 23 | rw   | requests         | 1.0000 | ROLE_PRESERVED |  26 /  140 /  57 |  30 /  235 / 116 |   1.42 |

**Distribution (historical post-wave-16 run, not fresh v0.6 evidence):**
- ROLE_PRESERVED (s_role >= 0.8): **23 / 23** (100%)
- DRIFT (0.5 <= s_role < 0.8): **0 / 23** (0%)
- FAILED (s_role < 0.5): **0 / 23** (0%)

**Historical summary statistics:** mean s_role = 1.0000, median s_role = 1.0000, min s_role = 1.0000, max s_role = 1.0000. Total benchmark wall-clock: ~108 s.

The historical post-wave-16 run reported 23/23 role-preserved targets. The wave-16 CONSTRAINT fix resolved the primary failure mode (constraint-lossy synthesizer) that had held tqdm, fastapi, click, httpx, urllib3, and requests below threshold. The POLICY/CONTEXT stub additions resolved the remaining partial losses on zoo/07, zoo/09, zoo/10, zoo/12, and flask_app. Regenerate a native v0.6 ledger before using those results as current release evidence.

## Method

**Forward:**
```
cogant scan  →  static analysis  →  program graph  →  translate (GNN)  →  statespace compiler (S, O, A, π)  →  GNN markdown
```

**Reverse:**
```
parse_gnn (reverse.parser)  →  plan_package (reverse.planner)  →  synthesize_package (reverse.synthesizer)  →  synthesized Python package
```

**Forward-again (on the synthesized package):**
Same forward pipeline as above, producing a second GNN.

**Role-preservation computation:**
`cogant.reverse.idempotency.verify_repo_roundtrip(repo_path).role_preservation_score`

Role-match is computed over the multiset of node roles (HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, CONTEXT) — comparing the role populations from the first and second forward passes. The canonical tiered thresholds (from `cogant/evaluation/METRICS.yaml`: `threshold_isomorphic = 0.8`, `threshold_approximate = 0.5`) partition outcomes into ROLE_PRESERVED (`s_role >= 0.8`), DRIFT (`0.5 <= s_role < 0.8`), and FAILED (`s_role < 0.5`). Legacy roundtrip driver code may still report a loose `roundtrip_status` at a 0.5 gate; this report always uses the stricter s_role >= 0.8 tier classification.

In v0.6, `roundtrip_status` is derived from an invariant ledger. The weaker
ROLE_PRESERVED tier means every original semantic role population survives the
forward-reverse-forward loop at the configured threshold. It does **not** mean
the original and regenerated program graphs are structurally isomorphic: strict
structural success additionally requires zero node/edge deltas, preserved edge-kind
counts, matrix shape and value preservation, GNN section preservation, and
generated-code compile/smoke success.

**Command used:**
```
cogant roundtrip <target> --json
```

Driver script: `cogant/evaluation/dataset/regenerate.py`. Output: `cogant/evaluation/dataset/roundtrip_results.jsonl`. The checked-in JSONL currently lacks the native v0.6 row fields needed for fresh role-score aggregation, so `tools/regenerate_metrics.py` treats it as stale legacy evidence.

## Per-Repo Analysis (post-wave-16)

### Zoo fixtures (12)

The historical post-wave-16 run reported all 12 zoo fixtures as s_role = 1.0000 role-preserved.

- **01–06, 08, 11**: Hand-authored to exercise a single Active-Inference primitive. Forward extracts the ground-truth role counts exactly; reverse-synthesized package re-forwards to a superset (extra scaffolding nodes), but role-match over the multiset of *original* roles is fully preserved.
- **07_event_driven** (pre-wave-16: s_role=0.7778, now s_role=1.0): POLICY stub fix in wave-16 resolves the POLICY→absent loss. The synthesizer now emits POLICY role stubs so the re-forwarded package recovers the original POLICY count.
- **09_policy** (pre-wave-16: s_role=0.6667, now s_role=1.0): Same fix — POLICY stubs recovered.
- **10_constraint** (pre-wave-16: s_role=0.7143, now s_role=1.0): CONSTRAINT fix in wave-16 — synthesizer now scales CONSTRAINT emission to match origin count, not fixed scaffolding.
- **12_full_pomdp** (pre-wave-16: s_role=0.9474, now s_role=1.0): POLICY stub recovers the single POLICY that was previously lost.

### Curated real-world examples (3, `examples/real_world/`)

The historical post-wave-16 run reported all 3 curated real-world examples as s_role = 1.0000 role-preserved.

- **json_stdlib**: 3 states, 1 obs, 15 actions in origin; synth preserves all.
- **requests_lib**: 9/24/16 origin; synth preserves multiset and adds scaffolding.
- **flask_app** (pre-wave-16: s_role=0.8429, now s_role=1.0): POLICY + CONTEXT stub fixes recover the roles that were previously dropped.

### Real-world libraries (8, `evaluation/eval_repos/`)

The historical post-wave-16 run reported all 8 eval repos as s_role = 1.0000 role-preserved.

- **dateutil**: Largest OBSERVATION count (796); role-match holds cleanly.
- **pyyaml**: 48 hidden states, 173 obs, 167 actions — all recovered.
- **tqdm** (pre-wave-16: s_role=0.5749 DRIFT, now s_role=1.0): CONSTRAINT scale fix resolved the 141→3 collapse.
- **fastapi** (pre-wave-16: s_role=0.5402 DRIFT, now s_role=1.0): CONSTRAINT/POLICY/CONTEXT stubs all contribute to recovery. Slowest target at ~50s due to 1703 OBSERVATION mappings.
- **click** (pre-wave-16: s_role=0.5134 DRIFT, now s_role=1.0): 54 hidden states, 252 obs, 91 actions recovered.
- **httpx** (pre-wave-16: s_role=0.4777 FAILED, now s_role=1.0): Previously the hardest of the HTTP-client trio; wave-16 CONSTRAINT fix resolved the 483→3 collapse.
- **urllib3** (pre-wave-16: s_role=0.4252 FAILED, now s_role=1.0): 744 CONSTRAINT recovered.
- **requests** (pre-wave-16: s_role=0.4147 FAILED, now s_role=1.0): 304 CONSTRAINT recovered.

## Observations (post-wave-16)

**What wave-16 fixed.** Three synthesizer changes landed in wave-16:
1. **CONSTRAINT scale fix**: `synthesize_package` now emits per-constraint assertion stubs proportional to the plan's constraint count, not fixed scaffolding (3–4). This resolved all six targets that were DRIFT/FAILED due to constraint-heavy origins.
2. **POLICY stub**: The synthesizer now emits POLICY role stubs. Previously all POLICY roles were absent from the re-forwarded GNN; this resolved 07_event_driven, 09_policy, 12_full_pomdp, flask_app, pyyaml, tqdm, fastapi.
3. **CONTEXT stub**: CONTEXT role stubs are now synthesized. Previously no CONTEXT survived the round-trip.

**What was consistent in the historical run.** HIDDEN_STATE, OBSERVATION, and
ACTION role populations were preserved across all 23 targets in this benchmark,
and shape match on (n_states, n_obs, n_actions) was TRUE for all 23 targets.
Regenerate the native v0.6 ledger before treating this as current evidence.

**No regressions in the historical run.** The 14 targets that were already role-preserved pre-wave-16 remained role-preserved, with identical or slightly improved shape counts.

## Best Candidate for the Empirical Claim

For the historical empirical-claim selection, we wanted a target that (a) round-tripped with s_role = 1.0 in that run and (b) was tractable enough to run an Active Inference cycle on, meaning small n_states, n_obs, n_actions so we could enumerate policies and compute expected free energy without scaling tricks.

**Best historical candidate for empirical claim: `zoo/01_simple_state`** (s_role = 1.0000 in the historical run, n_states = 1, n_obs = 1, n_actions = 2)

Runner-ups (also viable):

- `zoo/04_pomdp_minimal` — s_role=1.0, n_states=1, n_obs=3, n_actions=2. Most natural POMDP semantics.
- `zoo/06_hierarchical` — s_role=1.0, n_states=2, n_obs=2, n_actions=4. Two hidden factors exercises hierarchical inference.
- `rwex/json_stdlib` — s_role=1.0, n_states=3, n_obs=1, n_actions=15. Smallest real-world target. Too many actions for fast policy enumeration but usable with sampling.

For a first demonstration of the Active Inference cycle (forward → GNN → policy → free-energy minimization → action → observation → belief update) the historical recommendation is **`zoo/01_simple_state`**: the 1×1×2 POMDP is the smallest non-trivial policy space (two actions), the belief update is a 1D Bayesian update, the expected free energy is analytic, and the historical roundtrip run reported s_role = 1.0 with shape_match true.

## Artifacts

- JSONL results: `cogant/evaluation/dataset/roundtrip_results.jsonl` (23 legacy rows, one per target; current metrics classify them as `STALE_LEGACY`)
- Driver script: `cogant/evaluation/dataset/regenerate.py`
- Benchmark thresholds and calibration constants: [CALIBRATION.md](CALIBRATION.md)

---

## See also

- **Conceptual roundtrip explainer (published docs):** [`docs/concepts/roundtrip.md`](../concepts/roundtrip.md)
- **Wave-16 CONSTRAINT fix details:** [CONSTRAINT_FIX.md](CONSTRAINT_FIX.md)
- **Benchmark calibration snapshot:** [CALIBRATION.md](CALIBRATION.md)
- **v1.0 readiness assessment:** [V1.0_READINESS.md](V1.0_READINESS.md)
- **Live metrics (source of truth):** [`evaluation/METRICS.yaml`](https://github.com/docxology/cogant/blob/main/evaluation/METRICS.yaml)
- **Dataset (HuggingFace/Kaggle layout):** [`evaluation/dataset/`](https://github.com/docxology/cogant/blob/main/evaluation/dataset/)
- **Driver script:** [`evaluation/dataset/regenerate.py`](https://github.com/docxology/cogant/blob/main/evaluation/dataset/regenerate.py)
- **Implementing modules:**
  [`py/cogant/reverse/idempotency.py`](https://github.com/docxology/cogant/blob/main/py/cogant/reverse/idempotency.py) (verify_repo_roundtrip),
  [`py/cogant/reverse/synthesizer.py`](https://github.com/docxology/cogant/blob/main/py/cogant/reverse/synthesizer.py),
  [`py/cogant/reverse/parser.py`](https://github.com/docxology/cogant/blob/main/py/cogant/reverse/parser.py),
  [`py/cogant/reverse/planner.py`](https://github.com/docxology/cogant/blob/main/py/cogant/reverse/planner.py)
