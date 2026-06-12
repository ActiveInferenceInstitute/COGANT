# Mutation Testing Report

Date: 2026-04-09
Target: COGANT core algorithmic modules
Branch: `main` (cogant subrepo, worktree `charming-kalam`)

## Tool

- **Attempted**: `mutmut` 3.5.0 (installed via `uv add --dev mutmut`).
- **Outcome**: mutmut generated 403 mutants for `py/cogant/gnn/matrices.py`
  but reported every mutant as "no tests" in `mutmut results`. This is the
  mutmut-v3 stats-collection failure mode: the parent test runner never
  associated any test with mutated source lines (the v3 trampoline
  instrumentation requires tests to import the mutated file through
  `mutants/<path>` and our test runner does not).
- **Fallback**: Manual mutation testing. For each target mutation, the
  mutation was applied, the relevant `pytest` subset was run, and the
  mutation was reverted immediately. This is strictly more informative
  than a mutmut run that reports "no tests" for every mutant, because we
  actually observe whether the test *suite* catches each change.

## Summary

| Mutation # | File | Change | Result |
|---|---|---|---|
| M1 | `gnn/matrices.py` | `_normalize_row`: `v / total` → `v * total` | KILLED (B column sum test) |
| M2 | `gnn/matrices.py` | `_DEFAULT_DIRECT_MASS` ↔ `_DEFAULT_INDIRECT_MASS` | KILLED (A concentrates mass test) |
| M3 | `gnn/matrices.py` | `compute_C`: `total += sign * ...` → `total -= sign * ...` | KILLED (C reflects constraint test) |
| **M4** | **`gnn/matrices.py`** | **`compute_C`: `label.startswith(("avoid","reject","!"))` → never match** | **SURVIVED** |
| M5 | `gnn/matrices.py` | `compute_B`: `B[nxt][cur][k]` → `B[cur][nxt][k]` (swap axes) | KILLED (B column sum + concentration) |
| M6 | `translate/engine.py` | `translate`: `range(1, max_iterations+1)` → `range(1, 2)` (single pass) | **SURVIVED** (secondary finding — no convergence test) |
| M7 | `translate/engine.py` | `_resolve_conflicts`: `if key_a >= key_b` → `if key_a < key_b` | KILLED (priority test + ai_role_validation) |
| **M8** | **`markov/blanket.py`** | **`partition_by_seeds`: swap SENSORY ↔ ACTIVE for boundary nodes** | **SURVIVED** |
| **M9** | **`statespace/compiler.py`** | **`_map_confidence`: all `>=` → `>` (boundary flip)** | **SURVIVED** |
| M10 | `static/dataflow.py` | `edge_type="mutates"` → `edge_type="reads"` (all sites) | KILLED (3 dataflow tests) |
| M11 | `markov/blanket.py` | `if not (ext_in or ext_out)` → `if not (ext_in and ext_out)` | KILLED (only 1 test: `test_auto_on_two_module_graph`) |
| **M12** | **`gnn/matrices.py`** | **`compute_D`: CONFIGURATION neighbor `bias += 2.0` → `bias += 0.0`** | **SURVIVED** |
| M13 | `gnn/matrices.py` | `compute_A`: `if n_direct == 0:` → `if n_direct > 0:` (flip fallback) | KILLED (concentrates mass test) |
| M14 | `statespace/compiler.py` | `_map_confidence`: every branch returns DEFINITE | KILLED (`test_map_confidence_tiers`) |
| M15 | `translate/engine.py` | `get_coverage_report`: `total` → `(total + 1)` in denominator | Killed **only** by integration test; unit test with `0 < pct <= 100` misses it |

**Score:** 10 killed / 5 survived / 15 total → **mutation score 66.7%**

(mutmut's 403 auto-generated mutants on `matrices.py` are not included here
because mutmut could not run them; the 15 above are hand-picked to target
the algorithmic core rather than boilerplate like type-hint swaps.)

## Surviving mutants — action required

### 1. `gnn/matrices.py` — `compute_C` aversive preference path (M4)

