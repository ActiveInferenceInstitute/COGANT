# Supplementary materials {#sec:supplementary-materials}

This appendix collects the detailed artifacts supporting the main text: the
historical per-role roundtrip ledger across all 23 evaluation targets
(@sec:S01-appendix-roundtrip-epsilon), measured rule-family ablation
(@sec:S02-appendix-ablation), a Galois-style comparison
and scoped role-preservation invariant for the forward/reverse pair (@sec:S03-appendix-galois-sketch), the
discrete-POMDP active-inference mathematics of @sec:S04-appendix-inference-mathematics (the inference loop summarized in
@sec:10-conclusion and formalized in @sec:S04-appendix-inference-mathematics),
a curated {{BIB_ENTRIES}}-entry bibliography across 9 research areas (@sec:S05-appendix-extended-related-work),
and a source-material cross-reference index (@sec:S06-appendix-source-references).

Numerical data in @sec:S01-appendix-roundtrip-epsilon and @sec:S02-appendix-ablation derive verbatim from four package evaluation
artefacts: `../cogant/docs/evaluation/ROUNDTRIP_EVAL.md`,
`../cogant/docs/evaluation/REAL_WORLD_EVAL.md`,
`../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`, and
`../cogant/docs/evaluation/CONSTRAINT_FIX.md`. Where the same measurement appears in
more than one source the value in `ROUNDTRIP_EVAL.md` takes precedence as a
historical role-preservation artifact; the current `METRICS.yaml` aggregates are sourced from the native v0.6
ledger (`role_preservation_score_source: {{ROLE_PRESERVATION_SCORE_SOURCE}}`); any retained legacy rows are marked `STALE_LEGACY` and excluded.

**Recommended reading order:** @sec:S01-appendix-roundtrip-epsilon establishes the empirical ground truth
(per-fixture `s_role` scores and tier assignments); @sec:S02-appendix-ablation decomposes those scores into
per-rule-family contributions on the minimal zoo fixture; @sec:S03-appendix-galois-sketch formalizes the
mathematical substrate (approximate preorder-quotient comparison and bounded role-preservation invariant);
@sec:S04-appendix-inference-mathematics details the discrete-POMDP active-inference computation that closes the
evaluation loop; @sec:S05-appendix-extended-related-work contextualizes the work within a curated bibliography;
@sec:S06-appendix-source-references indexes the package source material cited throughout. @sec:S01-appendix-roundtrip-epsilon and @sec:S02-appendix-ablation are
prerequisites for @sec:S03-appendix-galois-sketch; the others are independent.

---

## Supplemental sections

- @sec:S01-appendix-roundtrip-epsilon provides per-fixture historical roundtrip role-preservation tables and validator scores across all 23 evaluation targets, with `STRUCTURALLY_ISOMORPHIC` / `ROLE_PRESERVED` / `DRIFT` / `FAILED` status vocabulary and explicitly historical wave-14 / wave-16 comparison.
- @sec:S02-appendix-ablation gives the measured role-level rule-family ablation on `zoo/01_simple_state`, with per-role deltas and failure-mode analysis.
- @sec:S03-appendix-galois-sketch gives the conjectural, scoped statement and argument sketch for an ε-approximate Galois-style comparison between **Prog** and **GNN** preorder quotients, plus @sec:thm-bounded-role-preservation-gap and @sec:prop-role-preservation-threshold.
- @sec:S04-appendix-inference-mathematics gives the discrete-time POMDP formulation, variational free energy (VFE) functional and derivation, belief-propagation equations, identity-case VFE = 0 analysis, observed VFE regimes, Bayesian D-update rule, and expected free energy (EFE) for policy selection.
- @sec:S05-appendix-extended-related-work gives the {{BIB_ENTRIES}}-entry curated bibliography across 9 topical clusters: program analysis to GNN, active inference tooling, code understanding and embeddings, formal methods, POMDP solvers, code summarization, program synthesis, lenses and categorical theory, and Markov blankets / active-inference foundations.
- @sec:S06-appendix-source-references indexes external COGANT package documentation, evaluation artefacts, and manuscript tooling referenced throughout the main text and appendices.

---

## Notation supplement

- @sec:98-notation-supplement is the canonical reference for manuscript-level mathematical symbols, acronyms, and formal objects. It is organised into program-graph symbols, translation-engine symbols, confidence-model symbols, A/B/C/D matrices, category-theory and Galois symbols, equation and scoped-claim index, Active Inference roles and mapping kinds, node and edge kind enumerations, and acronyms.
