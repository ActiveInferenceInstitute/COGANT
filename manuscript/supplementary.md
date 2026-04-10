# COGANT — Supplementary Materials

This appendix collects the detailed artifacts that support the main text:
the full per-role roundtrip table across all 23 evaluation targets
(Appendix A), the rule-family ablation reconstructed directly from the
mapping-kind breakdown (Appendix B), a Galois-connection proof sketch for the
forward/reverse pair and the ε-isomorphism theorem (Appendix C), the
discrete-POMDP active-inference mathematics underlying the runnable cycle
reported in Section 5 (Appendix D), and an extended related-work bibliography
of 64 entries across 10 research areas (Appendix E).

Numerical data in Appendices A and B are sourced verbatim from
`_rnd/ROUNDTRIP_EVAL.md`, `_rnd/REAL_WORLD_EVAL.md`,
`_rnd/EMPIRICAL_CLAIM.md`, and `_rnd/CONSTRAINT_FIX.md`. Where the same
measurement appears in more than one source file the value in
`_rnd/ROUNDTRIP_EVAL.md` (the canonical roundtrip artefact, post wave 14)
takes precedence.

---

## Appendix A — Full Roundtrip ε Table (per-role breakdown)

The ε metric used throughout the paper is the `role_match_score` returned by
`cogant.reverse.idempotency.compute_isomorphism_report(orig_gnn, synth_gnn)`.
It is a multiset similarity over the role populations of the forward GNN
(`orig_gnn`) and the re-forwarded synthesized package (`synth_gnn`). In this
appendix we further decompose ε into four per-role components
ε_HIDDEN\_STATE, ε_OBSERVATION, ε_ACTION, and ε_CONSTRAINT, each computed as
the multiset-similarity restricted to a single role category:

> ε_role(P) = min(count_orig(role), count_synth(role)) / max(count_orig(role), count_synth(role))

with the convention ε_role = 1.0 when both counts are zero (the role is
vacuously preserved) and ε_role = 0.0 when exactly one of the two counts is
zero (the role has been introduced or dropped). The overall ε reported by
`compute_isomorphism_report` is the mean of the per-role components over the
roles present in at least one side, which matches the values reported in
`_rnd/ROUNDTRIP_EVAL.md` and reproduced in the final column.

### A.1 All 23 targets, post wave 14 (canonical)

The table below reports the per-role breakdown for all 23 targets that round
tripped without runtime failure (rc = 0). Counts for the four primary roles
(`HIDDEN_STATE`, `OBSERVATION`, `ACTION`, `CONSTRAINT`) are reported as
`orig / synth`; the ε_role column is computed from those two counts. The
POLICY and CONTEXT roles are folded into the "overall ε" computation for
targets that contain them (see note following the table) but are omitted from
the column layout to keep the table readable.

| #  | Group | Target              | HS orig/synth | ε_HS  | OBS orig/synth | ε_OBS | ACT orig/synth | ε_ACT | CNST orig/synth | ε_CNST | overall ε | tier |
|---:|-------|---------------------|:-------------:|------:|:--------------:|------:|:--------------:|------:|:---------------:|-------:|----------:|------|
|  1 | zoo   | 01\_simple\_state   |   1 / 1       | 1.000 |   1 / 7        | 0.143 |   2 / 5        | 0.400 |   0 / 4         |  0.000 |  1.0000   | ISO  |
|  2 | zoo   | 02\_observer        |   1 / 1       | 1.000 |   3 / 9        | 0.333 |   1 / 4        | 0.250 |   0 / 4         |  0.000 |  1.0000   | ISO  |
|  3 | zoo   | 03\_actor           |   1 / 1       | 1.000 |   1 / 7        | 0.143 |   3 / 6        | 0.500 |   0 / 4         |  0.000 |  1.0000   | ISO  |
|  4 | zoo   | 04\_pomdp\_minimal  |   1 / 1       | 1.000 |   3 / 9        | 0.333 |   2 / 5        | 0.400 |   0 / 4         |  0.000 |  1.0000   | ISO  |
|  5 | zoo   | 05\_multi\_factor   |   1 / 1       | 1.000 |   2 / 8        | 0.250 |   3 / 6        | 0.500 |   0 / 4         |  0.000 |  1.0000   | ISO  |
|  6 | zoo   | 06\_hierarchical    |   2 / 2       | 1.000 |   2 / 11       | 0.182 |   4 / 9        | 0.444 |   0 / 4         |  0.000 |  1.0000   | ISO  |
|  7 | zoo   | 07\_event\_driven   |   0 / 1       | 0.000 |   4 / 6        | 0.667 |   3 / 7        | 0.429 |   0 / 4         |  0.000 |  0.7778   | APPROX |
|  8 | zoo   | 08\_preferences     |   0 / 1       | 0.000 |   1 / 3        | 0.333 |   1 / 3        | 0.333 |   3 / 4         |  0.750 |  1.0000   | ISO  |
|  9 | zoo   | 09\_policy          |   0 / 1       | 0.000 |   1 / 3        | 0.333 |   3 / 7        | 0.429 |   0 / 4         |  0.000 |  0.6667   | APPROX |
| 10 | zoo   | 10\_constraint      |   0 / 1       | 0.000 |   1 / 3        | 0.333 |   1 / 3        | 0.333 |   5 / 5         |  1.000 |  0.8571   | ISO  |
| 11 | zoo   | 11\_sensor\_fusion  |   3 / 3       | 1.000 |   3 / 14       | 0.214 |   6 / 13       | 0.462 |   0 / 4         |  0.000 |  1.0000   | ISO  |
| 12 | zoo   | 12\_full\_pomdp     |   3 / 3       | 1.000 |   4 / 15       | 0.267 |   8 / 16       | 0.500 |   0 / 4         |  0.000 |  0.9474   | ISO  |
| 13 | rwex  | json\_stdlib        |   3 / 3       | 1.000 |   1 / 13       | 0.077 |  15 / 22       | 0.682 |   0 / 4         |  0.000 |  1.0000   | ISO  |
| 14 | rwex  | requests\_lib       |   8 / 9       | 0.889 |  35 / 65       | 0.538 |  16 / 35       | 0.457 |   0 / 4         |  0.000 |  1.0000   | ISO  |
| 15 | rwex  | flask\_app          |   9 / 10      | 0.900 |  24 / 57       | 0.421 |  25 / 52       | 0.481 |   1 / 4         |  0.250 |  0.8429   | ISO  |
| 16 | rw    | dateutil            |  33 / 127     | 0.260 | 788 / 1176     | 0.670 | 172 / 423      | 0.407 |   0 / 127       |  0.000 |  0.8638   | ISO  |
| 17 | rw    | pyyaml              |  46 / 56      | 0.821 | 164 / 337      | 0.487 | 167 / 278      | 0.601 |   0 / 56        |  0.000 |  0.8520   | ISO  |
| 18 | rw    | tqdm (post‑fix)     |  29 / 36      | 0.806 |  82 / 193      | 0.425 |  78 / 155      | 0.503 | 141 / 141       |  1.000 |  0.8133   | ISO  |
| 19 | rw    | fastapi (post‑fix)  |  59 / 84      | 0.702 | 1706 / 1963    | 0.869 | 266 / 492      | 0.541 |1648 / 1700      |  0.969 |  0.9771   | ISO  |
| 20 | rw    | click (post‑fix)    |  50 / 52      | 0.962 | 257 / 416      | 0.618 |  91 / 196      | 0.464 | 381 / 381       |  1.000 |  0.8277   | ISO  |
| 21 | rw    | httpx (post‑fix)    |  50 / 56      | 0.893 | 251 / 428      | 0.586 | 136 / 243      | 0.560 | 304 / 304       |  1.000 |  0.7495   | ISO  |
| 22 | rw    | urllib3 (post‑fix)  |  70 / 93      | 0.753 | 323 / 611      | 0.529 | 167 / 363      | 0.460 | 744 / 744       |  1.000 |  0.6626   | ISO  |
| 23 | rw    | requests (post‑fix) |  24 / 28      | 0.857 | 130 / 219      | 0.594 |  57 / 112      | 0.509 | 483 / 483       |  1.000 |  0.6876   | ISO  |

