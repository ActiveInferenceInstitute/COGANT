# GNN Spec Validation Report
Date: 2026-06-12 (upstream contract updated 2026-10-14 for the GNN 4.1.0 migration)

## Upstream Validator

**Installed as an optional git-pinned extra.** COGANT can validate against the Active Inference Institute's `generalized-notation-notation` package through the optional `upstream` extra (`uv sync --extra upstream`; not part of `all`). The extra pins a full commit in `cogant/pyproject.toml`, mirrored in `uv.lock`: upstream `main` at `b4a583a5851021612a9a5df94e428f78aa6f76a0` (2026-10-14), distribution version `4.1.0`, 12 commits past the `v4.1.0` tag (`9255e19f951d4c9c1461514464d420bd3fc8b912`). The installed engine reports `gnn.__version__ == "4.1.0"`. The `GNN v2.0.0` value COGANT writes under `## GNNVersionAndFlags` is COGANT's own schema identifier (`cogant.schema.versions.CURRENT_GNN_VERSION`), not the upstream package release.

**Bridge boundary:** COGANT callers must use `cogant.gnn.upstream_bridge`, not a raw `import gnn`. GNN >= 4.0 installs the top-level `gnn` package; the GNN 2.x `src.gnn` import surface no longer exists. The bridge requires distribution version >= 4.0 and a `gnn` package owned by `generalized-notation-notation`, imports it lazily, and maps COGANT's facades onto the 4.x API: `validate_gnn_syntax` (level `standard`), `validate_gnn_source`, and `check_gnn_file_structure`. The 25-step pipeline runs as one `python -m gnn.main --only-steps …` invocation.

**Reference implementation used:** COGANT's own `GNNValidator` in `py/cogant/gnn/validator.py`, cross-referenced against the pinned upstream release:
- Upstream validator: `gnn.validate_gnn_syntax` at the `standard` and `strict` levels (`src/gnn/schema_validator/` in the upstream repository)
- Upstream pipeline acceptance steps: `3_gnn`, `5_type_checker` (`src/gnn/type_checker/`), and `6_validation`
- Canonical example files: `input/gnn_files/discrete/two_state_bistable.md`, `actinf_pomdp_agent.md`, `simple_mdp.md`

## Spec Source

All links are pinned to the audited commit.

- File structure: https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/blob/b4a583a5851021612a9a5df94e428f78aa6f76a0/src/gnn/documentation/file_structure.md
- Punctuation and connection grammar: https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/blob/b4a583a5851021612a9a5df94e428f78aa6f76a0/src/gnn/documentation/punctuation.md
- Schema validator: https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/tree/b4a583a5851021612a9a5df94e428f78aa6f76a0/src/gnn/schema_validator
- Type-checker: https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/tree/b4a583a5851021612a9a5df94e428f78aa6f76a0/src/gnn/type_checker
- Examples: https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/tree/b4a583a5851021612a9a5df94e428f78aa6f76a0/input/gnn_files/discrete

## Compliance Check

| Requirement | Status | Notes |
|---|---|---|
| Required upstream sections present (`GNNSection`, `GNNVersionAndFlags`, `ModelName`, `StateSpaceBlock`, `Connections`, `InitialParameterization`, `Equations`, `Time`, `ActInfOntologyAnnotation`, `ModelParameters`, `Footer`, `Signature`) | PASS | All required sections present, in canonical order, with substantive content (upstream 4.1.0 `validate_gnn_syntax` rejects empty required sections) |
| Upstream 4.1.0 `validate_gnn_syntax` on the generated control-positive model | PASS | `standard` and `strict` levels report 0 errors (see [GNN upstream audit surface](GNN_UPSTREAM_AUDIT_SURFACE.md)) |
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

Fixed by removing parentheses from single-variable endpoints. Multi-source connections use the upstream group grammar with a parenthesised source tuple (GNN 4.1.0 migration): the upstream 4.1.0 validator reads a bare comma form such as `A_m0,s_f0>o_m0` as one undeclared variable, which failed `standard` validation and upstream step `6_validation`.

**Before:**
```
(D_f0) > (s_f0)
(A_m0, s_f0) > (o_m0)
G > (u_c0)
```

**After:**
```
D_f0>s_f0
(A_m0, s_f0)>o_m0
G>u_c0
```

### Fix 3: Duplicate `## Connections` section header
**File:** `py/cogant/gnn/formatter/structural.py`, `_format_connections()`

COGANT generates two markdown sections with the header `## Connections`: the upstream-compatible one (in the upstream header block) and the COGANT extended one (detailed program-graph edge table). The upstream type-checker processes the entire file sequentially; encountering a second `## Connections` block could cause it to parse COGANT's extended table rows as malformed connection syntax.

