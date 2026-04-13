# Wave 19 — Coherence Narrative Audit

**Agent:** `coherence-narrative-agent`
**Date:** 2026-04-10
**Scope:** `docs/` and `docs/rnd/` (NOT `manuscript/`)
**Canonical source:** `cogant/evaluation/METRICS.yaml` (`stage_count = 8`, `translation_rules = 19`, `isomorphic_count = 23`, `mean_epsilon = 1.0`)

## Canonical Narrative Enforced

1. COGANT is a **Galois connection** (ε-bounded adjunction) between `ProgramGraph` and `GNNModel` lattices.
2. Forward pipeline is **8 stages**: `ingest → parse → graph → translate → statespace → markov → gnn → reverse`.
3. Translation uses **19 rules**.
4. GNN = **Generalized Notation Notation** (Active Inference Institute); **not** graph neural networks.
5. ε metric: `ε = |roles_preserved| / |roles_original|`. Perfect roundtrip at **ε = 1.0**; ISOMORPHIC threshold **ε ≥ 0.8**; APPROXIMATE `0.5 ≤ ε < 0.8`; DIVERGENT `ε < 0.5`.
6. Current benchmark (per METRICS.yaml): **23/23 ISOMORPHIC, mean ε = 1.0**.
7. Markov blanket: internal (HIDDEN_STATE), sensory (OBSERVATION), active (ACTION), external (CONTEXT).

## Contradictions Found and Fixed

### A. "GNN" misrendered as "Graph Neural Network"

| File | Before | After |
|---|---|---|
| `docs/reference/render_site.md` | "Implement GNN translation - Add actual graph neural network logic" | Clarified as Generalized Notation Notation; explicit "not graph neural networks" disambiguation |
| `docs/architecture/use_finalmappings_for_gnn_training.md` | Title & body implied neural-network training integration | Retitled "GNN export", added prominent "not graph neural networks" note, rewrote integration list to describe GNN package emission |
| `docs/architecture/cogant_engine_implementation_summary.md` | "Ready for GNN training" | "Consumed by the GNN (Generalized Notation Notation) package emitter; not graph-neural-network training" |
| `docs/faq.md` | Q28 answer implied graph-neural-network training was the intended pipeline | Clarified that GNN here is AII notation; downstream graph-neural-network consumption is a representational coincidence, not a claim |

Already-consistent files (no edit needed): `docs/cli/overview.md`, `docs/concepts/gnn.md`, `docs/reference/cogant_schemas_reference.md`, `docs/reference/introduction.md`, `docs/reference/glossary.md`, `docs/roadmap/cogant_benchmarks.md`, `docs/roadmap/changelog.md`, `docs/evaluation/SCOPING_REPORT.md`, `docs/evaluation/LITERATURE.md` (§ on AII), `docs/theory/gnn_format.md`. The `LITERATURE.md:305` mention of graph neural networks is a legitimate citation of prior work and was left intact.

### B. Wrong pipeline-stage counts (legacy 9/10-stage layouts)

| File | Before | After |
|---|---|---|
| `docs/reference/pipeline_stages.md` | Full 10-stage description (`ingest → static → normalize → graph → dynamic → translate → statespace → process → export → validate`) | Rewritten as 8-stage DAG matching METRICS.yaml; added canonical-source note + legacy-layout explanation |
| `docs/architecture/concurrency_parallelism.md` | Referenced Stage 2/3/5/6/9 of the legacy 10-stage layout | Rewritten to reference current 8-stage layout (Parse, Graph, Translate, GNN, Reverse) and linked to METRICS.yaml |
| `docs/validation/cogant_implementation_verification_report.md` | "PipelineConfig - 9-stage configuration" / "All 9 stages implemented" | Updated to "8-stage configuration" with the canonical stage list inline |
| `docs/evaluation/EMPIRICAL_CLAIM.md` | "10 stages: ingest → static → normalize → graph → translate → statespace → process → export → validate" | "8 stages: ingest → parse → graph → translate → statespace → markov → gnn → reverse (canonical source `cogant/evaluation/METRICS.yaml`)" |
| `docs/evaluation/V1.0_READINESS.md` | "8/8 real-world repos pass; 10 stages" | Replaced with 8-stage DAG listing + METRICS.yaml citation |
| `docs/evaluation/SCOPING_REPORT.md` | ASCII diagram "10-stage pipeline" with legacy stage names | Replaced with 8-stage listing matching METRICS.yaml |
| `docs/evaluation/FINAL_REPORT.md` | Evidence chain "10 pipeline stages: all status=success" | "8 pipeline stages (canonical list in METRICS.yaml)" |

Legacy historical entries left intact in `docs/changelog.md` (per-release sections v0.2.0/v0.3.0/v0.4.0) and `docs/evaluation/R&D_LOG.md` (wave-by-wave log) — these are append-only historical records and accurately describe what was true at the time of the referenced wave.

### C. Wrong translation-rule counts

| File | Before | After |
|---|---|---|
| `docs/architecture/cogant_engine_implementation_summary.md` | "Apply 8 rules for semantic patterns" | "Apply 19 translation rules (fixpoint) for semantic role assignment" |
| `docs/notebooks/05_custom_rules.ipynb` (cell 0) | "~18 built-in translation rules" | "19 built-in translation rules (canonical count: METRICS.yaml → pipeline.translation_rules)" |
| `docs/notebooks/10_rule_dsl.ipynb` (cell 2f9a6c43) | "alongside ~18 built-ins" | "alongside the 19 built-in translation rules (canonical count: METRICS.yaml)" |

