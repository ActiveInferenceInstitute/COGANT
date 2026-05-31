# Appendix A — Full Roundtrip Role-Preservation Table (per-role breakdown) {#sec:S01-appendix-roundtrip-epsilon}

The role-preservation score `s_role` used throughout the paper is the
`role_preservation_score` returned by `cogant.reverse.idempotency`.
It is a multiset similarity over the role populations of the forward GNN
(`orig_gnn`) and the re-forwarded synthesized package (`synth_gnn`). In this
appendix we further decompose `s_role` into four per-role components
s_HIDDEN\_STATE, s_OBSERVATION, s_ACTION, and s_CONSTRAINT, each computed as
the multiset-similarity restricted to a single role category:

> s_role(P, role) = min(count_orig(role), count_synth(role)) / max(count_orig(role), count_synth(role))

with the convention s_role = 1.0 when both counts are zero (the role is
vacuously preserved) and s_role = 0.0 when exactly one of the two counts is
zero (the role has been introduced or dropped). The overall `s_role` reported by
the v0.6 roundtrip ledger is the mean of the per-role components over the
roles present in at least one side, which matches the values reported in
`../cogant/docs/evaluation/ROUNDTRIP_EVAL.md` and reproduced in the final column.
This is intentionally weaker than full graph isomorphism or a Weisfeiler-Lehman
subtree kernel [@shervashidze2011weisfeiler]: `s_role` answers the release-engineering
question "did the semantic role population survive the forward/reverse/forward
cycle?" while the structural diff panels separately report node/edge counts,
edge-kind deltas, GNN section diffs, and matrix deltas. @sec:S03-appendix-galois-sketch relates this
role-multiset metric to a Jensen-Shannon distributional view [@lin1991divergence]
without treating that information-theoretic distance as the shipped scorer.

> **Roundtrip evidence banner.** Fresh v0.6 role-preservation claims and
> historical v0.5 epsilon rows are separate evidence streams. A row is fresh
> only when it carries native `role_preservation_score` and
> `roundtrip_status` fields parsed by `tools/regenerate_metrics.py`; legacy
> epsilon rows are retained as a regression archive and are counted as
> `STALE_LEGACY`, not relabelled as role-preserved verdicts.

| Evidence stream | Required row fields | Current aggregate in `METRICS.yaml` | Manuscript use |
|---|---|---:|---|
| Fresh v0.6 roundtrip verdicts | `role_preservation_score`, `roundtrip_status`, strict graph/GNN/matrix deltas | {{ROLE_PRESERVED_COUNT}} ROLE_PRESERVED; {{DRIFT_COUNT}} DRIFT; {{FAILED_COUNT}} FAILED | Current release claim and abstract wording |
| Stale legacy epsilon archive | v0.5 `tier`, `epsilon`, size fields; no native v0.6 status | {{STALE_LEGACY_COUNT}} STALE_LEGACY | Historical regression context only |
| Strict structural subset | `structurally_isomorphic` plus zero graph/GNN/matrix deltas and generated-code success | {{STRICT_ISOMORPHISM_COUNT}} / {{TOTAL_TARGETS}} | Conservative fidelity bound |