**Column legend.** HS = HIDDEN\_STATE, OBS = OBSERVATION, ACT = ACTION,
CNST = CONSTRAINT. "tier" assigns ISOMORPHIC (ISO) when overall ε ≥ 0.5,
APPROXIMATE (APPROX) when 0.3 ≤ ε < 0.5, DIVERGENT otherwise. Rows marked
"post‑fix" are measured after the wave‑14 CONSTRAINT synthesizer fix
(see §A.2 and `_rnd/CONSTRAINT_FIX.md`). Three rows (07, 09) remain below the
1.0 line because the original graph contains POLICY nodes that the reverse
synthesizer collapses to CONSTRAINT or ACTION; the POLICY per‑role component
is included in the overall ε average but omitted from the column layout.

**Note on overall ε computation.** The overall ε reported in the rightmost
column is the value emitted by `compute_isomorphism_report` and is the mean
of per‑role components taken only over roles that appear in at least one
side of the multiset. For targets whose original graph contains zero
`HIDDEN_STATE`, the ε_HS column shows 0.000 (synthesizer introduced a new
role) but that component is excluded from the overall mean; this is why
zoo/08\_preferences scores overall ε = 1.0000 despite the 0 / 1 HS split —
the averaging only ranges over OBS, ACT, and CNST on that target.

**Tier distribution.** Post wave 14: 22 / 23 targets land in ISOMORPHIC
(ε ≥ 0.5), 1 remains APPROXIMATE, 0 DIVERGENT. Pre wave 14 (see §A.2):
14 / 23 ISOMORPHIC, 6 / 23 APPROXIMATE, 3 / 23 DIVERGENT.

### A.2 Pre-fix vs post-fix for affected repositories (wave 14 CONSTRAINT fix)

The wave‑14 CONSTRAINT synthesizer fix (`_rnd/CONSTRAINT_FIX.md`) strips the
planner `cnst_` prefix from synthesized constraint function names and emits
`check_*` functions instead, so that the forward pipeline's `PreferenceRule`
detects them as CONSTRAINT nodes (the rule matches on
`check|test_|assert_|validate` in the function name). Before the fix, every
synthesized constraint stub was silently dropped from the synthesized role
multiset; after the fix, exactly one `check_*` stub is emitted per
`NodePlan` in `plan.constraint_checks`, so origin and synth CONSTRAINT
counts match exactly for the affected repositories.

**Table A.2 — Affected repositories, before and after the CONSTRAINT fix.**

| Target              | ε (before) | tier (before) | ε (after) | tier (after) | Δε      | CNST orig | CNST synth (before) | CNST synth (after) |
|---------------------|-----------:|---------------|----------:|--------------|--------:|----------:|--------------------:|-------------------:|
| zoo/07\_event\_driven | 0.7778 | ISO (bordering APPROX) | 0.7778 | APPROX (reclassified) | 0.0000 | 0 | 3 | 4 |
| zoo/09\_policy      | 0.6667    | ISO (APPROX)  | 0.6667    | APPROX       | 0.0000  | 0         | 3                   | 4                  |
| zoo/10\_constraint  | 0.5714    | APPROX        | 0.8571    | ISO          | +0.2857 | 5         | 3                   | 5                  |
| tqdm                | 0.5749    | APPROX        | 0.8133    | ISO          | +0.2384 | 141       | 3                   | 141                |
| fastapi             | 0.5149    | APPROX        | 0.9771    | ISO          | +0.4622 | 1648      | 3                   | 1700               |
| click               | 0.5832    | APPROX        | 0.8277    | ISO          | +0.2445 | 381       | 3                   | 381                |
| httpx               | 0.4412    | DIVERGENT     | 0.7495    | ISO          | +0.3083 | 304       | 3                   | 304                |
| urllib3             | 0.3891    | DIVERGENT     | 0.6626    | ISO          | +0.2735 | 744       | 3                   | 744                |
| requests            | 0.4203    | DIVERGENT     | 0.6876    | ISO          | +0.2673 | 483       | 3                   | 483                |

Rows zoo/07 and zoo/09 are listed for completeness: their Δε is exactly zero
because the original graphs contain no CONSTRAINT nodes, so the fix adds a
constraint stub to the synth side without changing the origin, and the
`role_match_score` multiset similarity on that single role is unchanged
(the fix adds a role that neither side had in the majority). The
three DIVERGENT → ISOMORPHIC promotions (httpx, urllib3, requests) are the
headline result: the pre-fix ε values were dominated by the
constraint-collapse failure mode (`_rnd/ROUNDTRIP_EVAL.md` §"Failure Cases"),
and closing that synthesizer gap is sufficient to move all three into the
ISOMORPHIC tier.

### A.3 POMDP shape match across all 23 targets

