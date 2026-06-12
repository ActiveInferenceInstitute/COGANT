---
project: cogant
phase: current-readiness
mode: source-grounded
updated: 2026-06-07
---

# COGANT Ideal State Artifact

COGANT is a private working project that pairs an installable Python package
with a manuscript and generated evidence artifacts. The authoritative project
root is `/Users/4d/Documents/GitHub/projects/working/cogant`; the installable
package root is `cogant/`; manuscript source lives in `manuscript/`; generated
manuscript output lives in `output/`; native package evaluation output lives
under `cogant/evaluation/`.

## Current Goal

The project should be defensible as a reproducible codebase-to-GNN research
artifact:

- numeric manuscript claims are injected from `cogant/evaluation/METRICS.yaml`
  and related generated data files;
- the native roundtrip ledger is regenerated from local source fixtures, not
  edited by hand;
- docs point to the working checkout and documented `uv run` commands;
- package behavior is verified by tests and local audit scripts; and
- limitations state the current scope boundary directly: Python roundtrip
  evidence, rule-derived role labels, and role preservation rather than full
  semantic equivalence.

## Source Of Truth

| Surface | Authority |
|---|---|
| Package implementation | `cogant/py/cogant/` |
| Package tests | `cogant/tests/` |
| Project-level audit tests | `tests/` |
| Roundtrip ledger | `cogant/evaluation/dataset/roundtrip_results.jsonl` |
| Aggregate metrics | `cogant/evaluation/METRICS.yaml` |
| Manuscript variables | `tools/manuscript_vars.py` and `output/data/manuscript_variables.json` |
| Manuscript source | `manuscript/*.md`, `manuscript/config.yaml`, `manuscript/references.bib` |
| Rendered manuscript source tree | `output/manuscript/` |
| Figure registry | `manuscript/figures/registry.json` plus generated PNGs under `output/figures/` |
| Pipeline runner | `run_all.py`, `tools/run_all_runner.py`, and `run_all.json` |

## Required Gates

Run these from the project root unless a command says otherwise:

```bash
uv run --directory cogant python ../tools/regenerate_roundtrip_ledger.py
uv run --directory cogant python ../tools/regenerate_metrics.py
uv run python scripts/z_generate_manuscript_variables.py --strict
uv run python tools/check_metrics_fresh.py
uv run python tools/audit_docs_constants.py
uv run python tools/audit_stage_list.py
uv run python tools/audit_manuscript_numbers.py --output /tmp/cogant_number_audit.md
uv run python tools/audit_manuscript_markdown_links.py
uv run python tools/audit_manuscript_crossrefs.py
uv run python tools/audit_manuscript_citations.py
uv run python tools/audit_manuscript_math_adjacency.py
uv run python tools/audit_robustness_table.py
uv run python tools/audit_synthetic_surfaces.py --strict
uv run python tools/audit_figure_renderers.py
uv run python tools/claim_ledger.py --manuscript-dir manuscript --output-dir /tmp/cogant_claim_ledger --fail-on-literal-numbers
uv run --directory cogant python docs/verify_doc_links.py
uv run --directory cogant python docs/verify_manuscript_links.py
uv run pytest tests/ -q
uv run --directory cogant pytest tests/ -q
```

The package suite is the expensive gate. Use targeted tests while developing,
then run the full suite before calling the repository ready.

## Claim Policy

- Do not state a metric in manuscript prose unless it is injected from a
  generator or checked by an audit.
- Do not use the roundtrip ledger to claim behavioral equivalence of arbitrary
  Python programs; it measures native role preservation and related diagnostics.
- Do not use JavaScript, TypeScript, Rust, or Go parser existence as evidence
  for reverse-synthesis coverage. Current roundtrip evidence is Python-scoped.
- Treat `control_positive` fixtures with zero source roles as invalid evidence;
  `tools/check_metrics_fresh.py` is responsible for rejecting that case.
- Re-run source-generating commands after modifying fixtures, translation
  rules, metrics logic, manuscript variables, or figure generators.
- Manuscript/public outputs must not publish source `.md` links or proxy matrix
  claims; strict generation plus `audit_manuscript_markdown_links.py`,
  `audit_synthetic_surfaces.py --strict`, and figure sidecar checks are the
  current public-surface guard.

## Release Boundary

Ready means:

- all gates above pass on the current worktree;
- `METRICS.yaml`, `roundtrip_results.jsonl`, and `output/manuscript/` agree;
- rendered figures are present under `output/figures/`;
- active docs contain no obsolete working-directory paths; and
- remaining limitations are explicit scope boundaries, not hidden defects.

Follow-up work that changes the empirical scope must come with new data:
human-labeled role annotations, a larger roundtrip corpus, non-Python
reverse-synthesis evidence, or a fresh performance benchmark on a graph-large
target.

## Changelog