Fixed by renaming the COGANT extended section to `## Program Graph Connections`. The validator's `CANONICAL_SECTIONS` and `base.py` `SECTION_ORDER` were updated to match.

**Before:** Two `## Connections` sections in the document.
**After:** One `## Connections` (upstream block) + one `## Program Graph Connections` (COGANT extended).

### Fix 4: Matrix literals and the EFE node under upstream GNN 4.1.0
**File:** `py/cogant/gnn/formatter/upstream.py`, `_format_initial_parameterization()` and the upstream state-space block

The GNN 4.1.0 migration aligned the `InitialParameterization` payload with how the upstream 4.x validator and render processors read shapes:

- A and B literals place rows directly inside the braces (`A_m0={ (row0), (row1) }`), so upstream reads the declared `[obs, state]` shape instead of a single 1xN row.
- A literals are column-stochastic: a hidden state without a distinct outcome gets a uniform column instead of an all-zero column that is not a probability distribution.
- B stays an explicit literal identity tensor per action slice (no symbolic `identity()` shorthand).
- The expected-free-energy node `G` is declared in `StateSpaceBlock` whenever connections route into it.

With these changes the generated control-positive models pass upstream `validate_gnn_syntax` at the `standard` and `strict` levels and upstream steps `3_gnn`, `5_type_checker`, and `6_validation`.

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
`tests/unit/test_gnn_validator_reports.py`: they distinguish an unavailable or
too-old upstream from bridge success, lock the single-invocation
`python -m gnn.main` contract on the active interpreter, and make the required
tail sections (`Equations`, `ModelParameters`, `Footer`, `Signature`)
non-optional.

## Audit Surface And Visualization

The structural validator is not the only evidence surface. The project-root
helper `tools/gnn_upstream_audit_surface.py` builds (`--collect`) or reads an
audit directory and writes JSON, Markdown, and SVG outputs that keep four claims
separate:

- pinned upstream version and bridge currentness (expected commit and version
  derived from `cogant/pyproject.toml` and `cogant/uv.lock`);
- COGANT-owned package validation plus single-file upstream validation of the
  translated model;
- selected upstream all-step execution status, reconciled against what upstream
  itself planned;
- dependency and supply-chain scan status.

Build and summarize an audit directory (the interpreter must import `cogant`
with the `upstream` extra installed):

```bash
uv run --directory cogant --extra upstream python ../tools/gnn_upstream_audit_surface.py \
  --collect --audit-dir /tmp/cogant_gnn_upstream_audit
```

Use `--strict-upstream` when the all-step upstream pipeline is a release gate.
That mode deliberately fails on selected upstream-step failures even though
normal COGANT product paths keep those failures advisory and preserve the
validated package. The companion page
[GNN upstream audit surface](GNN_UPSTREAM_AUDIT_SURFACE.md) records the
2026-10-14 results against the pinned 4.1.0 release line and explains how to
read the SVG.

## Remaining Open Issues

1. **Raw upstream import bypasses the bridge contract.** A direct `import gnn` skips the version (>= 4.0) and ownership gates and eagerly pulls in upstream's heavy dependencies. This is intentional containment: COGANT code must call the `upstream_*` facade functions rather than importing upstream modules directly.

2. **Upstream all-step execution is stricter than structural validation.** Against the pinned 4.1.0 release line, the generated calculator model passes upstream validation and every executed upstream step, including `11_render` (4/4 frameworks) and `12_execute`, which upstream runs as hard prerequisites of `16_analysis` / `18_security` even though the bridge's default selection skips them. Optional upstream extras (D2, scikit-learn, Gradio, bnlearn, an LLM backend) still change what those steps can exercise, so docs must not convert a green validator score into an all-step execution claim.

3. **Variable naming diverges from canonical upstream examples.** Upstream simple models use flat names (`s`, `o`, `A`, `B`). COGANT uses factor-indexed names (`s_f0`, `o_m0`, `A_m0`, `B_f0`). This is valid per the spec (alphanumeric + underscore allowed) and is intentional for multi-factor support. No change needed, but it may cause semantic mismatch warnings if the upstream type-checker expects single-letter names in `ActInfOntologyAnnotation`.

4. **Identity-shaped B and A payloads are structural defaults.** COGANT now emits explicit literal tensors (no `identity()` shorthand), so upstream 4.1.0 render processors read the declared shapes. The values remain identity transitions and identity-like likelihoods when the source code carries no stronger transition or observation evidence; see [`docs/theory/active_inference.md`](../theory/active_inference.md#known-limitations).