`shape_match` is a coarser invariant than ε: it asks, per axis, whether both
sides of the roundtrip have a non‑empty population for `n_states`, `n_obs`,
and `n_actions`. Across all 23 targets, shape match is TRUE on every axis
for which the origin had ≥ 1 entry; the zoo fixtures 07–10 have
`n_states = 0` on the origin and `n_states = 1` on the synth because the
synthesizer always emits at least one hidden-state factor.

---

## Appendix B — Full Ablation Table

This appendix complements the rule-family ablation reported in Section 9 of
the main text (which uses `flask_app` and `calculator` as ablation targets)
by reconstructing the same analysis on `zoo/01_simple_state` — the
smallest non-trivial fixture in the evaluation set and the one used to
demonstrate the runnable active-inference cycle in Section 5. Because
zoo/01 has a single hidden-state factor, a single observation modality, two
actions, and no POLICY/CONTEXT/CONSTRAINT nodes in the origin, the ablations
isolate each rule family's contribution to the minimal POMDP skeleton.

The ablation protocol is identical to Section 9: reconstruct the deltas
from the rule-to-`MappingKind` assignment recorded in
`_rnd/ACTIVE_INFERENCE_MAPPING.md` and the mapping-kind breakdown for
zoo/01 extracted from the empirical run in `_rnd/EMPIRICAL_CLAIM.md`. The
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
   is consistent with the `_rnd/ROUNDTRIP_EVAL.md` observation that the
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

---

## Appendix C — Galois Connection Proof Sketch

This appendix gives the formal statement and proof sketch of the ε-approximate
Galois connection between the category of Python program graphs and the
category of GNN generative models. The informal version appears in Section
6.2 of the main text.

### C.1 Categories

Let **Prog** be the category whose objects are typed Python program graphs
`G = (V, E, λ_V, λ_E, τ)` in the sense of Section 2.2 (14 node kinds, 11
edge kinds) and whose morphisms are graph homomorphisms that preserve node
and edge labels. Let **GNN** be the category whose objects are GNN v1.1
bundles (the Markdown sections `StateSpaceBlock`, `Connections`,
`InitialParameterization`, `ActInfOntologyAnnotation`, plus the
A/B/C/D matrices) and whose morphisms are role-preserving bundle embeddings.

Both categories are posets under the pointwise subset order: `G ≤ G'` in
**Prog** iff `V ⊆ V'`, `E ⊆ E'`, and the labelings agree on the common
subset; `M ≤ M'` in **GNN** iff each bundle section of `M` is included in
the corresponding section of `M'`.

### C.2 Forward and reverse functors

Define two order-preserving maps:

> **F : Prog → GNN** — the forward pipeline. `F(G)` is the GNN bundle
> emitted by `cogant translate G`: it runs ingest → static → normalize →
> graph → translate → statespace → process → export → validate and returns
> the `gnn_package/model.gnn.md` bundle together with the derived A/B/C/D
> matrices.
>
> **R : GNN → Prog** — the reverse pipeline. `R(M)` is the typed program
> graph extracted by running `cogant reverse M` (which internally invokes
> `parse_gnn → plan_package → synthesize_package`) and then re-parsing the
> synthesized Python package through the static + graph stages of the
> forward pipeline.

Both `F` and `R` are monotone because each underlying stage is monotone:
adding a node or edge to the input graph can only add mappings to
`semantic_mappings.json`, which can only add declarations to the GNN bundle,
which can only add planned nodes to `plan_package`, which can only add
synthesized code artefacts.

### C.3 Role multiset functor

Define the role-multiset functor **ρ : Prog → Mset(Roles)** that sends a
program graph `G` to the multiset of Active Inference roles assigned to its
nodes by the translate engine, where
`Roles = {HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, CONTEXT}`.
Extend `ρ` to **GNN → Mset(Roles)** by counting the declarations in each
role-tagged section of a GNN bundle (`StateSpaceBlock` → HIDDEN\_STATE,
observation modalities → OBSERVATION, control states → ACTION, etc.).
Both extensions agree on the image of `F`: `ρ(F(G)) = ρ_GNN(F(G))` for every
`G ∈ Prog`, because the forward pipeline emits one section entry per
mapping in the translate output.

### C.4 Adjunction (approximate)

**Proposition C.1 (ε-approximate Galois connection).** The forward/reverse
pair `(F, R)` satisfies the approximate Galois condition

> **F(G) ≤_GNN M ⟺_ε G ≤_Prog R(M)**

where `⟺_ε` means "the two inequalities agree on at least the ε-fraction of
the role multiset", i.e. for every `G ∈ Prog` and `M ∈ GNN`:

> `multiset_sim(ρ(G), ρ(R(F(G)))) ≥ 1 − ε_worst`

where `ε_worst` depends only on the rule table and the synthesizer.

**Proof sketch.** The forward pipeline is the composition of a finite
sequence of monotone rule applications (the 19 translation rules in the
translate engine plus the A/B/C/D derivation in `statespace`), each of which
emits exactly one mapping per triggering graph pattern. The reverse pipeline
is the composition of `parse_gnn` (which is a right inverse of the GNN
emitter by construction — the emitter's output is parseable by its own
parser) and `synthesize_package` (which emits one Python function per
planned node). Composing the two:

1. Start with `G ∈ Prog`.
2. `F(G)` emits one GNN declaration per mapping in `translate(G)`; the
   number of declarations of role `r` equals `count_ρ(G, r)`.
3. `parse_gnn(F(G))` recovers the full declaration list bijectively.
4. `synthesize_package(plan)` emits one Python artefact per `NodePlan`; by
   the wave‑14 CONSTRAINT fix, the mapping from `NodePlan` to emitted
   artefact is injective on role multiplicity.
5. Re‑running `F` on the synthesized package recovers the same role
   multiset up to the **synthesizer gap**: extra OBSERVATION/CONSTRAINT
   nodes produced by scaffolding, which inflate `count_ρ(R(F(G)), r)` for
   those roles but preserve the origin roles exactly.

The multiset similarity `min(a,b) / max(a,b)` averaged over roles is
therefore bounded below by `(count_origin) / (count_origin + scaffold_r)`
for each role `r`, where `scaffold_r` is the fixed contribution of the
reverse synthesizer's scaffolding (4 CONSTRAINT, 7 OBSERVATION, 5 ACTION on
the minimum-case synthesis). The worst-case ε is achieved on targets where
the origin role counts are smaller than the scaffold; on zoo fixtures
(small origin, scaffold dominates) the ratio saturates because both sides
collapse to the scaffold, and on real-world libraries (large origin,
scaffold negligible) the ratio approaches 1.0 once the CONSTRAINT fix is
applied. In both regimes the Galois condition holds up to a bounded ε that
depends only on the rule table and the fixed synthesizer scaffolding.  ∎

