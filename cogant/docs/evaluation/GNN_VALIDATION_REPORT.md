# GNN Spec Validation Report
Date: 2026-04-09

## Upstream Validator

**Not found as a pip-installable package.** No PyPI package named `gnn`, `pyGNN`, or `generalized-notation-notation` exists for the AII GNN spec. The Active Inference Institute's GNN project (`github.com/ActiveInferenceInstitute/GeneralizedNotationNotation`) provides a type-checker as part of its pipeline (`src/type_checker/checker.py`) but does not publish a standalone validator package.

**Reference implementation used:** COGANT's own `GNNValidator` in `py/cogant/gnn/validator.py`, cross-referenced against:
- Upstream spec: `doc/gnn/gnn_syntax.md` v1.1
- Upstream type-checker logic: `src/type_checker/checker.py` (analyzed via WebFetch)
- Canonical example files: `input/gnn_files/discrete/two_state_bistable.md`, `actinf_pomdp_agent.md`, `simple_mdp.md`

## Spec Source

- Primary: https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation/blob/main/doc/gnn/gnn_syntax.md
- Type-checker: https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation/blob/main/src/type_checker/checker.py
- Examples: https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation/tree/main/input/gnn_files/discrete/

## Compliance Check

| Requirement | Status | Notes |
|---|---|---|
| Required upstream sections present (GNNSection, GNNVersionAndFlags, ModelName, StateSpaceBlock, Connections, InitialParameterization, Time, ActInfOntologyAnnotation) | PASS | All 8 present and in canonical order |
| StateSpaceBlock variable syntax: `NAME[dim,dim,...,type=T]` | PASS | Uses `s_f0[10,1,type=int]` format matching upstream regex `(\w+)\s*\[([^\]]+)\]` |
| Variable type annotations | PASS | All declarations include `type=float` or `type=int` |
| Variable naming conventions (factor-indexed `s_fN`, `o_mN`, `u_cN`, `A_mN`, `B_fN`) | PASS | Factor-indexed naming is valid per spec; upstream allows alphanumeric+underscore |
| Connection syntax (bare variable names, no parentheses on single-variable nodes) | FIXED | Was: `(D_f0) > (s_f0)`; Fixed to: `D_f0>s_f0` |
| Time section format (`Discrete` + `Time=t` as separate keywords) | FIXED | Was: `DiscreteTime=t` (fused, not a valid upstream keyword); Fixed to: `Discrete\nTime=t` |
| No duplicate `## Connections` section headers | FIXED | COGANT extended section renamed from `## Connections` to `## Program Graph Connections` |
| A matrix notation (columns sum to 1) | PASS | Validated by `GNNValidator.validate_matrices()` |
| B matrix notation (columns per action slice sum to 1) | PASS | Validated by `GNNValidator.validate_matrices()` |
| C vector (log-preferences, length = n_obs) | PASS | Validated by `GNNValidator.validate_matrices()` |
| D vector (prior, sums to 1, length = n_states) | PASS | Validated by `GNNValidator.validate_matrices()` |
| ActInfOntologyAnnotation variable-to-concept mapping | PASS | Maps `s_fN=HiddenState`, `A_mN=LikelihoodMatrix`, `B_fN=TransitionMatrix`, etc. |
| Markov blanket section present | PASS | COGANT emits a full Markov blanket partition section |
| Provenance section present | PASS | `provenance.json` and markdown provenance section both present |
| Package file set complete | PASS | All 16 required JSON + markdown files generated |
| Checksum verification | PASS | SHA-256 checksums stored in `manifest.json` |
| Static time spec (no transitions) | PASS | Emits `Static` |

## Non-conformances Fixed

### Fix 1: Time Section — `DiscreteTime=t` fused token
**File:** `py/cogant/gnn/formatter/upstream.py`, `_format_time()`

The upstream type-checker (`checker.py`) validates Time section content against a list of known keywords: `Static`, `Dynamic`, `Time=t`, `Discrete`, `ModelTimeHorizon=Unbounded`. The fused form `DiscreteTime=t` is not in this list and would generate a warning. Fixed by splitting into two separate lines: `Discrete` and `Time=t`.

