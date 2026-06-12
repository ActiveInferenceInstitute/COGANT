# COGANT TODO

Last updated: 2026-06-12

This backlog scopes the most useful next development avenues after the manuscript,
test, rendering, and visualization passes. Keep items grounded in generated
artifacts and package behavior; COGANT should make claims only when the run
directory, test suite, or manuscript pipeline can reproduce them.

## 1. Visual Inspection Workbench

Goal: make human inspection of codebase-to-GNN and GNN-to-code artifacts a
first-class interface, not a side effect of scattered PNG files.

- [x] Add an early, manuscript-ready interpretability overview figure generated
  from real `<output_root>/<target_id>/` artifacts.
- [x] Render program graph, state-space factor, A/B/C/D matrix, Markov blanket,
  GNN markdown, process Gantt, and summary-cover PNGs from the same completed
  run directory.
- [x] Add a single-target inspection dashboard that reads `data/`,
  `gnn_package/`, `figures/`, `analysis/`, `reports/`, and `roundtrip/` without
  requiring in-memory Python objects.
- [x] Add a graphical abstract artifact that summarizes source code, typed
  graph, semantic roles, state-space compilation, GNN matrices, blanket
  partition, and roundtrip status in one visual chain.
- [x] Wire the inspection dashboard into `cogant viz`, `render_all_pngs()`,
  `run_all.py`'s existing viz step, and package documentation.
- [x] Link the inspection dashboard from generated `site/index.html` pages when
  a static site already exists.
- [x] Add dashboard affordances for artifact health: present/missing states,
  generated-at timestamps, validation status, matrix shapes, source coverage,
  confidence tiers, and hotspot rankings.
- [x] Add roundtrip diagnostics panels for role-preservation score, matrix score,
  structural score, shape parity, generated-code compile/test status, warnings,
  and changed semantic roles.
- [x] Add graph and GNN visual diff panels for roundtrip comparison: original
  graph versus regenerated graph and original GNN versus roundtripped GNN.
- [x] Add benchmark-scale visual artifact completeness summaries for the batch
  dashboard.
- [x] Add broader benchmark visual summaries for cross-target role
  distributions, graph-size trends, and failure reasons.
- [x] Run screenshot/browser QA for the current generated HTML dashboard after
  frontend changes.
- [x] Add reusable screenshot/browser QA for generated HTML dashboards.

## 2. Roundtrip Quality Diagnostics

Goal: treat roundtrip as a measurable reconstruction problem with inspectable
losses, not just a file-emission demo.

- [x] Define roundtrip invariants for code -> graph -> GNN -> code -> graph:
  node identity preservation, edge-kind preservation, role preservation,
  state-space shape preservation, and executable smoke behavior.
- [x] Emit `roundtrip/metrics.json` with role-preservation score, matrix score,
  structural score, shape parity, artifact paths, and warnings.
- [x] Extend `roundtrip/metrics.json` with a transparent role-multiset
  edit-distance proxy, a `graph_edit_distance` field for dashboards, and
  generated-code compile/test status.
- [x] Add role-delta roundtrip diagnostics to the inspection dashboard.
- [x] Add original-vs-regenerated graph and GNN side-by-side visualizations to
  the inspection dashboard.
- [x] Add fixture-level thresholds to `evaluation/METRICS.yaml` and manuscript
  variable bindings for roundtrip quality.
- [x] Add tests for roundtrip metrics emission and dashboard consumption.
- [x] Add a reverse-synthesis smoke test that executes a generated action
  against generated `State` factors.
- [x] Add broader tests for both one-way conversions and complete roundtrip
  output comparisons.
- [x] Keep failure cases explicit: when reverse synthesis is unavailable, the
  dashboard should say so rather than implying a completed loop.

## 3. Evaluation Corpus Expansion

Goal: broaden evidence across codebase shapes while keeping the suite cheap
enough for local development.

- [x] Add small fixtures for CLI tools, async services, data pipelines, plugin
  architectures, notebooks converted to modules, and multi-package workspaces.
- [x] Add one or two medium real repositories with permissive licenses and stable
  shallow-clone behavior. (`run_all.json`: `remote_click` 8.1.7 — ~10 KLOC
  BSD-3 — promoted to an active target; `remote_itsdangerous` and
  `remote_markupsafe` pinned to `2.2.0`/`2.1.5`. All remote `git_ref`s are
  now immutable release tags so `git clone --depth 1 --branch <tag>` is
  reproducible; the example block models the same pinned pattern.)
