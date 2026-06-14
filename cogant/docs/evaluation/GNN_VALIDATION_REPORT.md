# GNN Spec Validation Report
Date: 2026-06-12

## Upstream Validator

**Installed as a git-pinned dependency.** COGANT depends on the Active Inference Institute's `generalized-notation-notation` repository through a pinned git revision in `cogant/pyproject.toml` and `uv.lock`. The current pinned release bundle is v2.0.0, whose Python package exposes a v2.0.0.0 GNN engine.

**Bridge boundary:** COGANT callers must use `cogant.gnn.upstream_bridge`, not raw `import src.gnn`. The upstream v2.0.0 package is installed as a top-level `src` package but still imports siblings as `gnn.*`; the bridge activates the installed `src/` tree before importing upstream modules and before launching upstream subprocess steps.

**Reference implementation used:** COGANT's own `GNNValidator` in `py/cogant/gnn/validator.py`, cross-referenced against:
- Upstream spec: `doc/gnn/reference/gnn_syntax.md` v2.0.0.0 engine / v2.0.0 bundle
- Upstream type-checker logic: `src/type_checker/checker.py`
- Canonical example files: `input/gnn_files/discrete/two_state_bistable.md`, `actinf_pomdp_agent.md`, `simple_mdp.md`

## Spec Source

- Primary: https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation/blob/main/doc/gnn/gnn_syntax.md
- Type-checker: https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation/blob/main/src/type_checker/checker.py
- Examples: https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation/tree/main/input/gnn_files/discrete/

## Compliance Check

| Requirement | Status | Notes |
|---|---|---|
| Required upstream sections present (`GNNSection`, `GNNVersionAndFlags`, `ModelName`, `StateSpaceBlock`, `Connections`, `InitialParameterization`, `Equations`, `Time`, `ActInfOntologyAnnotation`, `ModelParameters`, `Footer`, `Signature`) | PASS | All required v2.0.0.0-engine sections present and in canonical order |
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

Test file: `tests/unit/test_gnn_spec_compliance.py` covers:

- `TestTimeSection` (3 tests): Dynamic time uses `Discrete` + `Time=t`, not `DiscreteTime=t`; static time emits `Static`
- `TestConnectionSyntax` (2 tests): No parenthesised single-variable nodes in upstream Connections section
- `TestNoDuplicateConnectionsHeader` (2 tests): Exactly one `## Connections`, COGANT extended uses `## Program Graph Connections`
- `TestUpstreamSectionOrder`: all required upstream sections present and in canonical order
- `TestStateSpaceBlockSyntax` (2 tests): Variable declarations match upstream regex and include `type=` annotation
- `TestValidatorSpec` (2 tests): Validator detects correct time format; CANONICAL_SECTIONS updated for renamed section

Additional negative controls live in `tests/unit/test_gnn_upstream_bridge.py`,
`tests/unit/test_upstream_pipeline_resolution.py`, and
`tests/unit/test_gnn_validator_reports.py`: they distinguish raw upstream import
failure from bridge success, lock the active-interpreter subprocess contract, and
make the v2.0.0.0-only tail sections (`Equations`, `ModelParameters`, `Footer`,
`Signature`) non-optional.

## Audit Surface And Visualization

The structural validator is not the only evidence surface. The project-root
helper `tools/gnn_v2_audit_surface.py` consumes an exhaustive audit directory
and writes JSON, Markdown, and SVG outputs that keep four claims separate:

- pinned upstream version and bridge currentness;
- COGANT-owned package, validator, formatter, reverse, roundtrip, runner, CLI,
  and pipeline method health;
- selected upstream all-step execution status;
- dependency and supply-chain scan status.

Use it after an audit run:

```bash
uv run python tools/gnn_v2_audit_surface.py \
  --audit-dir /tmp/cogant_gnn_v2_audit \
  --output-dir /tmp/cogant_gnn_v2_audit/published_surface
```

Use `--strict-upstream` when the all-step upstream pipeline is a release gate.
That mode deliberately fails on selected upstream-step failures even though
normal COGANT product paths keep those failures advisory and preserve the
validated package. The companion page
[GNN v2 audit surface](GNN_V2_AUDIT_SURFACE.md) explains how to read the SVG.

## Remaining Open Issues

1. **Raw upstream import remains layout-sensitive.** Direct `import src.gnn` can fail before COGANT's bridge adjusts `sys.path` for upstream's repo-style imports. This is intentional containment: COGANT code must call the `upstream_*` facade functions rather than importing upstream modules directly.

2. **Upstream executable render/execute is stricter than structural validation.** A COGANT package can pass COGANT validation plus upstream parse/type-check/export while upstream framework code generation still reports missing executable POMDP metadata. That failure is an interop target, not proof that the COGANT package validator is wrong; nevertheless, docs must not convert a green validator score into an all-step execution claim.

3. **Variable naming diverges from canonical upstream examples.** Upstream simple models use flat names (`s`, `o`, `A`, `B`). COGANT uses factor-indexed names (`s_f0`, `o_m0`, `A_m0`, `B_f0`). This is valid per the spec (alphanumeric + underscore allowed) and is intentional for multi-factor support. No change needed, but it may cause semantic mismatch warnings if the upstream type-checker expects single-letter names in `ActInfOntologyAnnotation`.

4. **`InitialParameterization` uses `identity()` function syntax for B.** COGANT emits `B_f0=identity(10,10,1)` as a symbolic shorthand. The upstream examples often use explicit brace-delimited matrix notation. The upstream type-checker currently accepts assignment syntax without deep matrix expansion, but stricter future validators may require explicit tensor payloads.