Lines 391–394 handle the PREFERENCE mapping case with `label.startswith(("avoid", "reject", "!"))`
flipping `sign` to `-1.0`. Replacing the tuple with garbage strings (so
the check never matches) leaves every fixture-suite test green. The
existing `test_C_reflects_constraint_on_o0` only covers the CONSTRAINT
branch where `sign` is always `+1.0`.

**Recommended test (added in `test_gnn_matrices_mutation_hardening.py`):**
build a `GNNMatrices` fixture whose observation `o_avoid` has a
PREFERENCE mapping with `semantic_label="avoid_crash"`, then assert
`C[o_avoid] < 0.0`. This kills any mutation that drops or weakens the
aversive-label check.

### 2. `markov/blanket.py` — sensory↔active boundary role (M8)

Lines 212–219: a boundary node with only outgoing edges to external
states is ACTIVE; with only incoming edges it is SENSORY. Swapping the
two role assignments (while keeping the rationale strings unchanged in
content) leaves all 25 `test_markov.py` tests green. The existing tests
check that `sensory_ids | active_ids = boundary_ids`, that counts add
up, and that `auto` strategy picks some non-empty boundary — but they
never assert that a node which writes to the external world is in
`active_ids` (and not in `sensory_ids`), nor vice-versa.

**Recommended test:** build a 2-node graph `{inner → external}` where
`inner` ∈ seeds, and assert `inner` ∈ `active_ids` and `inner` ∉
`sensory_ids`. Repeat for the reversed edge. This is a 6-line test
that kills any mutation flipping the role assignment.

### 3. `statespace/compiler.py` — `_map_confidence` boundary values (M9)

Lines 980–989 use `>=` for the tier cutoffs (0.95, 0.80, 0.60, 0.40).
Changing every `>=` to `>` leaves the existing `test_map_confidence_tiers`
green because that test only exercises 1.0, 0.85, 0.65, 0.45, 0.1 — all
strictly inside a tier. The boundary values are the exact inputs a
principled contract would pin down.

**Recommended test (added):** assert `_map_confidence(0.95) is
ConfidenceLevel.DEFINITE`, `_map_confidence(0.80) is HIGH`,
`_map_confidence(0.60) is MEDIUM`, `_map_confidence(0.40) is LOW`. Four
exact-boundary assertions kill the `>=` → `>` mutation family entirely.

### 4. `gnn/matrices.py` — `compute_D` CONFIGURATION bias (M12)

Lines 430–443 walk `variables` and add `+2.0` bias to the prior for any
variable whose graph node has a `CONFIGURATION` neighbour. Zeroing
that `+2.0` leaves all 21 matrix tests green because no fixture
attaches a `CONFIGURATION` node to a state variable. The only D-vector
tests check shape, sum-to-one, and non-negativity — none of which
constrain relative magnitude.

**Recommended test (optional):** extend the fixture with a
`CONFIGURATION`-typed node linked to `s0`, then assert
`D[0] > D[1]` and `D[0] > D[2]`. This kills mutations to the
configuration-bias constant.

### 5. `translate/engine.py` — fixpoint iteration count (M6, *secondary*)

Forcing `range(1, 2)` (i.e. exactly one pass, never converging beyond
the first iteration) leaves every translation test green. This means
no test constructs a graph whose mappings require more than one
fixpoint pass to appear. This is not a correctness bug (the engine
converges in one pass for all current fixtures) but it means the
convergence machinery is effectively untested — if a rule starts
depending on another rule's output, we won't notice.

**Recommended test (optional, left as follow-up):** create a rule
pair where rule B only matches nodes that rule A has already tagged,
and assert that running with `max_iterations=1` produces fewer
mappings than `max_iterations=10`. This is a behavioural contract for
fixpoint, not a simple invariant.

### 6. `translate/engine.py` — coverage_percent arithmetic (M15, *secondary*)

The unit test `test_coverage_report_on_real_graph` only asserts
`0.0 < report["coverage_percent"] <= 100.0`. An off-by-one in the
denominator (`total + 1`) is *only* caught by the integration test
that pins `coverage_percent == pytest.approx(33.33, abs=0.01)`.

**Recommended unit-test strengthening (optional):** change the unit
assertion to a pinned equality like
`report["coverage_percent"] == pytest.approx(100.0 * covered / total)`
so the arithmetic is locally tested without depending on the slow
integration path.