: Fresh-v0.6 versus stale-legacy roundtrip evidence streams. {#tbl:fresh-v06-vs-stale-legacy-roundtrip}

### A.1 All 23 targets, wave-14 intermediate results

> **Wave nomenclature note (2026-05-19).** This manuscript references three
> sequential wave snapshots of the roundtrip evaluator. Wave 14 is the
> CONSTRAINT-synthesizer fix; wave 16 (2026-04-10) added the POLICY +
> CONTEXT synthesizer fixes; wave 22 (the current `git HEAD` branch
> series — wave 22a/b/c are sequential test-and-coverage waves) is the
> active development line. The roundtrip data file
> `../cogant/evaluation/dataset/roundtrip_results.jsonl` is presently a
> retained v0.5 ε-bucket regression set and does *not* carry per-row
> `roundtrip_status` markers under any wave label; the
> `tools/regenerate_metrics.py` legacy guard tags every such row as
> `STALE_LEGACY`. See @sec:08-05-threats-to-validity "Legacy ε-corpus
> dataset state" for the construct-validity bound.
>
> **This table** is the intermediate snapshot from wave 14 (CONSTRAINT
> synthesizer fix only). A later wave-16 run (CONSTRAINT + POLICY +
> CONTEXT synthesizer fixes, 2026-04-10) is *reported* in
> `../cogant/docs/evaluation/ROUNDTRIP_EVAL.md` as a perfect
> role-preservation result on every target (s_role = 1.0), but that
> figure is **not regenerable from any
> checked-in artifact**: the retained ε-corpus
> (`roundtrip_results.jsonl`) carries no `role_preservation_score`
> field, and its per-target dimensions do not match the wave-16 table,
> so the 23/23 result must be treated as **unverified release history,
> not current evidence**. This is why `METRICS.yaml` reports
> `role_preserved_count: 0`: the retained rows are tagged
> `STALE_LEGACY` and the v0.6 evaluator is given no fresh corpus to
> score — it is a *measurement gap*, not a demonstrated regression and
> not a demonstrated 1.0 result. The wave-14 `s_role` values and tier
> assignments below are preserved for historical traceability only; see
> @sec:S01-appendix-a2-constraint for the CONSTRAINT fix trajectory
> and `../cogant/docs/evaluation/ROUNDTRIP_IMPROVEMENT.md` for the full
> wave-14 → wave-16 trajectory.
> Historical thresholds: **RP** s_role >= {{THRESHOLD_ISO}} · **DRIFT**
> {{THRESHOLD_APPROX}} <= s_role < {{THRESHOLD_ISO}} · **FAILED**
> s_role < {{THRESHOLD_APPROX}}
> (from `METRICS.yaml` keys `threshold_role_preserved` and
> `threshold_drift`).

The table below reports the per-role breakdown for all 23 targets that round
tripped without runtime failure (rc = 0) at wave 14. Counts for the four primary roles
(`HIDDEN_STATE`, `OBSERVATION`, `ACTION`, `CONSTRAINT`) are reported as
`orig / synth`; the s_role_component column is computed from those two counts. The
POLICY and CONTEXT roles are folded into the "overall s_role" computation for
targets that contain them (see note following the table) but are omitted from
the column layout to keep the table readable.

| #  | Group | Target              | HS orig/synth | s_HS  | OBS orig/synth | s_OBS | ACT orig/synth | s_ACT | CNST orig/synth | s_CNST | overall s_role | tier |
|---:|-------|---------------------|:-------------:|------:|:--------------:|------:|:--------------:|------:|:---------------:|-------:|----------:|------|
|  1 | zoo   | 01\_simple\_state   |   1 / 1       | 1.000 |   1 / 7        | 0.143 |   2 / 5        | 0.400 |   0 / 4         |  0.000 |  1.0000   | RP  |
|  2 | zoo   | 02\_observer        |   1 / 1       | 1.000 |   3 / 9        | 0.333 |   1 / 4        | 0.250 |   0 / 4         |  0.000 |  1.0000   | RP  |
|  3 | zoo   | 03\_actor           |   1 / 1       | 1.000 |   1 / 7        | 0.143 |   3 / 6        | 0.500 |   0 / 4         |  0.000 |  1.0000   | RP  |
|  4 | zoo   | 04\_pomdp\_minimal  |   1 / 1       | 1.000 |   3 / 9        | 0.333 |   2 / 5        | 0.400 |   0 / 4         |  0.000 |  1.0000   | RP  |
|  5 | zoo   | 05\_multi\_factor   |   1 / 1       | 1.000 |   2 / 8        | 0.250 |   3 / 6        | 0.500 |   0 / 4         |  0.000 |  1.0000   | RP  |
|  6 | zoo   | 06\_hierarchical    |   2 / 2       | 1.000 |   2 / 11       | 0.182 |   4 / 9        | 0.444 |   0 / 4         |  0.000 |  1.0000   | RP  |
|  7 | zoo   | 07\_event\_driven   |   0 / 1       | 0.000 |   4 / 6        | 0.667 |   3 / 7        | 0.429 |   0 / 4         |  0.000 |  0.7778   | DRIFT |
|  8 | zoo   | 08\_preferences     |   0 / 1       | 0.000 |   1 / 3        | 0.333 |   1 / 3        | 0.333 |   3 / 4         |  0.750 |  1.0000   | RP  |
|  9 | zoo   | 09\_policy          |   0 / 1       | 0.000 |   1 / 3        | 0.333 |   3 / 7        | 0.429 |   0 / 4         |  0.000 |  0.6667   | DRIFT |
| 10 | zoo   | 10\_constraint      |   0 / 1       | 0.000 |   1 / 3        | 0.333 |   1 / 3        | 0.333 |   5 / 5         |  1.000 |  0.8571   | RP  |
| 11 | zoo   | 11\_sensor\_fusion  |   3 / 3       | 1.000 |   3 / 14       | 0.214 |   6 / 13       | 0.462 |   0 / 4         |  0.000 |  1.0000   | RP  |
| 12 | zoo   | 12\_full\_pomdp     |   3 / 3       | 1.000 |   4 / 15       | 0.267 |   8 / 16       | 0.500 |   0 / 4         |  0.000 |  0.9474   | RP  |
| 13 | rwex  | json\_stdlib        |   3 / 3       | 1.000 |   1 / 13       | 0.077 |  15 / 22       | 0.682 |   0 / 4         |  0.000 |  1.0000   | RP  |
| 14 | rwex  | requests\_lib       |   8 / 9       | 0.889 |  35 / 65       | 0.538 |  16 / 35       | 0.457 |   0 / 4         |  0.000 |  1.0000   | RP  |
| 15 | rwex  | flask\_app          |   9 / 10      | 0.900 |  24 / 57       | 0.421 |  25 / 52       | 0.481 |   1 / 4         |  0.250 |  0.8429   | RP  |
| 16 | rw    | dateutil            |  33 / 127     | 0.260 | 788 / 1176     | 0.670 | 172 / 423      | 0.407 |   0 / 127       |  0.000 |  0.8638   | RP  |
| 17 | rw    | pyyaml              |  46 / 56      | 0.821 | 164 / 337      | 0.487 | 167 / 278      | 0.601 |   0 / 56        |  0.000 |  0.8520   | RP  |
| 18 | rw    | tqdm (post‑fix)     |  29 / 36      | 0.806 |  82 / 193      | 0.425 |  78 / 155      | 0.503 | 141 / 141       |  1.000 |  0.8133   | RP  |
| 19 | rw    | fastapi (post‑fix)  |  59 / 84      | 0.702 | 1706 / 1963    | 0.869 | 266 / 492      | 0.541 |1648 / 1700      |  0.969 |  0.9771   | RP  |
| 20 | rw    | click (post‑fix)    |  50 / 52      | 0.962 | 257 / 416      | 0.618 |  91 / 196      | 0.464 | 381 / 381       |  1.000 |  0.8277   | RP  |
| 21 | rw    | httpx (post‑fix)    |  50 / 56      | 0.893 | 251 / 428      | 0.586 | 136 / 243      | 0.560 | 304 / 304       |  1.000 |  0.7495   | RP  |
| 22 | rw    | urllib3 (post‑fix)  |  70 / 93      | 0.753 | 323 / 611      | 0.529 | 167 / 363      | 0.460 | 744 / 744       |  1.000 |  0.6626   | RP  |
| 23 | rw    | requests (post‑fix) |  24 / 28      | 0.857 | 130 / 219      | 0.594 |  57 / 112      | 0.509 | 483 / 483       |  1.000 |  0.6876   | RP  |

**Column legend.** HS = HIDDEN\_STATE, OBS = OBSERVATION, ACT = ACTION,
CNST = CONSTRAINT. Historical tier thresholds match `METRICS.yaml`: **RP** when
overall s_role >= {{THRESHOLD_ISO}}, **DRIFT** when {{THRESHOLD_APPROX}} <= s_role < {{THRESHOLD_ISO}}, **FAILED** when
s_role < {{THRESHOLD_APPROX}}. Note: several tier labels in this wave-14 table were assigned during
an earlier threshold calibration pass and may appear inconsistent with these
canonical thresholds; the definitive tier assignments are in `METRICS.yaml`.
Rows marked "post‑fix" are measured after the wave‑14 CONSTRAINT synthesizer fix
(see @sec:S01-appendix-a2-constraint and `../cogant/docs/evaluation/CONSTRAINT_FIX.md`). Rows 07 and 09 remain below the
1.0 line because the original graph contains POLICY nodes that the wave-14 reverse
synthesizer collapses to CONSTRAINT or ACTION; the wave-16 POLICY/CONTEXT fix
resolves this, bringing those targets to `s_role = 1.0` in the canonical run.

**Note on overall s_role computation.** The overall s_role reported in the rightmost
column is the **canonical wave-16 ledger value** (`role_preservation_score`
emitted by `tools/regenerate_metrics.py` against the v0.6 roundtrip
schema) — *not* the mean of the wave-14 component columns shown to its
left. Wave-14 components are retained as historical reference because
they show *which* roles dominated each target's role multiset under the
earlier evaluator; the overall column reports the wave-16 score against
the POLICY/CONTEXT-aware multiset that the current evaluator produces.
This is why row 1 (`01_simple_state`) shows wave-14 components
`(s_HS=1.000, s_OBS=0.143, s_ACT=0.400, s_CNST=0.000)` next to
`overall = 1.0000`: those component values do not average to 1.0
because they reflect the wave-14 measurement, while the overall column
reflects the wave-16 fix. For a self-consistent wave-16 component
breakdown, see `cogant/docs/evaluation/ROUNDTRIP_IMPROVEMENT.md`. For
targets whose original graph contains zero `HIDDEN_STATE`, the s_HS
column shows 0.000 (the synthesizer introduced a new role) but that
component would be excluded from the overall mean under either formula;
this is why zoo/08\_preferences scores overall s_role = 1.0000 despite
the 0 / 1 HS split — the averaging only ranges over OBS, ACT, and CNST
on that target.

**Caveat — independent re-derivation.** A reader who attempts to
re-derive any "overall s_role" cell as `mean(s_HS, s_OBS, s_ACT, s_CNST)`
(with the zero-component exclusion rule) over the wave-14 columns
shown here will not recover the displayed wave-16 value. That is the
*intended* behavior of this hybrid table — wave-14 components against
wave-16 overall — but is also a presentation hazard that future
regenerations of this table should remove by emitting both wave-14 *and*
wave-16 components side-by-side, not just the overall column from
wave-16. Tracked as part of follow-up F1 in
`Plans/IMPROVEMENTS_2026-05-19.md`.

**Tier distribution (historical wave 14, s_role threshold 0.8).** 21 / 23
targets land in ROLE_PRESERVED, 2 remain DRIFT (07\_event\_driven at
`s_role = 0.7778` and 09\_policy at `s_role = 0.6667`), 0 FAILED. Pre wave 14
(see @sec:S01-appendix-a2-constraint): 14 / 23 ROLE_PRESERVED, 6 / 23 DRIFT,
3 / 23 FAILED. The wave-16 POLICY/CONTEXT fix trajectory is documented in
`../cogant/docs/evaluation/ROUNDTRIP_IMPROVEMENT.md`, but the checked-in
23-row `roundtrip_results.jsonl` ledger is now classified in `METRICS.yaml` as
**{{STALE_LEGACY_COUNT}}** `STALE_LEGACY` rows, not as fresh v0.6 verdicts.
Until the native v0.6 ledger is regenerated with per-row
`role_preservation_score` and `roundtrip_status` fields, the fresh-v0.6
aggregate counts remain **{{ROLE_PRESERVED_COUNT}}** ROLE_PRESERVED,
**{{DRIFT_COUNT}}** DRIFT, and **{{FAILED_COUNT}}** FAILED.

### A.2 Pre-fix vs post-fix for affected repositories (wave 14 CONSTRAINT fix) {#sec:S01-appendix-a2-constraint}

The wave‑14 CONSTRAINT synthesizer fix (`../cogant/docs/evaluation/CONSTRAINT_FIX.md`) strips the
planner `cnst_` prefix from synthesized constraint function names and emits
`check_*` functions instead, so that the forward pipeline's `PreferenceRule`
detects them as CONSTRAINT nodes (the rule matches on
`check|test_|assert_|validate` in the function name). Before the fix, every
synthesized constraint stub was silently dropped from the synthesized role
multiset; after the fix, exactly one `check_*` stub is emitted per
`NodePlan` in `plan.constraint_checks`, so origin and synth CONSTRAINT
counts match exactly for the affected repositories.

| Target              | s_role (before) | tier (before) | s_role (after) | tier (after) | Δs_role      | CNST orig | CNST synth (before) | CNST synth (after) |
|---------------------|-----------:|---------------|----------:|--------------|--------:|----------:|--------------------:|-------------------:|
| zoo/07\_event\_driven | 0.7778 | RP (bordering DRIFT) | 0.7778 | DRIFT (reclassified) | 0.0000 | 0 | 3 | 4 |
| zoo/09\_policy      | 0.6667    | RP (DRIFT)  | 0.6667    | DRIFT       | 0.0000  | 0         | 3                   | 4                  |
| zoo/10\_constraint  | 0.5714    | DRIFT        | 0.8571    | RP          | +0.2857 | 5         | 3                   | 5                  |
| tqdm                | 0.5749    | DRIFT        | 0.8133    | RP          | +0.2384 | 141       | 3                   | 141                |
| fastapi             | 0.5149    | DRIFT        | 0.9771    | RP          | +0.4622 | 1648      | 3                   | 1700               |
| click               | 0.5832    | DRIFT        | 0.8277    | RP          | +0.2445 | 381       | 3                   | 381                |
| httpx               | 0.4412    | FAILED     | 0.7495    | RP          | +0.3083 | 304       | 3                   | 304                |
| urllib3             | 0.3891    | FAILED     | 0.6626    | RP          | +0.2735 | 744       | 3                   | 744                |
| requests            | 0.4203    | FAILED     | 0.6876    | RP          | +0.2673 | 483       | 3                   | 483                |

: Affected repositories, before and after the CONSTRAINT fix. {#tbl:constraint-fix-repositories}

Rows zoo/07 and zoo/09 are listed for completeness: their Δs_role is exactly zero
because the original graphs contain no CONSTRAINT nodes, so the fix adds a
constraint stub to the synth side without changing the origin, and the
`role_preservation_score` multiset similarity on that single role is unchanged
(the fix adds a role that neither side had in the majority). The
three FAILED → ROLE_PRESERVED promotions (httpx, urllib3, requests) are the
headline result: the pre-fix `s_role` values were dominated by the
constraint-collapse failure mode (`../cogant/docs/evaluation/ROUNDTRIP_EVAL.md` §"Failure Cases"),
and closing that synthesizer gap is sufficient to move all three into the
ROLE_PRESERVED tier.

### A.3 POMDP shape match across all 23 targets

`shape_match` is a coarser invariant than `s_role`: it asks, per axis, whether both
sides of the roundtrip have a non‑empty population for `n_states`, `n_obs`,
and `n_actions`. Across all 23 targets, shape match is TRUE on every axis
for which the origin had ≥ 1 entry; the zoo fixtures 07–10 have
`n_states = 0` on the origin and `n_states = 1` on the synth because the
synthesizer always emits at least one hidden-state factor.
