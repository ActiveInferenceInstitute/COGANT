# COGANT World-Threat + RedTeam Stress Test — 2026-05-21

This note applies the WorldThreatModelHarness frame to COGANT's package and
manuscript while acknowledging the current harness boundary: the persistent model
store at `~/.claude/MEMORY/RESEARCH/WorldModels/` does not exist in this
environment, so this is a project-specific horizon stress test rather than a
claim that all 11 persistent world-model files were loaded.

External research was gathered with Perplexity (`sonar`) on 2026-05-21. The
strongest current comparators remain Code Property Graph / Joern, GraphCodeBERT,
CodeT5 / CodeT5+, CodeSearchNet / CodeXGLUE-style evaluation, GGNN and
heterogeneous-GNN program encoders, and PyMDP / Active Inference Institute
tooling. The strongest reviewer threats are semantic-vs-structural roundtrip
validity, A/B/C/D matrix non-redundancy, proof that "active inference" is more
than branding, robustness to semantics-preserving code transforms, leakage-free
evaluation, and calibrated failure detection.

## Executive Verdict

COGANT is strongest as a reproducible evidence compiler over code artifacts,
not as a publish-ready claim of semantic equivalence across arbitrary codebases.
Near-term success depends on proving metric honesty, artifact reproducibility,
and scoped comparator positioning. Longer-term success depends on adding
semantic-oracle tests, robustness transforms, and an evaluation corpus that
separates in-sample fixture behavior from out-of-domain generalization.

## Horizon Analysis

| Horizon | Verdict | What holds | What breaks first |
|---|---|---|---|
| 6 months | Favorable | The current audit gates, manuscript variables, and dashboard artifacts can support a v0.6.x maintenance release. | Dirty-worktree metric provenance and legacy roundtrip rows remain easy reviewer targets. |
| 1 year | Favorable with constraints | A v0.7 wave can be credible if it lands a native v0.6 roundtrip ledger and non-fallback exemplar figures. | Claims about active inference or semantic preservation will be rejected if still backed mainly by structural validity. |
| 2 years | Neutral | The rule/provenance architecture remains useful as a deterministic baseline against learned code models. | Learned code-model baselines will make "symbolic only" look narrow unless COGANT reports head-to-head or hybrid results. |
| 3 years | Neutral | Repository-to-graph export remains valuable infrastructure for ML and analysis workflows. | Multi-language expectations rise; Python-first with optional JS/TS needs sharper scope boundaries. |
| 5 years | Mixed | Active-inference model export may become a differentiated niche if downstream runtime evidence matures. | Without calibrated uncertainty and semantic-oracle evaluation, COGANT risks being viewed as a visualization/export pipeline. |
| 7 years | Mixed | Provenance-bearing symbolic extracts are likely still valued for auditability and reproducibility. | End-to-end AI software engineering tools may absorb basic repository modeling and graph generation. |
| 10 years | Uncertain | The fixed IR and generated-artifact discipline can survive as a benchmarkable data-production tool. | Static rule families will need either continuous curation or learned/human-review calibration to avoid long-tail decay. |
| 15 years | Uncertain | The idea of code as an executable generative model remains intellectually durable. | Specific GNN/A/B/C/D conventions may change; COGANT must preserve adapters rather than lock claims to one format. |
| 20 years | Uncertain | Reproducible artifact ledgers and explicit provenance will still matter in scientific tooling. | Current parser and matrix assumptions may be obsolete without a stable abstraction boundary. |
| 30 years | Speculative | Symbolic evidence compilers may become archival infrastructure for software science. | Claims tied to current language front ends, tree-sitter behavior, or today's active-inference libraries will be historical. |
| 50 years | Speculative | The hard-to-vary contribution is the audit chain from source facts to model artifacts. | Any narrow implementation claim is fragile; only the extraction/provenance/evaluation philosophy is likely to persist. |

## RedTeam Synthesis

Critical convergence from local review plus Perplexity:

- **Semantic preservation is the deciding assumption.** Roundtrip role counts,
  graph edit distance, and matrix shape validity are necessary but insufficient.
  The next release wave needs compiler/interpreter-backed semantic checks and
  counterexamples where structural preservation hides meaning loss.
- **A/B/C/D matrices need non-redundancy evidence.** The matrix-fallback table is
  now honest, but the paper should show what breaks when A, B, C, or D evidence
  is removed on fixtures where those matrices are not all fallback.
- **Active inference must be bounded.** The manuscript should keep saying that
  COGANT emits agent-consumable artifacts and deterministic runtime traces; it
  should avoid implying that repository extraction alone proves closed-loop
  agency.
- **Baselines need explicit posture.** CPG/Joern, GraphCodeBERT, CodeT5,
  CodeSearchNet/CodeXGLUE, GGNN/HGT-style code graphs, Semgrep/CodeQL/Souffle,
  and PyMDP are the comparison set reviewers will expect.
- **Generalization claims must stay weak.** Without held-out, clone-aware,
  project-level splits and confidence intervals, COGANT should say "runs
  end-to-end on" rather than "generalizes to."

## Implementation Consequences

- Treat `tools/regenerate_metrics.py`, `tools/check_metrics_fresh.py`, and
  manuscript variable injection as the primary trust boundary; prose must never
  outpace these gates.
- Keep the new ablation `by_mapping_kind` block as a reviewer-visible artifact:
  net mapping deltas hide role-mix shifts, especially on `zoo/01_simple_state`.
- Add future work for semantics-preserving transforms: identifier renaming,
  dead-code insertion, formatting/comment changes, legal statement reordering,
  equivalent loop/branch rewrites, inlining/outlining, and parser/frontend
  variation.
- Keep graphical abstracts tied to non-degenerate fixtures when making evidence
  claims; use `calculator` only as a smallest-case orientation figure.
- Before publication, regenerate a native v0.6 roundtrip ledger with
  `role_preservation_score`, `roundtrip_status`, file/LOC/node/edge counts, and
  per-target scaffolding fraction populated from the same run.

## Model-Store Follow-Up

If WorldThreatModelHarness will be reused outside this project, create the
persistent 11-file store before the next horizon analysis:

`INDEX.md`, `6-month.md`, `1-year.md`, `2-year.md`, `3-year.md`, `5-year.md`,
`7-year.md`, `10-year.md`, `15-year.md`, `20-year.md`, `30-year.md`, and
`50-year.md`.

Each model should carry source date, confidence, geopolitical/technology/
economic/security/environment sections, and a wildcard register. Until that
exists, COGANT horizon analysis should be labeled project-specific, not a full
harness run.
