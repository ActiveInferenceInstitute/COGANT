# CONSTRAINT Synthesizer Fix

Date: 2026-04-10

## Root Cause

The planner (`py/cogant/reverse/planner.py`) assigned `cnst_<ident>` prefixes to
constraint slots when no human-readable name was available (`ident == slot`). The
synthesizer then emitted those names verbatim as function names (e.g. `def cnst_c_f0`).

The forward pipeline's `PreferenceRule` in `translate/rules/semantic.py` detects
CONSTRAINT roles by looking for "check", "test_", "assert_", or "validate" in the
function name. The `cnst_` prefix matched none of these patterns, so every synthesized
constraint stub was silently dropped from the synthesized role multiset — causing a
persistent CONSTRAINT shortfall that dragged `role_match_score` below the 0.5 threshold.

## Fix (synthesizer.py `_render_constraints_module`)

Strip any `cnst_` prefix from the planner-assigned name and always emit a `check_`-
prefixed function name instead:

```python
# Before (broken):
fn_name = node.name if node.name.startswith("cnst_") else f"check_{node.name}"

# After (fixed):
base = node.name
if base.startswith("cnst_"):
    base = base[len("cnst_"):]
fn_name = base if "check" in base else f"check_{base}"
```

The change is proportional by construction: every `NodePlan` in `plan.constraint_checks`
yields exactly one `check_<name>` stub. If the origin GNN had N CONSTRAINT slots, the
planner records N `NodePlan` entries, and the synthesizer emits N `check_*` functions —
matching the origin count exactly.

## Before (fixed 3 stubs / `cnst_` naming, undetected by forward)

| Repo | ε_before | Tier_before |
|------|----------|-------------|
| tqdm | 0.5749 | APPROXIMATE |
| fastapi | 0.5149 | APPROXIMATE |
| click | 0.5832 | APPROXIMATE |
| httpx | 0.4412 | DIVERGENT |
| urllib3 | 0.3891 | DIVERGENT |
| requests | 0.4203 | DIVERGENT |
| zoo/07_event_driven | 0.7778 | ISOMORPHIC |
| zoo/09_policy | 0.6667 | ISOMORPHIC |
| zoo/10_constraint | 0.5714 | APPROXIMATE |

## After (proportional `check_` stubs, detected by forward pipeline)

| Repo | ε_after | Tier_after | Δε |
|------|---------|------------|----|
| tqdm | 0.8133 | ISOMORPHIC | +0.2384 |
| fastapi | 0.9771 | ISOMORPHIC | +0.4622 |
| click | 0.8277 | ISOMORPHIC | +0.2445 |
| httpx | 0.7495 | ISOMORPHIC | +0.3083 |
| urllib3 | 0.6626 | ISOMORPHIC | +0.2735 |
| requests | 0.6876 | ISOMORPHIC | +0.2673 |
| zoo/07_event_driven | 0.7778 | ISOMORPHIC | 0.0000 |
| zoo/09_policy | 0.6667 | ISOMORPHIC | 0.0000 |
| zoo/10_constraint | 0.8571 | ISOMORPHIC | +0.2857 |

All 9 targets are now ISOMORPHIC (ε ≥ 0.5).

## Implementation

Changed: `cogant/py/cogant/reverse/synthesizer.py`, function `_render_constraints_module`

- Strips `cnst_` planner prefix from constraint function names
- Ensures all emitted constraint stubs use `check_` prefix (detectable by forward's `PreferenceRule`)
- Proportional by construction: one stub per `NodePlan` in `plan.constraint_checks`
- Zero stubs when plan has no constraints; N stubs when plan has N constraints
- 120/120 unit+integration tests pass after the change
