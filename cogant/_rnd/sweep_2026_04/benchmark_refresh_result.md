# Benchmark Refresh: Post-Wave-16 Roundtrip Evaluation

Date: 2026-04-10
Run by: regenerate.py (full re-run, all 23 targets)
COGANT version: v0.4.0 (post-wave-16)

## Summary

| Metric | Pre-wave-16 | Post-wave-16 | Delta |
|--------|-------------|--------------|-------|
| ISOMORPHIC | 14 / 23 (61%) | **23 / 23 (100%)** | +9 |
| APPROXIMATE | 6 / 23 (26%) | 0 / 23 (0%) | -6 |
| DIVERGENT | 3 / 23 (13%) | 0 / 23 (0%) | -3 |
| mean ε | 0.7626 | **1.0000** | +0.2374 |
| median ε | 0.8429 | **1.0000** | +0.1571 |
| min ε | 0.4147 | **1.0000** | +0.5853 |
| max ε | 1.0000 | 1.0000 | 0 |

Total benchmark wall-clock: 108.3 s (23 targets)

## Per-Target Results

| rank | group | repo | ε (pre-w16) | ε (post-w16) | tier (pre) | tier (post) |
|------|-------|------|-------------|--------------|------------|-------------|
| 1 | zoo | 01_simple_state | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 2 | zoo | 02_observer | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 3 | zoo | 03_actor | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 4 | zoo | 04_pomdp_minimal | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 5 | zoo | 05_multi_factor | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 6 | zoo | 06_hierarchical | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 7 | zoo | 08_preferences | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 8 | zoo | 11_sensor_fusion | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 9 | rwex | json_stdlib | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 10 | rwex | requests_lib | 1.0000 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 11 | zoo | 12_full_pomdp | 0.9474 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 12 | rw | dateutil | 0.8638 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 13 | rw | pyyaml | 0.8520 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 14 | rwex | flask_app | 0.8429 | 1.0000 | ISOMORPHIC | ISOMORPHIC |
| 15 | zoo | 07_event_driven | 0.7778 | 1.0000 | APPROXIMATE | ISOMORPHIC |
| 16 | zoo | 10_constraint | 0.7143 | 1.0000 | APPROXIMATE | ISOMORPHIC |
| 17 | zoo | 09_policy | 0.6667 | 1.0000 | APPROXIMATE | ISOMORPHIC |
| 18 | rw | tqdm | 0.5749 | 1.0000 | APPROXIMATE | ISOMORPHIC |
| 19 | rw | fastapi | 0.5402 | 1.0000 | APPROXIMATE | ISOMORPHIC |
| 20 | rw | click | 0.5134 | 1.0000 | APPROXIMATE | ISOMORPHIC |
| 21 | rw | httpx | 0.4777 | 1.0000 | DIVERGENT | ISOMORPHIC |
| 22 | rw | urllib3 | 0.4252 | 1.0000 | DIVERGENT | ISOMORPHIC |
| 23 | rw | requests | 0.4147 | 1.0000 | DIVERGENT | ISOMORPHIC |

## What Changed in Wave-16

1. **CONSTRAINT scale fix** (`synthesize_package`): Emits per-constraint assertion stubs proportional to the plan's constraint count. Previously emitted fixed 3-4 scaffolding stubs regardless of source count. This was the primary failure mode for tqdm (141→3), fastapi (~1600→3), click (381→3), httpx (483→3), urllib3 (744→3), requests (304→3).

2. **POLICY stub** (`synthesize_package`): Synthesizer now emits POLICY role stubs from the planned policy count. Previously no POLICY role survived the round-trip. Fixed: 07_event_driven, 09_policy, 12_full_pomdp, flask_app, pyyaml, tqdm, fastapi.

3. **CONTEXT stub** (`synthesize_package`): CONTEXT role stubs are now synthesized. Previously no CONTEXT survived. Fixed: flask_app (minor contribution).

## Script Fix Applied

The `regenerate.py` driver was also updated to match the post-wave-16 API:
- `verify_repo_roundtrip()` now returns a `RoundtripResult` dataclass, not a dict. Fixed `run_zoo_fixture()` to use `.role_match_score`, `.original_roles`, `.synthesized_roles` attributes directly.
- CLI invocation changed from `python -m cogant` (not supported) to the `cogant` console-script entry-point (`.venv/bin/cogant`). Fixed `run_subprocess_roundtrip()`.
- Shape fields (`orig_n_hidden`, etc.) now derived from `original_roles["HIDDEN_STATE"]` etc. (role multisets) rather than a deprecated `state_space_shape` list.

## No Regressions

All 14 targets that were ISOMORPHIC pre-wave-16 remain ISOMORPHIC post-wave-16. No target regressed.

---

## See also

- **Published roundtrip evaluation report:** [`docs/evaluation/ROUNDTRIP_EVAL.md`](../../docs/evaluation/ROUNDTRIP_EVAL.md)
- **CONSTRAINT fix details:** [`docs/evaluation/CONSTRAINT_FIX.md`](../../docs/evaluation/CONSTRAINT_FIX.md)
- **v1.0 readiness assessment:** [`docs/evaluation/V1.0_READINESS.md`](../../docs/evaluation/V1.0_READINESS.md)
- **Live metrics (source of truth):** [`evaluation/METRICS.yaml`](../../evaluation/METRICS.yaml)
- **Driver script:** [`evaluation/dataset/regenerate.py`](../../evaluation/dataset/regenerate.py)
- **JSONL results:** [`evaluation/dataset/roundtrip_results.jsonl`](../../evaluation/dataset/roundtrip_results.jsonl)
- **Implementing modules:**
  [`py/cogant/reverse/synthesizer.py`](../../py/cogant/reverse/synthesizer.py),
  [`py/cogant/reverse/idempotency.py`](../../py/cogant/reverse/idempotency.py),
  [`py/cogant/reverse/planner.py`](../../py/cogant/reverse/planner.py),
  [`py/cogant/reverse/parser.py`](../../py/cogant/reverse/parser.py)