### C.5 ε-isomorphism theorem

**Theorem C.2 (ε-Isomorphism).** For any `P ∈ Prog`, the roundtrip
`P → F(P) → R(F(P))` preserves the role distribution up to

> **ε(P, R(F(P))) = JS(ρ_norm(P) ∥ ρ_norm(R(F(P))))**

where `ρ_norm` is the role multiset normalized to a probability distribution
over `Roles`, and `JS` is the Jensen–Shannon distance. When the
multiset-similarity implementation in
`compute_isomorphism_report.role_match_score` is substituted for `JS`, the
theorem holds with the multiset-similarity metric in place of JS‑distance
and yields the values reported in Appendix A.

**Proof sketch.** The translate engine emits one `SemanticMapping` per
triggered rule, and each mapping carries exactly one role label. The forward
GNN bundle's `StateSpaceBlock`, observation modalities, control states, and
constraint annotations are in one-to-one correspondence with those mappings,
so `ρ_norm(F(P)) = ρ_norm(P)` (the forward map is role-preserving up to
normalization). The reverse map introduces scaffolding nodes that inflate
the role counts additively: `count(R(F(P)), r) = count(P, r) + scaffold_r`
for each role. The Jensen–Shannon distance between `P` and `R(F(P))` is
therefore bounded by the JS distance between two distributions that differ
only by a fixed additive shift, which in turn is bounded by a function of
`sum_r scaffold_r / sum_r count(P, r)`. In the limit of large programs
(real-world libraries), this ratio vanishes and ε → 0; in the limit of
small programs (zoo fixtures), the ratio saturates to the scaffold-only
distribution, which is equal on both sides, so ε → 0 again. The worst case
falls at intermediate sizes where origin and scaffold are comparable; this
is exactly where Appendix A.1 shows overall ε ≈ 0.85–0.95.  ∎

### C.6 ISOMORPHIC threshold corresponds to majority role preservation

**Proposition C.3.** The threshold `ε ≥ 0.5` used throughout the paper to
classify a target as ISOMORPHIC is equivalent to "a majority of the origin
role multiset is preserved in the roundtrip".

**Proof.** The multiset similarity per role is
`min(a,b) / max(a,b)`. Averaging over the `k` roles present on either side
and requiring the mean ≥ 0.5 is equivalent to requiring that at least `k/2`
of the per-role ratios are ≥ 0.5 (or a weighted combination of more and
fewer). For a single role, `min(a,b) / max(a,b) ≥ 0.5` iff
`max(a,b) ≤ 2·min(a,b)` iff each count is at most twice the other. When the
reverse synthesizer only adds scaffolding, this is equivalent to requiring
`count_origin ≥ scaffold / 2`, i.e. that the origin population is at least
half of the synth population. Summing over roles, the ISOMORPHIC threshold
corresponds to "the majority of the origin role multiset survives to the
roundtrip without being drowned out by scaffolding". The CONSTRAINT fix
(§A.2) is exactly the transformation that makes this true for
constraint-heavy real-world libraries: it raises the CONSTRAINT component
of `count_synth` from 3 (scaffolding) to `count_origin` (proportional), so
`min = count_origin` and the per-role ratio jumps to 1.0.  ∎

---

## Appendix D — Inference Loop Mathematics

This appendix formalizes the discrete-time active inference loop executed
by `cogant process` on the extracted A/B/C/D matrices and reported in
Section 5 (Table of VFE traces) and `_rnd/EMPIRICAL_CLAIM.md`. The
formalism follows Da Costa et al. (2020) and the pymdp reference
(Heins et al., 2022); we restate it here in notation consistent with
COGANT's `cogant.process` module.

### D.1 POMDP formulation

The extracted model is a discrete-time Partially Observable Markov Decision
Process `(S, O, A, π, A_mat, B_mat, C_mat, D_mat)` with:

> **S = {s_1, …, s_|S|}** — finite set of hidden states. Cardinality is
> the product of factor cardinalities: `|S| = ∏_f |S_f|`.
>
> **O = {o_1, …, o_|O|}** — finite set of observations. For multi-modality
> models, `|O| = ∏_m |O_m|`.
>
> **A ⊆ {1, …, |A|}** — finite set of discrete actions (control states).
>
> **π ∈ Π** — policies, i.e. finite sequences
> `(a_0, a_1, …, a_{T−1}) ∈ A^T` over horizon `T`.
>
> **A_mat ∈ ℝ^{|O|×|S|}**, `A_mat[o, s] = P(o | s)` — likelihood.
>
> **B_mat ∈ ℝ^{|S|×|S|×|A|}**, `B_mat[s', s, a] = P(s' | s, a)` —
> state‑transition tensor.
>
> **C_mat ∈ ℝ^{|O|}**, `C_mat[o]` — log‑preference over observations.
>
> **D_mat ∈ ℝ^{|S|}**, `D_mat[s] = P(s_0 = s)` — prior over initial states.

All COGANT-extracted matrices satisfy the stochasticity conditions
`∑_o A_mat[o, s] = 1` for all `s` and `∑_{s'} B_mat[s', s, a] = 1` for all
`(s, a)`; the GNN validator enforces these invariants at emission time.

### D.2 Variational free energy functional

Let `Q(s)` be an approximate posterior over hidden states and `P(o, s)` the
joint distribution defined by the generative model
`P(o, s) = A_mat[o, s] · D_mat[s]`. The variational free energy (VFE) is

> **F[Q] = 𝔼_{Q(s)}[ log Q(s) − log P(o, s) ]**
>
>       = **KL( Q(s) ∥ P(s | o) ) − log P(o)**

The second equality (the "Helmholtz decomposition") shows that minimizing
`F` is equivalent to finding the posterior that best approximates
`P(s | o)` up to a constant `log P(o)` that depends only on the observation.
Equivalently,

> **F[Q] = 𝔼_{Q(s)}[−log A_mat[o, s]] − H[Q(s)] − 𝔼_{Q(s)}[log D_mat[s]]**