- [x] Record fixture intent, expected graph motifs, expected semantic roles, and
  expected failure modes near each fixture.
- [x] Add corpus-stratified metrics: file count, LOC, node/edge counts,
  mapping count, state-space dimensions, validation result, render completeness,
  and roundtrip status.
- [x] Keep slow or network-dependent corpus runs separated from the fast unit
  suite while making their results reproducible through `run_all.py`.

## 4. Rule Calibration And Reviewer Loop

Goal: make semantic mapping rules inspectable, tunable, and reviewable.

- [x] Emit per-rule match traces with evidence snippets, confidence components,
  conflict resolution decisions, and final role assignments.
- [x] Add a reviewer annotation format for accepted/rejected mappings and use it
  to calibrate confidence thresholds.
- [x] Add precision/recall reports on annotated fixtures.
- [x] Add dashboard panels for rule-family contribution and conflict outcomes.
- [x] Add ablation regeneration commands that update `METRICS.yaml` and the
  manuscript without hand-editing numeric claims. (`tools/regenerate_ablation.py`
  runs the live pipeline + `TranslationEngine.translate(rule_filter=…)` per
  family on the 6 packaged fixtures, computes rule-family / fixpoint /
  matrix degraded-output deltas, merges an `ablation:` block into `METRICS.yaml`
  (additive, header-preserving), and is wired into `regenerate_metrics.py`.
  `09_ablation.md` rule-family + fixpoint + matrix degraded-output tables now
  resolve from `{{ABLATION_*}}` placeholders — no hand-edited numerics.
  Measurement corrected materially-wrong reconstructed values; see
  CHANGELOG erratum.)
  - [x] Sub: emit per-`MappingKind` decomposition of family deltas.
    `tools/regenerate_ablation.py` now writes `ablation.by_mapping_kind`
    alongside net family totals, with regression coverage in
    `tests/test_regenerate_ablation.py`.
  - [x] Sub: extend the measured harness to `zoo/01_simple_state`.
    `S02_appendix_ablation.md` now resolves measured zoo/01 values from
    `METRICS.yaml` rather than hand-reconstructed estimates.

## 5. Language Front-End Maturation

Goal: make parser and graph extraction behavior clear across languages and
degraded-output modes.

- [x] Document exactly which language front ends are production-grade,
  experimental, or fixture-only.
- [x] Add language-specific smoke fixtures and parser fallback tests.
- [~] Improve graph normalization around imports, method receivers, async calls,
  decorators/annotations, generated files, and test-only code.
  **Progress 2026-05-19**: dotted-import package-qualified keying landed.
  `module_nodes` is now indexed under both the bare stem *and* the
  dotted package path (e.g. `pkg.deep.x`), `__init__.py` collapses to its
  package name, IMPORTS resolution walks `pkg.deep.x → pkg.deep → pkg` and
  also tries `target + imported_name` for the submodule case
  (`from pkg.deep import x` matches `pkg.deep.x`). A two-pass refactor
  fixes a latent ordering hazard (importing modules walked before targets
  were indexed silently dropped edges). Behaviour pinned by
  `cogant/tests/unit/test_graph_orchestration_dotted_imports.py` (4
  tests). **Remaining as honest follow-ups** (out of scope for this pass —
  each is its own increment): method-receiver→class resolution,
  async-call edge kind, decorator-driven edges, generated-file
  detection, test-only `NodeKind.TEST` classification.
- [x] Add dashboard badges for parser certainty and degraded-output usage.
- [x] Add error reports that identify skipped files and unsupported constructs.

## 6. Runtime And Inference Demonstrations

Goal: show that emitted GNN artifacts are not only syntactically valid but also
useful in active-inference runtimes.

- [x] Add a small deterministic POMDP demo whose generated matrices can be run
  through the upstream GNN toolchain and an inference backend.
- [x] Record inference traces as artifacts and visualize policy, belief, and
  preference trajectories.
- [x] Add manuscript figures that distinguish structural translation evidence
  from actual inference behavior.
- [x] Keep runtime dependencies optional and isolate them behind explicit extras.

## 7. CI, Packaging, And Promotion Readiness

Goal: make the project easy to link into `projects/working/cogant/` from the
working sidecar checkout without breaking the template pipeline.

- [x] Keep `PROMOTION.md` current with every path assumption introduced by new
  tooling.
- [x] Add CI checks for `uv sync --extra all`, `pytest`, `ruff`, `mypy`,
  manuscript variable generation, manuscript validation, and strict figure-copy
  mode.