- **2026-06-08 — Post-review hardening + held-out eval (round 2).**
  - **Guard audit (durable):** added `tools/audit_manuscript_math_adjacency.py`
    + `tests/test_audit_manuscript_math_adjacency.py` and wired it into the gate
    list and `.github/workflows/ci.yml`. It resolves manuscript variables, then
    flags any inline-math span whose closing `$` is digit-adjacent (the
    `$-$10` Pandoc leak) so the bug class cannot recur. Live manuscript: 0.
  - **Citation→claim semantic check:** added `tools/citation_claim_ledger.py`
    (deterministic, CI-safe) that pairs every `[@key]` with its claim sentence
    and bib title for review. Ran an out-of-band LLM-judge pass over all 12
    newly-added citations: **12 SUPPORTS, 0 PARTIAL, 0 MISMATCH** — each
    confirmed against the cited paper's actual abstract.
  - **Dev-env note:** manuscript audits that import `cogant.*`
    (`audit_manuscript_module_refs.py`, etc.) MUST run via
    `uv run --directory cogant python ../tools/<audit>.py` (the inner env has
    `numpy`); the bare root venv lacks package deps and will false-fail.
  - **Template render fix (`../template`):** `infrastructure/rendering/latex_texttt.py`
    only made `\texttt{}` breakable when it contained `/`, `_`, `.`, or `*`, so
    long separator-less CamelCase rule names (`MutatingSubsystemRule`,
    `SingletonAccessRule`) overflowed narrow ablation-table columns. Broadened
    to all monospace spans ≥16 chars (`\seqsplit` only adds break points, so
    fitting spans are unchanged) + regression test. Fixes the review's
    right-margin-overflow item for every project, not just COGANT.
  - **Held-out evaluation (NEW DATA):** ran `cogant roundtrip` on never-tuned
    external repos (tqdm, dateutil, pyyaml — rules NOT authored against them) to
    produce genuine out-of-sample role-preservation scores; results in
    `/tmp/cogant_heldout/`. Unlike the in-sample fixtures (which upper-bound),
    these estimate generalization and are the new-data class the Release
    Boundary requires before any scope-expanding claim.
  - **PDF re-render:** re-rendered via `../template/scripts/03_render_pdf.py
    --project working/cogant` so the `−` fix, 12 citations, taxonomy footnote,
    and texttt overflow fix are live in `output/`.
  - **Residual (template-side, lower impact):** Appendix A.4 fenced-command
    overflow and notation-supplement column collision still want a
    `listings`/column-width pass in `../template`; the dominant ablation-table
    overflow is fixed.

- **2026-06-08 — Peer-review incorporation (manuscript).** Acted on an external
  deep review. (1) Fixed a real rendering bug in `manuscript/09_ablation.md`: the
  rule-family ablation table wrote `$-${{TOKEN}}`, and pandoc does not treat a
  closing `$` immediately followed by a digit as math, so `$-$10` leaked
  literally; replaced with a Unicode minus `−` (renders in both the HTML and
  LaTeX paths; the engine already handles `Δ`/`σ`). RedTeam correction: the
  review's claimed second instance ("Table 22 fixpoint ablation") does not
  exist — `S02_appendix_ablation.md` uses bare `{{TOKEN}}` with no `$-$`.
  (2) Added **12** web-verified citations to `references.bib`, each wired into
  its matching section (1:1 used/defined invariant preserved, audit 119==119):
  `foster2008quotient`, `pacheco2013generic`, `smithe2024structured`,
  `tull2023active` (08_03 lenses/categorical); `liu2024codexgraph`,
  `ouyang2024repograph`, `abdelaziz2021graphgen4code` (08_02 related work);
  `friston2024pixels`, `parr2019generalised`, `friston2017curiosity`,
  `friston2025reasoning` (S04 inference math); `grohe2024similarity` (S03).
  Verification caught review errors: Foster DOI was off by one digit
  (`1411203`→`1411204`), GraphGen4Code title was wrong, Smithe needs
  "(Extended Abstract)". `friston2025reasoning` (arXiv:2512.21129) was first
  excluded as venue-less, then re-included after confirming a stable arXiv ID —
  "no DOI" was not a valid exclusion reason. `friston2017curiosity`/`2025reasoning`
  are framed honestly as the *unimplemented* Bayesian-model-reduction alternative
  to the running-mean D-update, not as something COGANT implements.
  (3) Added a fixture-taxonomy footnote in the abstract clarifying
  six benchmark ⊂ {{SHIPPED_FIXTURE_COUNT}} shipped ⊂ {{TOTAL_TARGETS}} round-trip targets.
  Gates green: citation/crossref/strict-injection/claim-ledger audits + manuscript tests.
  NOT addressed (template/LaTeX-render concerns, not fixable from markdown source):
  right-margin overflow of long monospace identifiers in the ablation tables,
  Appendix A.4 command-line overflow, notation-supplement column collision —
  these require column-spec changes in the sibling `../template` render pipeline.
