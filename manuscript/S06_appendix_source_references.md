# Appendix F — Source References and Cross-Links {#sec:S06-appendix-source-references}

This appendix indexes the external COGANT package documentation, evaluation
artifacts, and manuscript tooling referenced in the main text and other
appendices. All paths are relative to the COGANT package root (`../cogant/`)
unless otherwise noted. In a standalone checkout, run project-local commands
from the COGANT root. After vendoring into the parent template, replace
project-local command prefixes with `projects/working/cogant/` when running from the
template root.

Package documentation is the canonical navigation surface for API, CLI, MkDocs,
and operational details. The manuscript therefore keeps only evidence-bearing
package paths inline and centralizes the broader documentation map here: start
at `../cogant/docs/index.md`, use
`../cogant/docs/reference/documentation_modules.md`
for the module index, and run
`../cogant/docs/verify_doc_links.py`
when editing package docs.

---

## Source-tier classification

| Tier | Definition | Examples in this manuscript | Use in claims |
|---|---|---|---|
| T1 generated package artifact | Machine-written artifact from a COGANT run, regeneration script, or validation gate | `../cogant/evaluation/METRICS.yaml`, `../cogant/evaluation/dataset/roundtrip_results.jsonl`, `../cogant/evaluation/figures/metrics.json`, `../output/figures/manifest.json` | Numeric release claims, fixture tables, figure provenance |
| T2 source-controlled implementation/test | Code, tests, or config checked into this tree | `../cogant/py/cogant/`, `../cogant/tests/`, `../tools/claim_ledger.py` | API behavior, validation contracts, audit-tool behavior |
| T3 measured fixture artifact | Checked-in benchmark or external-repository run with a fixed source file and stated measurement date | `../cogant/evaluation/real_world_eval_summary.json`, `../cogant/docs/evaluation/REAL_WORLD_EVAL.md` | Scaling and forward-pipeline fixture claims |
| T4 primary external source | Peer-reviewed paper, standard, official specification, or official project documentation | `references.bib` entries for Joern/CPG, CodeQL, SARIF, ProGraML, PyMDP, CodeT5, CodeXGLUE | Related-work and standards claims |
| T5 secondary/navigation source | Index pages, README-style maps, or convenience docs | MkDocs navigation pages, manuscript README files | Pointers only; do not anchor numeric or novelty claims |

When tiers conflict, prefer the narrowest directly generated artifact for local
numbers, the current implementation/test for package behavior, measured
fixtures for their stated fixture scope, and primary external sources for
related-work claims.

## Evaluation artifacts

| Artifact | Path | Referenced in |
|---|---|---|
| Current native roundtrip ledger | `../cogant/docs/evaluation/ROUNDTRIP_EVAL.md` | @sec:S01-appendix-roundtrip-epsilon, @sec:10-conclusion, @sec:09-ablation |
| Real-world library forward fixture | `../cogant/docs/evaluation/REAL_WORLD_EVAL.md` | @sec:S01-appendix-roundtrip-epsilon |
| Per-fixture empirical claim runs | `../cogant/docs/evaluation/EMPIRICAL_CLAIM.md` | @sec:S01-appendix-roundtrip-epsilon, @sec:S04-appendix-inference-mathematics |
| Constraint-role recovery mechanism | `../cogant/docs/evaluation/CONSTRAINT_FIX.md` | @sec:S03-role-preservation-theorem |
| Reverse-synthesis status | `../cogant/docs/evaluation/ROUNDTRIP_IMPROVEMENT.md` | @sec:10-conclusion, @sec:00-abstract |
| Active Inference role mapping per rule | `../cogant/docs/evaluation/ACTIVE_INFERENCE_MAPPING.md` | @sec:09-ablation |
| Confidence calibration table | `../cogant/docs/evaluation/CALIBRATION.md` | @sec:09-ablation |
| Mutation testing report | `../cogant/docs/evaluation/MUTATION_REPORT.md` | @sec:06-04-tests-mutation-and-benchmarks |
| Role-preservation invariant notes | `../cogant/docs/evaluation/ISOMORPHISM_THEOREM.md` | @sec:S03-appendix-galois-sketch |
| Annotated bibliography ({{BIB_ENTRIES}} entries) | `../cogant/docs/evaluation/LITERATURE.md` | @sec:S05-appendix-extended-related-work |