- [x] Add an artifact completeness check for `run_all.py` outputs.
- [x] Ensure generated dashboards and figures remain deterministic enough for
  documentation and review.
- [x] Audit docs for the COGANT project root versus package root distinction
  before promotion.

## 8. Review Backlog (surfaced 2026-05-15 comprehensive review)

Concrete findings from the multi-agent review that are reviewed and
recorded here rather than silently deferred. Each is scoped beyond a safe
review-and-improve pass (architectural decision or broad refactor).

- [~] **Typed config / preset subsystem partial-wire decision (2026-05-19).**
  The `--config` path (`py/cogant/cli/main.py:732`) does call
  `ConfigLoader.load_from_yaml` / `load_json_from_file`, but
  `build_pipeline_config(preset=...)`, `config/presets.py:PRESETS` (a
  *parallel* registry to `config/defaults.py:PRESETS`), and the
  `config/schema.py` enums were not anchored by any test. Status pinned by
  `tests/unit/test_typed_config_loaders_e2e.py` (14 tests, including
  `test_documented_dual_preset_surface_remains_acknowledged` which records
  the two-registry asymmetry as deliberate-and-known). **Resolution path A**
  (preferred): canonicalize a single name map and have the CLI honour both
  registries. **Resolution path B**: prune `presets.py` and migrate the
  richer-content presets into `defaults.PRESETS`. Deferred to a release
  session because the field-name mapping between `cogant.yaml`'s
  `pipeline.stages` and the schema's `run_stages` is the kind of rename
  that wants a deprecation cycle, not an overnight pass.
- [x] **Pipeline stage-list docs omit `dynamic` and self-contradict.**
  Fixed: `docs/cli_reference.md:20`, `docs/getting-started/quickstart.md:19`,
  `docs/faq.md:55`, and the `cogant translate` CLI docstring
  (`py/cogant/cli/main.py:695`) now list the real 10-stage default
  (`… → graph → dynamic → translate → …`) and note `dynamic` runs by
  default / `--no-dynamic` skips it. The `analyze` docstring was already
  correct; the `explain` minimal-pipeline mentions are intentionally
  dynamic-free and left as-is. Empirically grounded against the observed
  live stage log.
- [x] **FAQ `--min-confidence` flag** (2026-05-19). The flag IS implemented
  on both `cogant translate` (cli/main.py:690) and `cogant analyze`
  (cli/main.py:952), threaded through to
  `api.orchestration._filter_semantic_mappings` (line 218). The FAQ
  documentation (`cogant/docs/faq.md:143`) matches the implemented
  semantics. Behaviour pinned by
  `tests/unit/test_min_confidence_filtering.py` (10 tests covering
  threshold-band keep/drop, edge cases at 0.0 / 1.0, empty-input, and
  out-of-range tolerance with the validation layer at the CLI boundary).
- [x] **Stage-list drift gate (durable fix for M4)** (2026-05-19). Canonical
  source of truth now lives at `cogant.pipeline.RUNNER_STAGES`
  (`py/cogant/pipeline/__init__.py`, exported via `__init__.pyi`).
  Auditor `tools/audit_stage_list.py` scans CLI docstrings + selected docs
  + manuscript API section for full-pipeline-claiming stage lists, fails on
  any divergence from the canonical tuple, and is wired into the
  Makefile (`make audit-stages`) and the CI lint job
  (`.github/workflows/ci.yml`). Tests at
  `tests/test_audit_stage_list.py` (7 tests including a negative-control
  fixture that proves the gate catches a forged canonical mismatch — pinned
  per [[feedback-shape-tests-dont-bind-truth]]). No hand-patch path remains.
- [x] **Viz test output-blindness** (2026-05-19). Shared
  helper `cogant/tests/unit/_viz_assert.py` exports
  `assert_figure_nondegenerate` (rejects empty-axes / text-only Figures)
  and `assert_png_nondegenerate` (validates PNG magic bytes + IHDR
  dimensions > 1×1). Migrated viz tests: `test_viz_network.py`,
  `test_viz_matrix.py`, `test_viz_ablation.py`,
  `test_viz_static_analysis.py` (heatmap + histogram),
  `test_viz_static_analysis_view_rendering.py`,
  `test_viz_pipeline_view_rendering.py`, `test_viz_png_export_outputs.py`,
  `test_viz_semantic_view_rendering.py`,
  `test_viz_export_network_views.py` (4 figures). `test_viz_diff.py` and
  `test_viz_plots.py` were verified to have no tautological
  Figure-is-not-None assertions (their probes are content-typed strings).