## Modules with strong test coverage (mutation score on sampled mutants)

- **`static/dataflow.py`**: 3/3 mutants killed. The dataflow tests
  assert on specific `(source, target, edge_type)` tuples rather than
  just edge counts, so any change to edge_type strings is caught.
- **`translate/engine.py` conflict resolution**: 1/1 killed. The
  `test_priority_wins_over_lower_priority` and `test_confidence_wins_on_equal_priority`
  tests directly exercise the comparator.
- **`gnn/matrices.py` column normalisation**: 4/5 killed. The
  `A_columns_sum_to_one`, `B_columns_sum_to_one_per_action`, and
  `A_concentrates_mass_on_direct_reads` tests are good — every
  arithmetic mutation to normalisation is caught. The only miss in
  this file is the PREFERENCE-label sign flip (M4) and the D-vector
  CONFIGURATION bias (M12), both of which simply aren't exercised by
  any fixture.

## Modules needing test hardening (mutation score < 60% on sampled mutants)

- **`markov/blanket.py`**: 1/2 killed (M8 survived, M11 killed but
  only by a single test). The tests verify partition *structure* (sets
  are disjoint, counts add up, union equals all nodes) but not
  *semantic direction*. Recommendation: add a "direction → role"
  assertion as described above.
- **`statespace/compiler.py` boundary thresholds**: 0/1 killed for the
  boundary-value mutation (M9). Recommendation: add the four
  exact-boundary assertions in `test_map_confidence_tiers`.
- **`gnn/matrices.py` D vector biases**: 0/1 killed (M12). D-vector
  tests only assert shape/sum/non-negativity, never relative magnitude.

## Hardening tests added (this commit)

See `tests/unit/test_gnn_matrices_mutation_hardening.py`:

1. `test_C_aversive_preference_produces_negative_log_pref`
   — kills M4 (PREFERENCE aversive label path).
2. `test_boundary_with_only_outgoing_edge_is_active`
   and `test_boundary_with_only_incoming_edge_is_sensory`
   — kill M8 (SENSORY ↔ ACTIVE swap). Live in
   `tests/unit/test_markov_mutation_hardening.py`.
3. `test_map_confidence_exact_boundary_values`
   — kills M9 (boundary `>=` family). Lives in
   `tests/unit/test_statespace_compiler_mutation_hardening.py`.

The D-vector CONFIGURATION-bias mutation (M12) and the fixpoint
iteration-count mutation (M6) are documented but not covered by new
tests in this commit; they require non-trivial fixture changes and are
left as follow-ups.

---

## See also

- **Calibration registry (boundary thresholds):** [CALIBRATION.md](CALIBRATION.md)
- **Active Inference mapping:** [ACTIVE_INFERENCE_MAPPING.md](ACTIVE_INFERENCE_MAPPING.md)
- **v1.0 readiness:** [V1.0_READINESS.md](V1.0_READINESS.md)
- **Mutation regression test suite:**
  [`tests/unit/test_mutation_regressions_engine_matrices_statespace.py`](https://github.com/docxology/cogant/blob/main/tests/unit/test_mutation_regressions_engine_matrices_statespace.py),
  [`tests/unit/test_mutation_hardening.py`](https://github.com/docxology/cogant/blob/main/tests/unit/test_mutation_hardening.py)
- **Implementing modules under test:**
  [`py/cogant/gnn/matrices.py`](https://github.com/docxology/cogant/blob/main/py/cogant/gnn/matrices.py),
  [`py/cogant/markov/blanket.py`](https://github.com/docxology/cogant/blob/main/py/cogant/markov/blanket.py),
  [`py/cogant/statespace/compiler.py`](https://github.com/docxology/cogant/blob/main/py/cogant/statespace/compiler.py),
  [`py/cogant/translate/engine.py`](https://github.com/docxology/cogant/blob/main/py/cogant/translate/engine.py),
  [`py/cogant/static/dataflow.py`](https://github.com/docxology/cogant/blob/main/py/cogant/static/dataflow.py),
  [`py/cogant/reverse/synthesizer.py`](https://github.com/docxology/cogant/blob/main/py/cogant/reverse/synthesizer.py)
