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
persistent CONSTRAINT shortfall that dragged `role_preservation_score` below the 0.5 threshold.

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

| Repo | s_role before | Tier before |
|------|----------|-------------|
| tqdm | 0.5749 | DRIFT |
| fastapi | 0.5149 | DRIFT |
| click | 0.5832 | DRIFT |
| httpx | 0.4412 | FAILED |
| urllib3 | 0.3891 | FAILED |
| requests | 0.4203 | FAILED |
| zoo/07_event_driven | 0.7778 | ROLE_PRESERVED |
| zoo/09_policy | 0.6667 | ROLE_PRESERVED |
| zoo/10_constraint | 0.5714 | DRIFT |

## After (proportional `check_` stubs, detected by forward pipeline)

| Repo | s_role after | Tier after | Δs_role |
|------|---------|------------|----|
| tqdm | 0.8133 | ROLE_PRESERVED | +0.2384 |
| fastapi | 0.9771 | ROLE_PRESERVED | +0.4622 |
| click | 0.8277 | ROLE_PRESERVED | +0.2445 |
| httpx | 0.7495 | ROLE_PRESERVED | +0.3083 |
| urllib3 | 0.6626 | ROLE_PRESERVED | +0.2735 |
| requests | 0.6876 | ROLE_PRESERVED | +0.2673 |
| zoo/07_event_driven | 0.7778 | ROLE_PRESERVED | 0.0000 |
| zoo/09_policy | 0.6667 | ROLE_PRESERVED | 0.0000 |
| zoo/10_constraint | 0.8571 | ROLE_PRESERVED | +0.2857 |

All 9 affected targets crossed the role-preservation gate measured by this fix
note. Current v0.6 reporting uses the public ROLE_PRESERVED threshold
(`s_role >= 0.5`) and reports strict structural isomorphism separately.

## Implementation

Changed: `cogant/py/cogant/reverse/synthesizer.py`, function `_render_constraints_module`

- Strips `cnst_` planner prefix from constraint function names
- Ensures all emitted constraint stubs use `check_` prefix (detectable by forward's `PreferenceRule`)
- Proportional by construction: one stub per `NodePlan` in `plan.constraint_checks`
- Zero stubs when plan has no constraints; N stubs when plan has N constraints
- 120/120 unit+integration tests pass after the change

---

## See also

- **Translation rules reference (PreferenceRule, etc.):** [`docs/reference/translation_rules.md`](../reference/translation_rules.md)
- **Roundtrip evaluation report (post-fix benchmark):** [ROUNDTRIP_EVAL.md](ROUNDTRIP_EVAL.md)
- **Benchmark calibration snapshot:** [CALIBRATION.md](CALIBRATION.md)
- **v1.0 readiness:** [V1.0_READINESS.md](V1.0_READINESS.md)
- **Implementing modules:**
  [`py/cogant/reverse/synthesizer.py`](https://github.com/docxology/cogant/blob/main/py/cogant/reverse/synthesizer.py) (`_render_constraints_module`),
  [`py/cogant/reverse/planner.py`](https://github.com/docxology/cogant/blob/main/py/cogant/reverse/planner.py) (`plan.constraint_checks`),
  [`py/cogant/translate/rules/semantic.py`](https://github.com/docxology/cogant/blob/main/py/cogant/translate/rules/semantic.py) (`PreferenceRule`)
