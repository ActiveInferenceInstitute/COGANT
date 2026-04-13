# AGENTS.md — Evaluation module

Dated R&D reports, empirical studies, calibration notes, release-readiness
assessments, and the bibliography of the COGANT evaluation program. This
module is the human-facing narrative companion to the machine-readable
artifacts that live in the repository-root `evaluation/` directory (a
sibling of `docs/`, not part of the MkDocs tree).

## Purpose and ownership

The evaluation module is append-mostly: old reports stay for provenance
even after they have been superseded. Every file here is either (a) a
dated R&D log, (b) a release-gate assessment, (c) an empirical study, or
(d) a bibliography / related-work page. Owned jointly by whoever is running
the current evaluation gate and whoever last updated `R&D_LOG.md`.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC, grouped by readiness / theory / empirical / bibliography | When a file is added or moved between groupings |
| `AGENTS.md` | This file — maintenance rules | When the append-only policy or grouping changes |
| `V1.0_READINESS.md` | Gate-by-gate v1.0 readiness assessment | At each v1.0 readiness gate review |
| `FINAL_REPORT.md` | Consolidated narrative for the current evaluation effort | When a major evaluation milestone closes |
| `SCOPING_REPORT.md` | Scope and milestone tracking | When scope changes or a milestone lands |
| `R&D_LOG.md` | Dated gate entries (changes, tests, coverage, decisions) | Appended at every gate; never rewritten |
| `RELEASE_NOTES_v0.2.0.md`, `RELEASE_NOTES_v0.5.0.md` | Historical release notes | Immutable — treat as archived |
| `ACTIVE_INFERENCE_MAPPING.md` | Code patterns to Active Inference roles (canonical source) | When the role vocabulary or mapping rules change |
| `ISOMORPHISM_THEOREM.md` | Roundtrip / isomorphism statement and proof sketch | When the isomorphism definition changes |
| `CALIBRATION.md` | Confidence and rule-calibration backlog | When the calibration model or threshold defaults change |
| `CONSTRAINT_FIX.md` | The CONSTRAINT detection fix and its impact on the metrics | Only to correct factual errors post-hoc |
| `FIRST_INFERENCE.md` | First-inference experiment notes | Only to correct factual errors post-hoc |
| `ROUNDTRIP_EVAL.md` | Forward + reverse roundtrip evaluation results | When roundtrip results are re-measured |
| `ROUNDTRIP_VALIDATION.md` | Validation of the roundtrip claim | When the validation methodology changes |
| `ROUNDTRIP_IMPROVEMENT.md` | Iterative improvements log | Appended when improvements land |
| `CROSS_LANG_ROUNDTRIP.md` | Cross-language roundtrip study | When new language pairs are added |
| `REAL_WORLD_EVAL.md` | External-repository evaluation runs | When new external repos are added |
| `EMPIRICAL_CLAIM.md` | Stated empirical claims and the evidence for each | When claims are added, weakened, or withdrawn |
| `BENCHMARK_VS_PRIOR.md` | Baseline comparisons | When baselines are re-run |
| `INCREMENTAL_BENCHMARK.md` | Incremental rescanning benchmarks | When the incremental algorithm changes |
| `SCALING_ANALYSIS.md` | Scaling characteristics on larger inputs | When a new scale is measured |
| `GNN_VALIDATION_REPORT.md` | Validation results for generated GNN packages | When the GNN validator rule set changes |
| `MUTATION_REPORT.md` | Mutation-testing results | When mutation testing is re-run |
| `LITERATURE.md` | Bibliography-style references | When a cited paper is added or corrected |
| `RELATED_WORK.md` | Comparison with adjacent tools and research | When a comparable tool is released or a comparison is updated |

## Adding a new doc

1. Decide the category: readiness, theory, empirical, or bibliography.
   The `README.md` groups files by category, so new files need to land in
   the right table.
2. Use `UPPER_SNAKE_CASE.md` to match the existing convention — these
   filenames are cited from code and release notes, so stability matters.
3. If the new file supersedes an older one, do not delete the older file.
   Add a `> **Superseded by ...**` banner at the top of the old file and
   link to the replacement.
4. Add a row to the appropriate table in `README.md`.
5. If the file is cited from `R&D_LOG.md` or from `manuscript/`, double-
   check that inbound links still resolve with
   `uv run python docs/verify_doc_links.py`.

## Known gotchas

- **Do not rename**. Other files, code, and release notes cite evaluation
  pages by their exact filename. Renaming breaks inbound links in ways
  `verify_doc_links.py` will not catch (because it only checks outbound
  links from `docs/`).
- `R&D_LOG.md` is append-only. Never rewrite a prior gate entry; add a
  follow-up entry that corrects or supersedes it instead.
- Some files have companion machine artifacts (datasets, JSON metrics,
  dashboard exports) in the repository-root `evaluation/` directory. Keep
  the two in sync when you update numbers here.
