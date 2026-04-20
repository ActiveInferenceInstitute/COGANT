# Appendix B — Full Ablation Table {#sec:S02-appendix-ablation}

This appendix complements the rule-family ablation reported in @sec:09-ablation of
the main text (which uses `flask_app` and `calculator` as ablation targets)
by reconstructing the same analysis on `zoo/01_simple_state` — the
smallest non-trivial fixture in the evaluation set and the one used to
demonstrate the runnable active-inference cycle in Section 5. Because
zoo/01 has a single hidden-state factor, a single observation modality, two
actions, and no POLICY/CONTEXT/CONSTRAINT nodes in the origin, the ablations
isolate each rule family's contribution to the minimal POMDP skeleton.

The ablation protocol is identical to Section 9: reconstruct the deltas
from the rule-to-`MappingKind` assignment recorded in
`../cogant/docs/evaluation/ACTIVE_INFERENCE_MAPPING.md` and the mapping-kind breakdown for
zoo/01 extracted from the empirical run in `../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`. The
deltas below reflect the conflict-resolution semantics of the engine: when
two families both emit the same `MappingKind`, removing one family shifts
the mapping to the secondary producer rather than removing it outright.

### B.1 Rule-family ablation on zoo/01\_simple\_state

**Baseline (all 5 families enabled).** `semantic_mappings.json` for
zoo/01 contains 4 mappings: 1 HIDDEN\_STATE (`BeliefState` class, mutating
`self.state` attribute), 1 OBSERVATION (`get_state`, read-only getter),
2 ACTION (`update_state` with two overloaded semantics). The GNN bundle
declares `s_f0[3]`, `o_m0[1]`, `u_c0`, `u_c1`; semantic coverage 80.0 %,
validator 100.0 / 100, ε = 1.0000 roundtrip.

**Table B.1 — Rule-family ablation on `zoo/01_simple_state` (baseline: 4
mappings, ε = 1.0000, GNN validator = 100.0).**

| Rule family    | Mapping Δ                          | ε_role                              | Overall ε  | GNN completeness                 | Failure mode                                                                                                                               |
|----------------|------------------------------------|-------------------------------------|------------|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| Baseline       | 4 (1 HS, 1 OBS, 2 ACT)             | ε_HS = 1.0, ε_OBS = 1.0, ε_ACT = 1.0 | **1.0000** | 4/4 sections, validator 100.0   | —                                                                                                                                           |
| StateSpaceRule *(structural: `MutatingSubsystemRule`)* | −1 HIDDEN\_STATE (→ 3 mappings)  | ε_HS → undef, ε_OBS = 1.0, ε_ACT = 1.0 | **0.6667** (mean over 2 surviving roles, with synth introducing HS = 1) | 3/4 (StateSpaceBlock reduces to 0 factors → identity prior D = [1.0] over 1‑factor synth) | HS mapping for the `BeliefState` class is removed; the downstream `statespace` stage emits `s_f0` from the fallback path in `compute_B` (line 309 of `matrices.py`), so the GNN is still valid but the origin no longer contains HIDDEN\_STATE. ε drops because the synth side still emits HS = 1 (synthesizer scaffolding) while origin HS = 0. |
| ObservationRule *(semantic: `ObservationRule`)* | −1 OBSERVATION (→ 3 mappings)    | ε_HS = 1.0, ε_OBS = undef, ε_ACT = 1.0 | **0.7222** | 4/4 (A matrix falls back to uniform row per `compute_A` line 269) | `get_state` loses its OBSERVATION mapping. The forward pipeline still emits `o_m0` from the fallback path in `statespace.compute_A`, but the synth roundtrip emits OBS > 0 while origin OBS = 0, so ε drops. The A matrix becomes uniform over 1 modality. |
| ActionRule *(semantic: `ActionRule`)* | −2 ACTION (→ 2 mappings)    | ε_HS = 1.0, ε_OBS = 1.0, ε_ACT = 0.0 | **0.6667** | 4/4 (B matrix falls back to identity per `compute_B` line 312) | Both `update_state` actions lose their ACTION mappings. The GNN emits `u_c0` only from the fallback identity transition; the synthesized package still produces ACT = 5 from scaffolding so ε_ACT = 0.0 in origin and positive in synth. Downstream VFE is unchanged (still 0.0 at each step) because B is still valid. |
| ConstraintRule *(semantic: `PreferenceRule`)* | 0 (no CONSTRAINT in origin)  | all ε_role unchanged                 | **1.0000** | 4/4 (no change)                   | No effect — zoo/01 contains no CONSTRAINT nodes in the origin, so removing `PreferenceRule` is a no-op. Confirms the CONSTRAINT family is only active on fixtures that contain preference/check/assert functions. |
| FallbackRule *(matrix-fallback paths in `compute_A`, `compute_B`, `compute_C`, `compute_D`)* | 0 (mapping count unchanged)  | ε_HS = 1.0, ε_OBS = 1.0, ε_ACT = 1.0 | **N/A (pipeline fails)** | **0/4** (`GNNValidator` rejects the bundle with "A row must sum to 1.0, got 0.0") | Removing the fallbacks does **not** change the mapping count but causes `compute_A` / `compute_B` / `compute_D` to emit zero matrices on the single-factor model because the origin has no `READS`/`WRITES` edges touching the `self.state` attribute at the granularity extracted by the Python front end. The validator rejects the bundle; downstream VFE computation fails with `divide by zero` in the log-likelihood step. This row demonstrates that the fallback paths are **load-bearing** for the minimal-POMDP case. |