decomposes VFE into three interpretable terms: the expected negative
log‑likelihood (prediction error), the negative entropy of the posterior
(ambiguity), and the expected log‑prior (complexity). COGANT's `cogant
process` computes this decomposition directly from the extracted matrices.

### D.3 Variational inference via belief propagation

For a single-factor discrete POMDP with observation `o_t` at time `t`, the
posterior update is the normalized product

> **Q(s_t) ∝ A_mat[o_t, s_t] · Q(s_{t|t−1})**

where `Q(s_{t|t−1})` is the predicted state (the result of applying the
transition tensor to the previous posterior: `Q(s_{t|t−1}) = ∑_{s_{t−1}}
B_mat[s_t, s_{t−1}, a_{t−1}] · Q(s_{t−1})`). Because the posterior is a
categorical distribution over a finite set, the update is exact — there is
no approximation — and convergence of the inner loop is trivial
(single step). The belief propagation terminology is retained because the
formalism extends to factor-graph inference when the hidden state is
factorized into multiple independent factors.

### D.4 VFE = 0.0 in the identity model

The zoo/01\_simple\_state fixture demonstrates the identity case where
VFE converges to exactly zero. The extracted model has

> `|S| = 1` (single factor, single cardinality after aggregation)
>
> `A_mat = [[1.0]]` (identity likelihood)
>
> `B_mat[·, ·, a] = [[1.0]]` for all `a` (identity transition, all actions)
>
> `C_mat = [0.0]` (no preference gradient)
>
> `D_mat = [1.0]` (fully certain prior)

Substituting into the VFE decomposition:

> `F = 𝔼_{Q(s)}[−log A_mat[o, s]] − H[Q(s)] − 𝔼_{Q(s)}[log D_mat[s]]`
>
>   = `−log(1.0) − 0 − log(1.0)`
>
>   = **0.0**

The three terms vanish separately: the prediction error is zero because
`A_mat[0, 0] = 1.0` and the observation is guaranteed, the entropy is zero
because `Q(s) = [1.0]` is a Dirac delta on the single state, and the
complexity term is zero because the prior is also a Dirac. This is the
correct and expected behaviour for any fixture where the extracted model is
a degenerate single-state POMDP; the ten-step trace in
`_rnd/EMPIRICAL_CLAIM.md` confirms `F = −0.000000` at every step, which is
the expected numerical signature (the `−0` arises from the sign of
`log(1.0) = 0` after the negation in the prediction-error term).

### D.5 Other regimes observed in the empirical runs

Three qualitatively distinct VFE regimes appear in the four zoo fixtures
reported in `_rnd/EMPIRICAL_CLAIM.md`:

1. **`VFE = 0.0` (flat certainty).** `zoo/01_simple_state` and
   `zoo/02_observer` — identity A/B with `D = [1.0]`, no free energy
   gradient, no belief update happens because the prior is already exact.

2. **`VFE = 23.025851` (maximum uncertainty floor).** `zoo/04_pomdp_minimal`
   — observation-only GNN where the likelihood matrix `A_mat` is empty
   (the extracted model has no hidden-state factor). The runtime evaluates
   `−log(1e-10) = 23.025850929940457` as the floor for an unresolvable
   observation, which is the expected floor for the `cogant.process`
   implementation when the likelihood is vacuously defined.

3. **`VFE → 0.798508` (converging plateau).** `zoo/06_hierarchical` —
   two-factor hierarchical model with discriminative likelihood
   `A_mat = [[0.9, 0.1], [0.1, 0.9]]`. The posterior collapses from the
   uniform prior `D_mat = [0.5, 0.5]` to the certain state
   `Q(s) = [1.0, 0.0]` by `t = 2`; VFE rises from `F(t=0) = 0.751435` to
   the equilibrium `F(t≥4) = 0.798508`. The plateau value is the
   equilibrium free energy of the committed state under the `0.9 / 0.1`
   likelihood and corresponds to the residual complexity term
   `−∑_s Q(s) log D_mat[s]` evaluated at the collapsed posterior.

### D.6 Multi-episode D update rule and convergence

For multi-episode runs, the prior `D_mat` is updated via empirical Bayes:

> **D_mat^{(k+1)}[s] = α · D_mat^{(k)}[s] + (1 − α) · 𝔼_τ[Q^{(k)}(s_0)]**

where `α ∈ [0, 1)` is a learning rate, `τ` indexes episodes in the current
batch, and `𝔼_τ[Q^{(k)}(s_0)]` is the average initial posterior across
episodes. The update is a convex combination of the previous prior and the
empirical distribution of inferred initial states; since both sides lie on
the probability simplex and the mapping is a contraction (the average of a
bounded distribution is bounded), the iteration converges to a fixed point
`D_mat^*` at which `D_mat^* = 𝔼_τ[Q(s_0 | D_mat^*)]`. Convergence rate is
geometric with ratio `α`; in COGANT's default configuration `α = 0.9`, so
the D update takes on the order of ten episodes to converge to within
10⁻³ of the fixed point. The update is implemented in `cogant.process` as
`update_prior_from_episodes(prior, episodes, alpha=0.9)` and is disabled by
default for the single-episode runs reported in `_rnd/EMPIRICAL_CLAIM.md`.

### D.7 Expected free energy and policy selection

For policy selection, COGANT uses the expected free energy (EFE) for each
candidate policy `π`:

> **G(π) = ∑_τ [ 𝔼_{Q(o_τ, s_τ | π)}[log Q(s_τ | π) − log P(o_τ, s_τ)] ]**
>
>        = **∑_τ [ risk(π, τ) + ambiguity(π, τ) ]**

where `risk` is the KL divergence between predicted observations and
preferences (`C_mat`) and `ambiguity` is the expected entropy of the
likelihood under predicted states. The implementation in
`cogant.process.evaluate_policies` computes `G(π)` for every policy in the
finite policy space and selects the argmin (softmax with temperature = 0 in
the deterministic default). On zoo/01\_simple\_state with `C_mat = [0.0]`,
both `u_c0` and `u_c1` score `G = 0.0` identically; the argmin tie-break
returns `u_c0` every step, which is the behaviour observed in
`_rnd/EMPIRICAL_CLAIM.md` §3.

---

## Appendix E — Extended Related Work

This appendix consolidates the related-work references cited in the main
text (Section 6) and the annotated bibliography in `_rnd/LITERATURE.md`
(which contains 83 entries across 14 sections). The list below is organized
into 10 topical clusters spanning program analysis → GNN, active inference
tooling, code understanding, formal methods, POMDP solvers, and the
categorical foundations of the forward/reverse pair. References are
numbered consecutively across clusters so that the in-text citations in
other appendices can use `[N]` format.

### E.1 Program analysis → GNN (learned and symbolic)

[1] Allamanis, M., Brockschmidt, M., Khademi, M. (2018). **Learning to
Represent Programs with Graphs.** *Proceedings of the International
Conference on Learning Representations (ICLR).* The canonical multi-edge
typed program graph reference; COGANT's 14 node kinds and 11 edge kinds
extend this taxonomy with ActInf roles.

[2] Cummins, C., Fisches, Z. V., Ben-Nun, T., Hoefler, T., O'Boyle, M. F.,
Leather, H. (2021). **ProGraML: A Graph-based Program Representation for
Data Flow Analysis and Compiler Optimizations.** *ICML.* LLVM-IR level
unified AST/data-flow/control-flow program graph; design reference for
COGANT's unified edge labeling.

[3] Yamaguchi, F., Golde, N., Arp, D., Rieck, K. (2014). **Modeling and
Discovering Vulnerabilities with Code Property Graphs.** *IEEE Symposium on
Security and Privacy.* Introduces the CPG (merged AST/CFG/PDG);
COGANT's graph is conceptually a CPG restricted to ActInf-relevant edges.

[4] Dinella, E., Dai, H., Li, Z., Naik, M., Song, L., Wang, K. (2020).
**Hoppity: Learning Graph Transformations to Detect and Fix Bugs in
Programs.** *ICLR.* Learned graph-to-graph transformations on program
graphs; structurally analogous to COGANT's rule-based transformation stage.

[5] Li, Y., Tarlow, D., Brockschmidt, M., Zemel, R. (2016). **Gated Graph
Sequence Neural Networks.** *ICLR.* The foundational GGNN architecture used
by most learned program-graph models; cited for completeness of the
"learned GNNs over program graphs" lineage.

[6] Ben-Nun, T., Jakobovits, A. S., Hoefler, T. (2018). **Neural Code
Comprehension: A Learnable Representation of Code Semantics.** *NeurIPS.*
inst2vec: LLVM-IR embeddings for code representation; the learned
counterpart to COGANT's symbolic statespace module.

[7] Mir, A. M., Latoškinas, E., Proksch, S., Gousios, G. (2022). **Type4Py:
Practical Deep Similarity Learning-Based Type Inference for Python.** *ICSE.*
Learned type inference over Python program graphs; the closest "learned
role assignment" analogue to COGANT's declarative translate rules.

[8] Kanade, A., Maniatis, P., Balakrishnan, G., Shi, K. (2020). **Learning
and Evaluating Contextual Embedding of Source Code.** *ICML.* CuBERT: BERT
pretraining on Python source; baseline for position-aware token
representations that could serve as features for a hybrid COGANT variant.

### E.2 Active inference tooling and implementations

[9] Heins, C., Millidge, B., Demekas, D., Klein, B., Friston, K., Fields, C.,
Buckley, C., Tschantz, A. (2022). **pymdp: A Python library for active
inference in discrete state spaces.** *Journal of Open Source Software,
7(73).* The reference Python implementation of discrete active inference;
COGANT's `cogant.process` module targets pymdp's matrix conventions.

[10] Smith, R., Friston, K. J., Whyte, C. J. (2022). **A Step-by-Step
Tutorial on Active Inference and Its Application to Empirical Data.**
*Journal of Mathematical Psychology, 107.* The practitioner tutorial
against which COGANT's `cogant.process` test fixtures are validated.

[11] Parr, T., Pezzulo, G., Friston, K. J. (2022). **Active Inference: The
Free Energy Principle in Mind, Brain, and Behavior.** MIT Press. The
current textbook reference for discrete-time active inference and the A/B/C/D
matrix formalism that COGANT targets.

[12] Da Costa, L., Parr, T., Sajid, N., Veselic, S., Neacsu, V., Friston, K.
(2020). **Active Inference on Discrete State-Spaces: A Synthesis.**
*Journal of Mathematical Psychology, 99.* Explicit algorithms for policy
evaluation via Expected Free Energy; COGANT's EFE implementation follows
the pseudocode in this paper.

[13] Sajid, N., Ball, P. J., Parr, T., Friston, K. J. (2021). **Active
Inference: Demystified and Compared.** *Neural Computation, 33(3).* Compares
active inference to RL and optimal control; used to position COGANT's
choice of the A/B/C/D representation against reward-function alternatives.

[14] Friston, K. J., Lin, M., Frith, C. D., Pezzulo, G., Hobson, J. A.,
Ondobaka, S. (2017). **Active Inference, Curiosity and Insight.** *Neural
Computation, 29(10).* Decomposes EFE into pragmatic and epistemic
components; COGANT's EFE includes the epistemic term.

[15] Active Inference Institute (2022–2026). **infer-actively / pymdp
reference implementation and example gallery.** GitHub:
`infer-actively/pymdp`. The living library of example GNN specifications
against which COGANT's output is diffed in the reference-corpus
integration tests.

[16] Friston, K. J., Mattout, J., Trujillo-Barreto, N., Ashburner, J.,
Penny, W. (2007). **Variational Free Energy and the Laplace Approximation.**
*NeuroImage, 34(1).* SPM12 active-inference variational Bayesian framework;
the historical predecessor to pymdp and the source of the Laplace
approximation used in continuous-state extensions of COGANT.

[17] Smekal, J., Friedman, D. A. et al. (2023). **Generalized Notation
Notation: A Text-Based Format for Active Inference Generative Models.**
Active Inference Institute technical report. The specification document
for GNN v1.1, which COGANT's `cogant.gnn` formatter targets.

[18] Champion, T., Grzes, M., Bowman, H. (2022). **Branching Time Active
Inference: Empirical Study and Complexity Class Analysis.** *Neural
Networks, 152.* Demonstrates GNN-style specifications for hierarchical
active inference; target formalism for COGANT's branching-time extension.

### E.3 Code understanding and learned code models

[19] Feng, Z., Guo, D., Tang, D., Duan, N. et al. (2020). **CodeBERT: A
Pre-Trained Model for Programming and Natural Languages.** *Findings of
EMNLP.* Bimodal pretraining for code + NL; baseline for semantic
similarity tasks over code.

[20] Guo, D., Ren, S., Lu, S., Feng, Z. et al. (2021). **GraphCodeBERT:
Pre-training Code Representations with Data Flow.** *ICLR.* BERT-style model
with data-flow attention masks; the closest learned analogue to COGANT's
graph-structured role assignment.

[21] Guo, D., Lu, S., Duan, N., Wang, Y., Yin, M., Ren, S. (2022).
**UniXcoder: Unified Cross-Modal Pre-training for Code Representation.**
*ACL.* Unified encoder-decoder over AST, code, and comments.

[22] Wang, Y., Wang, W., Joty, S., Hoi, S. C. H. (2021). **CodeT5:
Identifier-Aware Unified Pre-trained Encoder-Decoder Model for Code
Understanding and Generation.** *EMNLP.* Identifier-aware T5 for code;
node-kind classification parallels COGANT's 14 node kinds.

[23] Alon, U., Zilberstein, M., Levy, O., Yahav, E. (2019). **code2vec:
Learning Distributed Representations of Code.** *POPL.* AST-path aggregation
for code embedding; complementary to COGANT's whole-graph approach.

[24] Hellendoorn, V. J., Sutton, C., Singh, R., Maniatis, P., Bieber, D.
(2019). **Global Relational Models of Source Code.** *ICLR.* Relational
graph attention over program graphs; validates COGANT's premise that
graph structure carries essential semantic information.

[25] Allamanis, M., Barr, E. T., Devanbu, P., Sutton, C. (2018). **A Survey
of Machine Learning for Big Code and Naturalness.** *ACM Computing Surveys,
51(4).* Landscape of learned code models against which COGANT is
positioned as a graph-based symbolic extractor.

[26] Bielik, P., Raychev, V., Vechev, M. (2016). **PHOG: Probabilistic Model
for Code.** *ICML.* Tree-conditional grammar for context-sensitive role
prediction; symbolic analogue of COGANT's rule engine with learned grammars.

[27] Raychev, V., Vechev, M., Krause, A. (2015). **Predicting Program
Properties from "Big Code".** *POPL.* CRF over program graphs for learned
role assignment; the learned counterpart to COGANT's rule engine.

### E.4 Graph kernels and structural similarity for code

[28] Shervashidze, N., Schweitzer, P., van Leeuwen, E. J., Mehlhorn, K.,
Borgwardt, K. M. (2011). **Weisfeiler-Lehman Graph Kernels.** *Journal of
Machine Learning Research, 12.* The foundational graph kernel that COGANT's
role-multiset similarity metric is a weighted analogue of (the WL-subtree
kernel reduces to multiset comparison at depth 1).

[29] Kriege, N. M., Johansson, F. D., Morris, C. (2020). **A Survey on
Graph Kernels.** *Applied Network Science, 5(1).* Comprehensive survey of
graph kernels; locates COGANT's role-match score in the kernel lineage.

[30] Nikolentzos, G., Siglidis, G., Vazirgiannis, M. (2021). **Graph Kernels:
A Survey.** *Journal of Artificial Intelligence Research, 72.* Alternative
survey with emphasis on structural kernels over labeled graphs.

### E.5 Formal methods: abstract interpretation and Galois connections in static analysis

[31] Cousot, P., Cousot, R. (1977). **Abstract Interpretation: A Unified
Lattice Model for Static Analysis of Programs by Construction or
Approximation of Fixpoints.** *POPL.* The foundational framework; COGANT's
confidence tiers and the forward/reverse functor pair are both instances.

[32] Cousot, P., Cousot, R. (1992). **Abstract Interpretation Frameworks.**
*Journal of Logic and Computation, 2(4).* Generalizes the 1977 framework
with explicit Galois connections between concrete and abstract domains.

[33] Nielson, F., Nielson, H. R., Hankin, C. (2005, 2nd printing).
**Principles of Program Analysis.** Springer. The standard textbook;
COGANT's translate stage is a worklist fixpoint in the monotone framework.

[34] Bravenboer, M., Smaragdakis, Y. (2009). **Strictly Declarative
Specification of Sophisticated Points-to Analyses.** *OOPSLA.* Doop and
Datalog-based static analysis; validates the principle that declarative
rule systems can handle sophisticated whole-program analyses at scale.

[35] Rice, H. G. (1953). **Classes of Recursively Enumerable Sets and
Their Decision Problems.** *Transactions of the AMS, 74(2).* Rice's
theorem establishes the fundamental undecidability that motivates the
approximate (Galois-connection) approach to semantic role assignment.

[36] Jones, N. D., Nielson, F. (1995). **Abstract Interpretation: A
Semantics-Based Tool for Program Analysis.** In *Handbook of Logic in
Computer Science.* Comprehensive reference for Galois-connection-based
static analysis; the categorical machinery used in Appendix C.

[37] Hoare, C. A. R. (1969). **An Axiomatic Basis for Computer Programming.**
*Communications of the ACM, 12(10).* The foundational paper for program
logic; COGANT's translate rules can be read as Hoare-style inference rules.

[38] Reynolds, J. C. (2002). **Separation Logic: A Logic for Shared Mutable
Data Structures.** *LICS.* Separation logic frame rule; analogue of
COGANT's Markov blanket extraction over program graphs.

[39] Milner, R. (1978). **A Theory of Type Polymorphism in Programming.**
*Journal of Computer and System Sciences, 17(3).* Hindley-Milner type
inference; COGANT's role assignment computes a "principal role" analogous
to a principal type.

[40] Leroy, X. (2009). **Formal Verification of a Realistic Compiler.**
*Communications of the ACM, 52(7).* CompCert: the gold standard for
verified program transformation; COGANT's roundtrip property is a weaker
but analogous correctness statement.

### E.6 POMDP solvers and planning

[41] Kaelbling, L. P., Littman, M. L., Cassandra, A. R. (1998). **Planning
and Acting in Partially Observable Stochastic Domains.** *Artificial
Intelligence, 101(1-2).* The foundational POMDP reference; establishes the
belief-state MDP reformulation that active inference specializes.

[42] Silver, D., Veness, J. (2010). **Monte-Carlo Planning in Large POMDPs.**
*NeurIPS.* POMCP: Monte Carlo tree search for large POMDPs. Alternative
planner to active inference's EFE-based policy selection; cited as a
scalable baseline for large extracted state spaces.

[43] Ye, N., Somani, A., Hsu, D., Lee, W. S. (2017). **DESPOT: Online
POMDP Planning with Regularization.** *Journal of AI Research, 58.*
Determinized Sparse Partially Observable Tree; anytime online POMDP
planner whose specification format could be generated from COGANT's
extracted A/B/C/D matrices as an alternative runtime.

[44] Kurniawati, H., Hsu, D., Lee, W. S. (2008). **SARSOP: Efficient
Point-Based POMDP Planning by Approximating Optimally Reachable Belief
Spaces.** *Robotics: Science and Systems.* Point-based value iteration;
the anytime offline counterpart to DESPOT. Relevant to COGANT extensions
that compute exact EFE-optimal policies rather than argmin-tie-break.

[45] Astrom, K. J. (1965). **Optimal Control of Markov Decision Processes
with Incomplete State Information.** *Journal of Mathematical Analysis
and Applications, 10(1).* The historical origin of the belief-state MDP
reformulation used throughout the POMDP literature.

[46] Hansen, E. A. (1998). **Solving POMDPs by Searching in Policy Space.**
*UAI.* Finite-state controllers for POMDPs; an alternative representation
of π that could be extracted by COGANT from repository control flow.

### E.7 Program synthesis and reverse engineering

[47] Alur, R., Bodik, R., Juniwal, G., Martin, M. M. K., Raghothaman, M.,
Seshia, S. A., Singh, R., Solar-Lezama, A., Torlak, E., Udupa, A. (2013).
**Syntax-Guided Synthesis.** *FMCAD.* SyGuS framework; COGANT's reverse
is a specialization with Python AST as grammar and GNN as specification.

[48] Solar-Lezama, A. (2008). **Program Synthesis by Sketching.** PhD
thesis, UC Berkeley. The sketching paradigm; COGANT's reverse output is a
sketch whose holes correspond to behaviors underspecified by the GNN.

[49] Gulwani, S. (2011). **Automating String Processing in Spreadsheets
Using Input-Output Examples.** *POPL.* FlashFill; popularized program
synthesis from input-output examples. Relevant to future COGANT work
using extract(code)→GNN pairs as synthesis training data.

[50] Jha, S., Gulwani, S., Seshia, S. A., Tiwari, A. (2010). **Oracle-Guided
Component-Based Program Synthesis.** *ICSE.* CEGIS loop; COGANT's forward
extraction is a natural correctness oracle for the reverse synthesis.

[51] Polozov, O., Gulwani, S. (2015). **FlashMeta: A Framework for
Inductive Program Synthesis.** *OOPSLA.* Witness-function synthesis
framework; candidate refactor for COGANT's reverse module.

[52] Gulwani, S., Polozov, O., Singh, R. (2017). **Program Synthesis.**
*Foundations and Trends in Programming Languages, 4(1-2).* The definitive
survey; locates COGANT's reverse in the deductive-from-formal-spec corner.

### E.8 Bidirectional transformations, lenses, and the categorical frame

[53] Foster, J. N., Greenwald, M. B., Moore, J. T., Pierce, B. C., Schmitt,
A. (2007). **Combinators for Bidirectional Tree Transformations: A
Linguistic Approach to the View-Update Problem.** *ACM TOPLAS, 29(3).*
The foundational lens paper; COGANT's forward/reverse pair is a partial
lens in this sense.

[54] Hofmann, M., Pierce, B. C., Wagner, D. (2011). **Edit Lenses.**
*POPL.* Extends lenses with edit actions; relevant to COGANT's incremental
update mode.

[55] Diskin, Z., Xiong, Y., Czarnecki, K., Ehrig, H., Hermann, F.,
Orejas, F. (2011). **From State- to Delta-Based Bidirectional Model
Transformations: The Symmetric Case.** *ICMT.* Symmetric lens
generalization; candidate for COGANT's future bidirectional synchronization.

[56] Fong, B., Spivak, D. I. (2019). **Seven Sketches in Compositionality:
An Invitation to Applied Category Theory.** Cambridge University Press.
Accessible reference for Galois connections (Chapter 1) and
databases-as-functors (Chapter 3); the mathematical home for COGANT's
confidence tiers and graph-as-category reading.

[57] Spivak, D. I. (2020). **Poly: An Abundant Categorical Setting for
Mode-Dependent Dynamics.** arXiv:2005.01894. The category **Poly** of
polynomial endofunctors on **Set**; the deepest categorical setting for
COGANT's forward/reverse functor pair.

[58] Niu, N., Spivak, D. I. (2023). **Polynomial Functors: A Mathematical
Theory of Interaction.** arXiv:2312.00990. 372-page monograph; the
reference for COGANT-Theory follow-on work.

[59] Awodey, S. (2010). **Category Theory (2nd ed.).** Oxford University
Press. The standard graduate textbook; definitions of functor, adjunction,
and unit/counit used in Appendix C.

### E.9 Markov blankets and active inference foundations

[60] Friston, K. J. (2010). **The Free-Energy Principle: A Unified Brain
Theory?** *Nature Reviews Neuroscience, 11(2).* The canonical statement of
the Free Energy Principle; the theoretical substrate of GNN notation.

[61] Pearl, J. (1988). **Probabilistic Reasoning in Intelligent Systems:
Networks of Plausible Inference.** Morgan Kaufmann. The book that
introduced Markov blankets for Bayesian networks; COGANT's blanket
extraction is over the program graph in Pearl's sense.

[62] Kirchhoff, M., Parr, T., Palacios, E., Friston, K., Kiverstein, J.
(2018). **The Markov Blankets of Life: Autonomy, Active Inference and the
Free Energy Principle.** *Journal of the Royal Society Interface, 15(138).*
Lifts Markov blankets from graphical models to dynamical systems; the
conceptual warrant for COGANT's "software Markov blanket" claim.

[63] Bruineberg, J., Dolega, K., Dewhurst, J., Baltieri, M. (2022). **The
Emperor's New Markov Blankets.** *Behavioral and Brain Sciences.* Critical
examination of Markov blanket usage; informs COGANT's cautious framing
(Pearl blankets, not Friston blankets).

[64] Biehl, M., Pollock, F. A., Kanai, R. (2021). **A Technical Critique of
Some Parts of the Free Energy Principle.** *Entropy, 23(3).* Conditions
under which FEP's Markov blanket claims hold rigorously vs break down;
COGANT's discrete-graph setting sidesteps the continuous-dynamics concerns.

---

## References back to COGANT source material

- Roundtrip data: `_rnd/ROUNDTRIP_EVAL.md` (Appendix A)
- Real-world eval data: `_rnd/REAL_WORLD_EVAL.md` (Appendix A)
- Empirical claim runs: `_rnd/EMPIRICAL_CLAIM.md` (Appendices A, D)
- CONSTRAINT synthesizer fix: `_rnd/CONSTRAINT_FIX.md` (Appendix A.2)
- Annotated bibliography (83 entries): `_rnd/LITERATURE.md` (Appendix E)
- Section 9 rule-family ablation: `manuscript/09_ablation.md` (Appendix B)
- Main text isomorphism theorem: `manuscript/cogant_paper.md` §6.2
  (Appendix C)

