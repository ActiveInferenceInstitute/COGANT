# Supplementary materials {#sec:supplementary-materials}

This appendix collects the detailed artifacts supporting the main text: the
current native roundtrip ledger across all {{TOTAL_TARGETS}} evaluation targets
(@sec:S01-appendix-roundtrip-epsilon), measured rule-family ablation
(@sec:S02-appendix-ablation), a Galois-style comparison and scoped
role-preservation invariant for the forward/reverse pair
(@sec:S03-appendix-galois-sketch), the discrete-POMDP active-inference
mathematics of @sec:S04-appendix-inference-mathematics, a curated
{{BIB_ENTRIES}}-entry bibliography across research areas
(@sec:S05-appendix-extended-related-work), and a source-material
cross-reference index (@sec:S06-appendix-source-references).

Numerical data in @sec:S01-appendix-roundtrip-epsilon and
@sec:S02-appendix-ablation derive from package evaluation artifacts:
`../cogant/evaluation/METRICS.yaml`,
`../cogant/evaluation/dataset/roundtrip_results.jsonl`,
`../cogant/docs/evaluation/ROUNDTRIP_EVAL.md`,
`../cogant/docs/evaluation/REAL_WORLD_EVAL.md`,
`../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`, and
`../cogant/docs/evaluation/CONSTRAINT_FIX.md`. When duplicate values appear,
`METRICS.yaml` governs roundtrip aggregate claims and measured fixture files
govern their own fixture-specific tables.

This appendix is an index and not a new evidence source. Cross-reference and
claim-scope checks should be run with `uv run python tools/audit_manuscript_crossrefs.py`
and `uv run python tools/audit_manuscript_claim_scope.py`; those validators
bound the appendix links but do not independently remeasure the package.

**Recommended reading order:** @sec:S01-appendix-roundtrip-epsilon establishes
the empirical ground truth for roundtrip status; @sec:S02-appendix-ablation
decomposes those scores into per-rule-family contributions on the minimal zoo
fixture; @sec:S03-appendix-galois-sketch formalizes the mathematical substrate;
@sec:S04-appendix-inference-mathematics details the discrete-POMDP
active-inference computation that closes the evaluation loop;
@sec:S05-appendix-extended-related-work contextualizes the work within a
curated bibliography; @sec:S06-appendix-source-references indexes the package
source material cited throughout.

---

## Supplemental sections

- @sec:S01-appendix-roundtrip-epsilon provides per-fixture current native
  roundtrip role-preservation status across all {{TOTAL_TARGETS}} evaluation
  targets, with `STRUCTURALLY_ISOMORPHIC` / `ROLE_PRESERVED` / `DRIFT` /
  `FAILED` status vocabulary.
- @sec:S02-appendix-ablation gives the measured role-level rule-family ablation
  on `zoo/01_simple_state`, with per-role deltas and failure-mode analysis.
- @sec:S03-appendix-galois-sketch gives the conjectural, scoped statement and
  argument sketch for an epsilon-approximate Galois-style comparison between
  **Prog** and **GNN** preorder quotients, plus
  @inv:bounded-role-preservation-gap and
  @prop:role-preservation-threshold.
- @sec:S04-appendix-inference-mathematics gives the discrete-time POMDP
  formulation, variational free energy (VFE) functional and derivation,
  belief-propagation equations, identity-case zero-VFE analysis, observed VFE
  regimes, Bayesian D-update rule, and expected free energy (EFE) for policy
  selection.
- @sec:S05-appendix-extended-related-work gives the {{BIB_ENTRIES}}-entry
  curated bibliography across topical clusters: program analysis to GNN,
  active inference tooling, code understanding and embeddings, formal methods,
  POMDP solvers, code summarization, program synthesis, lenses and categorical
  theory, and Markov blankets / active-inference foundations.
- @sec:S06-appendix-source-references indexes external COGANT package
  documentation, evaluation artifacts, and manuscript tooling referenced
  throughout the main text and appendices.

---

## Notation supplement

- @sec:98-notation-supplement is the canonical reference for manuscript-level
  mathematical symbols, acronyms, and formal objects. It is organised into
  program-graph symbols, translation-engine symbols, confidence-model symbols,
  A/B/C/D matrices, category-theory and Galois symbols, equation and
  scoped-claim index, Active Inference roles and mapping kinds, node and edge
  kind enumerations, and acronyms.