- [x] **`98_notation_supplement` dangling figure** (2026-05-19). Resolved
  by adding a call-out paragraph in
  `manuscript/98_notation_supplement.md` after the confidence-tier
  threshold table; the figure (`{#fig:cogant-confidence-calibration}`,
  defined at `manuscript/04_examples_and_failure_modes.md:43`) is now
  cross-referenced. `tools/audit_manuscript_crossrefs.py` reports 109
  ids, 417 references, zero dangling.
- [~] **Semantic-preservation and robustness suite (2026-05-21).**
  Per the WorldThreatModel/RedTeam/Perplexity stress test in
  `Plans/WORLD_THREAT_MODEL_COGANT_2026-05-21.md`, the next evaluation
  wave should add semantics-preserving transformation tests before any
  stronger generalization claim: identifier renaming, dead-code insertion,
  formatting/comment changes, legal statement reordering, equivalent
  loop/branch rewrites, inlining/outlining, and parser/frontend variation.
  Success means each transform has a fixture, a roundtrip semantic-oracle
  assertion, and a dashboard-visible degradation row.
  **Progress 2026-06-09 (verifier-first RedTeam):** the harness +
  `tests/integration/test_semantic_preservation.py` now cover **7** transforms
  (reformat, insert_comments, insert_dead_code, rename_locals, reorder_methods,
  swap_if_branches, outline_first_function) with a real negative control
  (`drop_half_definitions`, DETECTED) — confirmed genuinely behaviour-checking
  (importability + role-multiset equality, not shape-only). The manuscript
  robustness table is now **claim-policy-bound**: `tools/audit_robustness_table.py`
  (+ `tests/test_audit_robustness_table.py`, 5 negative controls) ties every
  manuscript row to `robustness_results.json`, wired into CI and the gate list —
  closing the RedTeam science-gap that the table was hand-written. **Remaining
  honest follow-ups:** still in-sample-only (3 base fixtures); the *equivalent
  loop rewrite*, *inlining*, and *parser/frontend variation* transforms and a
  held-out robustness corpus are not yet implemented; the
  `robustness_results.json` freshness (re-run harness on PR) is audited for
  table-consistency but not yet auto-regenerated in CI.
- [x] **Roundtrip drift reduction.**
  Completed in the 2026-06-12 evidence-gated pass: the native v0.6 ledger now
  carries per-row `role_preservation_score`, `roundtrip_status`, file/LOC/node/
  edge counts, and scaffolding fraction, and all 24 native rows are
  role-preserved with 0 drift targets in the refreshed metrics. Remaining
  release work is no longer in-sample drift reduction; it is the separate
  held-out promotion item in the current sequence below.

- [x] **Evidence-gated real-matrix publication pass (2026-06-12).**
  Public A/B/C/D matrix figures now require real exported `matrices.A/B/C/D`
  from `gnn_package/model.gnn.json`, a source digest, source/display shapes,
  B reducer metadata, aligned state-space dimensions, and empty fallback /
  degraded panel lists. `GNNValidator` now actively validates matrix shape,
  stochasticity, missing panels, and state-space alignment before a package can
  receive a perfect score; degenerate developer fixtures remain non-public
  diagnostics with warnings rather than perfect evidence. `run_all.py` summary
  rows are revalidated from the generated `gnn_package/`, and strict manuscript
  generation plus `audit_manuscript_markdown_links.py`,
  `audit_synthetic_surfaces.py --strict`, and figure-renderer/provenance checks
  gate public output. Verified on 2026-06-12 with `run_all.py --fail-fast`
  (`24` targets, `0` failed steps), strict manuscript regeneration, template
  Markdown validators, and PDF/HTML render.

## Current Sequence

Completed items above stay as history. The active sequence is:

1. Resolve the typed config / preset subsystem into one documented preset
   registry with a deprecation path for legacy field names.
2. Finish the remaining graph-normalization increments one at a time:
   method-receiver-to-class resolution, async-call edge kind, decorator-driven
   edges, generated-file detection, and test-only `NodeKind.TEST`
   classification.
3. Extend semantic-preservation robustness beyond the current 7 transforms with
   equivalent loop rewrites, inlining/outlining variants, parser/frontend
   variation, and a held-out robustness corpus.
4. Add held-out fixtures that stress the saturated in-sample roundtrip ledger and
   keep `check_metrics_fresh` guarding against non-native score relabelling.
5. Decompose one thermo-nuclear maintainability hotspot per sprint, starting
   with `viz/inspection_dashboard.py` or `tools/manuscript_figures.py`, without
   weakening the public-output evidence gates.
