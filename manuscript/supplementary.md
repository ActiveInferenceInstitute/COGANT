# Supplementary materials {#sec:supplementary-materials}

This appendix collects the detailed artifacts supporting the main text: per-role
roundtrip ε-isomorphism across all 23 evaluation targets (Appendix A), rule-family
ablation reconstructed from empirical data (Appendix B), a Galois-connection proof
sketch and ε-isomorphism theorem for the forward/reverse pair (Appendix C), the
discrete-POMDP active-inference mathematics of Appendix D (the inference loop summarized in
[`05_conclusion.md`](05_conclusion.md) and formalized in [`S04_appendix_inference_mathematics.md`](S04_appendix_inference_mathematics.md)),
a curated {{BIB_ENTRIES}}-entry bibliography across 9 research areas (Appendix E),
and a source-material cross-reference index (Appendix F).

Numerical data in Appendices A and B derive verbatim from four package evaluation
artefacts: `../cogant/docs/evaluation/ROUNDTRIP_EVAL.md`,
`../cogant/docs/evaluation/REAL_WORLD_EVAL.md`,
`../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`, and
`../cogant/docs/evaluation/CONSTRAINT_FIX.md`. Where the same measurement appears in
more than one source the value in `ROUNDTRIP_EVAL.md` (canonical post-wave-16 roundtrip
artefact, 23/23 ISOMORPHIC) takes precedence.

**MkDocs documentation map.** Tutorials, API/CLI reference, theory pages, and module indexes live under [`../cogant/docs/`](../cogant/docs/); start at [`../cogant/docs/index.md`](../cogant/docs/index.md) or the area listing in [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md).

**Recommended reading order:** Appendix A establishes the empirical ground truth
(per-fixture ε-scores and tier assignments); Appendix B decomposes those scores into
per-rule-family contributions on the minimal zoo fixture; Appendix C formalizes the
mathematical substrate (approximate Galois connection and ε-isomorphism theorem);
Appendix D details the discrete-POMDP active-inference computation that closes the
evaluation loop; Appendix E contextualizes the work within a curated bibliography;
Appendix F indexes the package source material cited throughout. Appendices A–B are
prerequisite for Appendix C; the others are independent.

---

## Supplemental files

- [`S01_appendix_roundtrip_epsilon.md`](S01_appendix_roundtrip_epsilon.md) — per-fixture
  roundtrip ε-isomorphism tables and validator scores across all 23 evaluation targets,
  with tier assignments (ISOMORPHIC / APPROXIMATE / DIVERGENT) and wave-14 vs. wave-16
  comparison.

- [`S02_appendix_ablation.md`](S02_appendix_ablation.md) — role-level rule-family ablation
  reconstructed on `zoo/01_simple_state` (the smallest ISOMORPHIC fixture), with per-role
  ε-deltas and failure-mode analysis.

- [`S03_appendix_galois_sketch.md`](S03_appendix_galois_sketch.md) — formal statement and
  proof sketch of the ε-approximate Galois connection between **Prog** and **GNN**
  categories, plus the ε-Isomorphism Theorem (Theorem C.2) and the ISOMORPHIC-threshold
  proposition (Proposition C.3).

- [`S04_appendix_inference_mathematics.md`](S04_appendix_inference_mathematics.md) — discrete-time
  POMDP formulation, variational free energy (VFE) functional and derivation, belief
  propagation equations, identity-case VFE = 0 analysis, observed VFE regimes, Bayesian
  D-update rule, and expected free energy (EFE) for policy selection.

- [`S05_appendix_extended_related_work.md`](S05_appendix_extended_related_work.md) — {{BIB_ENTRIES}}-entry
  curated bibliography across 9 topical clusters (E.1 program analysis → GNN,
  E.2 active inference tooling, E.3 code understanding and embeddings, E.4 formal methods,
  E.5 POMDP solvers, E.6 code summarization, E.7 program synthesis, E.8 lenses and
  categorical theory, E.9 Markov blankets and active inference foundations).

- [`S06_appendix_source_references.md`](S06_appendix_source_references.md) — index of
  external COGANT package documentation, evaluation artefacts, and manuscript tooling
  referenced throughout the main text and appendices.

---

## Notation supplement

- [`98_notation_supplement.md`](98_notation_supplement.md) — canonical reference for every
  mathematical symbol, acronym, and formal object used across the manuscript. Organised
  into nine groups: G.1 program graph symbols, G.2 translation engine, G.3 confidence
  model, G.4 A/B/C/D matrices, G.5 category-theory and Galois symbols, G.6 equation and
  theorem index, G.7 Active Inference roles and mapping kinds, G.8 node and edge kind
  enumerations, G.9 acronyms. Rendered after the appendices in the PDF (glossary discovery
  bucket, `98_` prefix).