The `docs/evaluation/ISOMORPHISM_THEOREM.md:197` "v0.1.0 rule table contains K = 27 rules" is explicitly scoped to v0.1.0 and is a historical mathematical computation; left intact.

### D. Wrong ε-benchmark numbers (14/23, 19/23, 0.5/0.7 thresholds)

| File | Before | After |
|---|---|---|
| `docs/evaluation/FINAL_REPORT.md` row 57 | "14/23 ISOMORPHIC, 6/23 APPROXIMATE, 3/23 DIVERGENT (pre-wave-16 benchmark)" | "23/23 ISOMORPHIC, mean ε = 1.0 (post-wave-16; canonical source METRICS.yaml). Pre-wave-16 baseline preserved as context." |
| `docs/evaluation/FINAL_REPORT.md` §4 header | "Pre-wave-16 benchmark (JSONL ground truth, current) - 14/23" | Replaced with "Current benchmark (post-wave-16, per METRICS.yaml): 23/23 ISOMORPHIC, mean ε = 1.0"; historical rows preserved |
| `docs/evaluation/FINAL_REPORT.md` line 76 | "is_isomorphic=true (threshold 0.5)" | "ISOMORPHIC threshold ε ≥ 0.8; perfect roundtrip at ε = 1.0" |
| `docs/evaluation/EMPIRICAL_CLAIM.md` line 35 | "is_isomorphic: true (threshold 0.5)" | "is_isomorphic: true (ISOMORPHIC threshold ε ≥ 0.8; see METRICS.yaml)" |
| `docs/evaluation/EMPIRICAL_CLAIM.md` line 113 | "is_isomorphic=true at threshold 0.5" | "is_isomorphic=true at the canonical ISOMORPHIC threshold (ε ≥ 0.8)" |
| `docs/evaluation/ROUNDTRIP_EVAL.md` line 70 | "is_isomorphic uses default threshold 0.5" | Rewritten to cite METRICS.yaml canonical thresholds (0.8 / 0.5) and explain that legacy drivers may use a loose 0.5 gate but this report uses the stricter ε ≥ 0.8 tier |
| `docs/evaluation/CROSS_LANG_ROUNDTRIP.md` line 95 | "PERFECT (ε = 0)" — contradicted the role-preservation convention | "ISOMORPHIC (ε = 1.0 — every original role preserved)"; added canonical-convention note |
| `docs/concepts/roundtrip.md` lines 71–86 | "epsilon = distance(GNN_original, GNN_roundtrip) ... A perfect roundtrip has epsilon = 0" | Rewrote with canonical ε = roles_preserved / roles_original definition, perfect ε = 1.0, ISOMORPHIC ≥ 0.8, + legacy-note pointer |
| `docs/reference/glossary.md` canonical-conventions bullet | "ε is the fidelity score — a count of ambiguous nodes" | Rewrote as role-preservation ratio in [0, 1], ε = 1.0 perfect |
| `docs/reference/glossary.md` ε entry | "ε counts the ambiguous nodes whose role assignment is not preserved. ε is not an accuracy or similarity; it is a structural distance" | Rewrote as role-preservation fidelity ratio with canonical thresholds and METRICS.yaml citation; preserved the pre-wave-14 "error" formulation as theoretical context |
| `docs/notebooks/04_roundtrip.ipynb` cell 62946a58 | Used composite-score convention (threshold 0.7, ε = 1 − total_score) without explaining the divergence from the canonical ε | Added explicit conventions note distinguishing the notebook's composite score (threshold 0.7) from the canonical role-preservation ε (threshold 0.8, from METRICS.yaml) |

`docs/changelog.md:46` / `:55` left intact — inside historical v0.4.0 release notes, where "19/23" and "14/23 → 19/23" are accurate for the v0.4.0 wave-9 / wave-14 timelines.

### E. ε = 0 ↔ ε = 1 convention contradictions

The canonical project-wide convention is **ε = 1.0 is a perfect roundtrip**. The `ISOMORPHISM_THEOREM.md` pre-proof uses a complementary ε_max-is-exact-at-0 formulation. This is genuine theoretical complexity (the theorem is a separate formalization), so:

- `docs/concepts/roundtrip.md` and `docs/reference/glossary.md` were rewritten to the canonical ε = 1.0 = perfect convention, with an explicit note pointing at ISOMORPHISM_THEOREM.md §4 as the legacy "error" formulation for theoretical context.
- `docs/evaluation/ISOMORPHISM_THEOREM.md` itself was **not** rewritten — it is an intentionally standalone mathematical artifact and its ε_max definition is internally consistent within the proof.
- `docs/evaluation/CROSS_LANG_ROUNDTRIP.md:95` (`PERFECT (ε = 0)`) was fixed because it directly contradicted the line above it on the same page (`|R1 ∩ R2| / |R1| = 6/6 = 1.0000 (PERFECT)`).

## Files NOT Edited (left intentionally)

- `docs/manuscript/**` — out of scope per task binding.
- `docs/evaluation/ISOMORPHISM_THEOREM.md` — internally consistent mathematical artifact with its own ε convention.
- `docs/evaluation/R&D_LOG.md` — append-only historical log; wave-by-wave entries reference the numbers accurate at each wave.
- `docs/changelog.md` historical v0.2.0/v0.3.0/v0.4.0 sections — version release notes for prior versions.
- `docs/evaluation/LITERATURE.md:305` — legitimate citation of prior graph-neural-network work.
- `docs/rnd/*.md` — scanned; no narrative markers found.

## Canonical Source Links Added

Several edits now explicitly cite `cogant/evaluation/METRICS.yaml` as the canonical source for stage count, translation-rule count, roundtrip benchmark, and ε thresholds. This reduces future drift by centralizing the load-bearing numbers in one place.