## Manuscript tooling

| Tool | Path | Purpose |
|---|---|---|
| Metric token registry | `../tools/manuscript_vars.py` | `MANUSCRIPT_VARS` keys to dotted paths in `METRICS.yaml` |
| METRICS.yaml regeneration | `../tools/regenerate_metrics.py` | Rebuilds canonical numeric ground truth |
| Manuscript variable injection | `../tools/inject_manuscript_vars.py` | Substitutes registered tokens in `.md` files |
| Manuscript figure registry | `../tools/manuscript_figures.py` | Copies package-run PNGs from `../cogant/output/` to `../output/figures/` |
| Visualization quality audit | `../tools/visualization_quality_audit.py` | Summarizes promoted figure sidecars into JSON, Markdown, and PNG review artifacts |
| Manuscript evidence audit | `../tools/manuscript_evidence_audit.py` | Summarizes section-level citation, metric, figure, artifact, validator, and boundary-language lanes, including non-fatal reviewer actions |
| Manuscript review dashboard | `../tools/manuscript_review_dashboard.py` | Combines figure QA, section evidence, claim ledger, figure-manifest status, and the current evidence review queue |
| Publication readiness audit | `../tools/audit_publication_readiness.py` | Classifies claims by evidence primitive, checks render-time date autofill, and combines generated evidence surfaces into a ready / caveated / blocked verdict |
| Claim ledger generator | `../tools/claim_ledger.py` | Indexes numeric, citation, figure, artifact-path, and placeholder claims in the manuscript |
| GNN v2 audit surface | `../tools/gnn_v2_audit_surface.py` | Separates version, bridge, COGANT-method, upstream-step, and supply-chain claims into JSON/Markdown/SVG evidence |
| Organization state-space R&D audit | `../tools/organization_state_space_audit.py` | Validates typed-organization sketches against dynamic-evidence, provenance, temporal-admissibility, role-compatible transition, negative-control, and SVG-review requirements |
| Metrics freshness check | `../tools/check_metrics_fresh.py` | Detects drift between METRICS.yaml and source artifacts |
| Manuscript number audit | `../tools/audit_manuscript_numbers.py` | Cross-checks prose numbers against METRICS.yaml |
| Canonical metrics | `../cogant/evaluation/METRICS.yaml` | Single source of truth for all manuscript numbers |
| Variable snapshot | `../output/data/manuscript_variables.json` | Flat `{NAME: value}` generated by `z_generate_manuscript_variables.py` |
| Claim ledger snapshot | `../output/claim_ledger.md` | Generated review table for unsupported or newly added literal claims |
| Manuscript evidence snapshot | `../output/analysis/manuscript_evidence_audit.md` | Generated section-level matrix and reviewer-action queue for evidence-lane review |
| Manuscript review dashboard | `../output/analysis/manuscript_review_dashboard.md` | Generated integrated review summary for figure, claim, evidence, manifest, and review-queue status |
| Publication readiness snapshot | `../output/analysis/publication_readiness.md` | Generated verdict tying active publication metadata and claims to metric, artifact, citation, validator, or limitation evidence |

## Manuscript sections cited by other appendices

| Section | Description |
|---|---|
| Main text @sec:09-ablation | @tbl:rule-family-ablation, @tbl:fixpoint-iteration-ablation, @tbl:matrix-degraded-output-ablation |
| @sec:S02-appendix-ablation | Per-role ablation on `zoo/01_simple_state` |
| @sec:02-01-program-graph-and-formal-foundations | Formal program-graph and fixpoint definitions |
| @sec:S03-appendix-galois-sketch | Conjectural Galois-style preorder comparison and scoped role-preservation invariant |

## Editorial and validation tooling

| Resource | Path | Purpose |
|---|---|---|
| Manuscript editorial protocol | `AGENTS.md` | Canonical sources of truth, exclusion rules, sync cadence |
| Manuscript structure index | `README.md` | Section ordering, discovery, validation commands |
| Link verification | `../cogant/docs/verify_manuscript_links.py` | Checks relative links in `manuscript/*.md` against the package tree |
| Markdown validation | `uv run python tools/audit_manuscript_crossrefs.py` locally; `uv run python -m infrastructure.validation.cli markdown ./projects/working/cogant/manuscript/` after linking into the parent template | Manuscript cross-reference and template-level Markdown integrity checks |