**Before:**
```
## Time
Dynamic
DiscreteTime=t
ModelTimeHorizon=Unbounded
```

**After:**
```
## Time
Dynamic
Discrete
Time=t
ModelTimeHorizon=Unbounded
```

### Fix 2: Connections — Parenthesised single-variable nodes
**File:** `py/cogant/gnn/formatter/upstream.py`, `_format_upstream_connections()`

The upstream type-checker splits connection lines on `>` and `-` to extract source/target variable names. A connection like `(D_f0) > (s_f0)` produces source name `(D_f0)` (including the parenthesis), which the checker flags as "potentially undefined variable: (D_f0". The canonical upstream examples (e.g., `two_state_bistable.md`) use bare variable names: `D>s`, `s-A`.

Fixed by removing parentheses from single-variable endpoints and using bare comma-separated syntax for multi-source tuples (consistent with how upstream examples write multi-source connections like `A,s>o`).

**Before:**
```
(D_f0) > (s_f0)
(A_m0, s_f0) > (o_m0)
G > (u_c0)
```

**After:**
```
D_f0>s_f0
A_m0,s_f0>o_m0
G>u_c0
```

### Fix 3: Duplicate `## Connections` section header
**File:** `py/cogant/gnn/formatter/structural.py`, `_format_connections()`

COGANT generates two markdown sections with the header `## Connections`: the upstream-compatible one (in the upstream header block) and the COGANT extended one (detailed program-graph edge table). The upstream type-checker processes the entire file sequentially; encountering a second `## Connections` block could cause it to parse COGANT's extended table rows as malformed connection syntax.

Fixed by renaming the COGANT extended section to `## Program Graph Connections`. The validator's `CANONICAL_SECTIONS` and `base.py` `SECTION_ORDER` were updated to match.

**Before:** Two `## Connections` sections in the document.
**After:** One `## Connections` (upstream block) + one `## Program Graph Connections` (COGANT extended).

## Tests Added

New test file: `tests/unit/test_gnn_spec_compliance.py` — 13 tests covering:

- `TestTimeSection` (3 tests): Dynamic time uses `Discrete` + `Time=t`, not `DiscreteTime=t`; static time emits `Static`
- `TestConnectionSyntax` (2 tests): No parenthesised single-variable nodes in upstream Connections section
- `TestNoDuplicateConnectionsHeader` (2 tests): Exactly one `## Connections`, COGANT extended uses `## Program Graph Connections`
- `TestUpstreamSectionOrder` (2 tests): All 8 required sections present and in canonical order
- `TestStateSpaceBlockSyntax` (2 tests): Variable declarations match upstream regex and include `type=` annotation
- `TestValidatorSpec` (2 tests): Validator detects correct time format; CANONICAL_SECTIONS updated for renamed section

All 80 GNN-related tests pass (13 new + 67 existing).

## Remaining Open Issues

1. **No upstream pip-installable validator.** The AII GNN project does not publish a standalone Python package. True upstream validation requires cloning the full GeneralizedNotationNotation repo and running `src/5_type_checker.py` locally. This is not currently wired into COGANT's CI.

2. **`html_renderer.py` imports missing `cytoscape_view` module.** This is a pre-existing bug in the working tree (`py/cogant/viz/html_renderer.py` line 8) that breaks integration tests when the `html_renderer` is imported. This is unrelated to GNN spec compliance and is NOT caused by these fixes.

3. **Variable naming diverges from canonical upstream examples.** Upstream simple models use flat names (`s`, `o`, `A`, `B`). COGANT uses factor-indexed names (`s_f0`, `o_m0`, `A_m0`, `B_f0`). This is valid per the spec (alphanumeric + underscore allowed) and is intentional for multi-factor support. No change needed, but it may cause semantic mismatch warnings if the upstream type-checker expects single-letter names in `ActInfOntologyAnnotation`.

4. **`InitialParameterization` uses `identity()` function syntax for B.** COGANT emits `B_f0=identity(10,10,1)` as a symbolic shorthand. The upstream spec examples use explicit brace-delimited matrix notation. The upstream type-checker only counts `=` assignments without deep structural validation, so this passes, but strict future validators may reject the symbolic form.