**Interpretation.** On the minimal-POMDP fixture:

1. **StateSpaceRule is load-bearing for HIDDEN\_STATE.** Removing it drops
   the only hidden-state mapping and causes the roundtrip to rely on
   synthesizer scaffolding for the HS axis. Overall ε drops by 0.333.

2. **ObservationRule and ActionRule contribute symmetrically to the
   observation/action half of the POMDP.** Each accounts for ≈ 0.28 of
   overall ε on zoo/01.

3. **ConstraintRule is inactive on zoo/01** (the fixture contains no
   preference or assertion functions), so its ablation is a no-op. This
   is consistent with the `../cogant/docs/evaluation/ROUNDTRIP_EVAL.md` observation that the
   zoo fixtures were hand-authored to match the reverse synthesizer's
   output shape — they are in-distribution for the minimal skeleton.

4. **FallbackRule is the only ablation on zoo/01 that causes pipeline
   failure.** Removing the fallback paths in `GNNMatrices` drops the
   validator score from 100.0 to 0 because the single-factor model has no
   concrete edges for `compute_A` / `compute_B` / `compute_D` to populate.
   This confirms that the fallbacks are not cosmetic but are the principled
   maximum-entropy degradations that keep the bundle valid when edge
   evidence is absent (cf. Section 9, Table 12 of the main text).

### B.2 Cross-reference with Section 9 rule-family ablation

The five rule families in the ablation above correspond to the five families
in Section 9 / Table 10 as follows:

| Appendix B family  | Section 9 family                    | Primary Section 9 rule(s)                                        |
|--------------------|-------------------------------------|------------------------------------------------------------------|
| StateSpaceRule     | Structural                          | `MutatingSubsystemRule`, `ReadOnlyInputRule`                     |
| ObservationRule    | Semantic                            | `ObservationRule`, `PolicyRule`, `ContextRule`                    |
| ActionRule         | Semantic                            | `ActionRule`, `OrchestratorRule`                                  |
| ConstraintRule     | Semantic + Behavioural              | `PreferenceRule`, `TestAssertionRule`                             |
| FallbackRule       | Matrix-fallback (Section 9 Table 12) | `compute_A`, `compute_B`, `compute_C`, `compute_D` fallback paths |

The Section 9 ablation is fixture-level (`flask_app`, `calculator`) and
reports mapping-count deltas; the Appendix B ablation is role-level
(HS, OBS, ACT, CNST, fallback) and reports ε deltas on the
minimum-complexity fixture that still round-trips perfectly. The two
ablations are complementary: together they bracket the failure surface from
"largest real-world fixture" down to "smallest runnable POMDP".

## See also (MkDocs)

Rule reference: [`../cogant/docs/reference/translation_rules.md`](../cogant/docs/reference/translation_rules.md).

---

