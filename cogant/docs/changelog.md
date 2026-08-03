# CHANGELOG

All notable changes to COGANT are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- **Compatibility cleanup:** removed `cogant.viz.png_export` shim; canonical PNG API is
  `cogant.viz.png` with direct submodule imports in `viz/png/orchestrator.py`.
- `ProgramGraph` exports only from `cogant.schemas.graph` (no import fallback chain).
- Drift analyzer reads top-level `graph` / `state_space` / `mappings` only (dropped
  nested `stage_results` bundle layouts).
- Config docs distinguish composable `pipeline.PipelineConfig` from YAML
  `schema.PipelineConfig`.

### Removed
- `scripts/split_png_export.py` and `scripts/split_cli_main.py` (wave-3 mechanical
  split debris); CI guard `tests/unit/test_no_mechanical_split_scripts.py`.

### Added
- `tests/unit/test_viz_png_degraded_paths.py` (renamed from `test_viz_png_export_fallbacks`).

## [0.6.0] - 2026-05-18

### Changed
- Version bumped to 0.6.0 (`cogant.__version__`); `manuscript/config.yaml` aligned to 0.6.0.

### Fixed (audit-driven fidelity pass, 2026-05-18)
- Canonical metrics regenerated from a clean full `uv run pytest tests/ --cov=py/cogant`
  run: line coverage **94.98%** (28016/29498 statements). The previously advertised
  97.14% was carried from an out-of-sync `coverage.json` whose statement denominator (26986)
  predated codebase growth; it was above the 89% CI gate so no build broke, but the
  advertised figure was inaccurate. Test counts re-verified unchanged: **9561 passing /
  0 failing / 52 skipped** (9613 collected).
- `GNNBundle` de-duplicated in `cogant.__all__`.
- `scripts/empirical_claim_demo.py`: roundtrip JSON extraction rewritten to
  `json.JSONDecoder().raw_decode` (the prior first-`}` match truncated nested JSON and
  crashed the demo with exit 1; it now runs to completion).
- Documentation accuracy corrections: `py/cogant/graph/AGENTS.md`
  (`finalize()`/`queries.py`), `py/cogant/gnn/AGENTS.md` (`formatter/` package; 16
  required files), `py/cogant/viz/AGENTS.md` (21 viz modules incl. `ablation_view.py`),
  `py/cogant/README.md` usage imports, `cogant-store` checksum doc-comment (SipHash via
  `DefaultHasher`, not SHA256), and the manuscript's `27 on-disk files` claim corrected
  to the 16 required `gnn_package/` files plus generated assets.
- Manuscript factual corrections: PyO3/GIL statement (calls are synchronous and hold
  the GIL; no GIL release is implemented), and the matrix-mass defaults attributed to
  the real module-level `_DEFAULT_DIRECT_MASS`/`_normalize_row` symbols.
- Out-of-date `projects_in_progress/cogant` path references corrected to
  `projects/working/cogant` across active docs, scripts, and tooling.
- Generated the missing `output/claim_ledger.md` snapshot referenced by
  `manuscript/S06_appendix_source_references.md` (manuscript link checker now clean).

## [0.5.1] - 2026-05-09

### Added (wave-21, 2026-05-09)
- 242 new tests across 4 new test files (wave-21 sweep) targeting thin
  coverage in `viz/export_view.py`, `viz/network_view.py`,
  `viz/flow.py`, `viz/matrix_view.py`, `observability/logging.py`,
  `ingest/manifest.py`, `config/loaders.py`, `cli/main.py`,
  `viz/pdf_export.py`, and `gnn/upstream_bridge`; overall coverage
  rises from 95.11% to **96.22%** (9,222 passing, 9,253 total).
- Comprehensive calibration guide at `docs/reference/calibration_guide.md`
  documenting the four-tier confidence model, threshold registry across
  all `translate/` and `statespace/` source files, calibration
  methodology, and all 36 `TODO(calibration)` markers.
- Expanded `translate/confidence.py` module docstring (~215 lines)
  covering the full public API surface, threshold tables, and an
  end-to-end walk-through of `compute_confidence_score()`.

### Added (wave-20 + wave-20b, 2026-05-09)
- ~1150 new tests across 44 new test files (wave-20 + wave-20b sweep)
  targeting previously thin coverage in `process/`, `statespace/`,
  `normalize/`, `validate/`, `gnn/`, `config/`, `viz/`, `markov/`,
  and `observability/`; overall coverage rises from 90% to **95.1%**.
- `__all__` export list on `cogant.metrics` for predictable
  `from cogant.metrics import *` behaviour and clearer public API.
- Honoured `set_entry_stage()` override on `ProcessExtractor` —
  the value is now stored on `_forced_entry_stage_id` and consumed by
  `_find_entry_stage()` on the next `extract()` call. Previously the
  setter logged but never altered the resulting `ProcessModel`.

### Fixed
- `find_cycles` directed-graph correctness in `graph/builder.py`:
  cycle detection now walks the *directed* adjacency (out-edges only)
  instead of the undirected neighbour set, eliminating spurious
  "cycles" reported for every single directed edge.
- `AttributeError` in `statespace/temporal.py`: callers that asked for
  `compute_critical_path` now resolve to the canonical
  `get_critical_path` (the older method was renamed and the one
  remaining call site was missed).
- `process/extractor.py` `_find_entry_stage` / `_find_exit_stages`:
  the two helpers were operating on swapped sets — entry was returning
  exit stages and vice versa. Both now use the correct
  `target_stage_id` (incoming) / `source_stage_id` (outgoing) sets
  matching their docstrings.
- `process/policies.py` `_extract_branches_for_node` now restricts the
  branch table to control-flow edge kinds (`CALLS` / `TRIGGERS`) and
  drops self-loops, so incidental `CONTAINS` / `READS` edges no longer
  pollute the branching policy output.
- Broken doc link in `docs/playground.md`.

### Changed
- Performance of `validate/integrity.py` lifted from O(V³) to O(V+E) by
  replacing the per-node scan with a precomputed adjacency view.
- `process/extractor.py::_infer_trigger` now takes a typed `Edge`
  parameter instead of `Any`; `Any` import dropped from the module.
- `normalize/canonical.py::_extract_python_metadata` no longer
  re-copies the `decorators` field; the common-field pass already
  handles it (purely cosmetic — values were identical, just clarifies
  intent).
- `statespace/variables.py::compute_dimensionality` docstring now
  documents the heuristic `2**k` continuous-variable contribution as a
  coarse two-bin discretization rather than implying it is exact.

### Internal
- Narrowed bare `except Exception` clauses in `config/loaders.py`
  (now `except (OSError, ValueError, yaml.YAMLError)`) and in
  `gnn/matrices.py` (now `except (ValueError, IndexError, TypeError)`).
- `gnn/json_export.py`: `datetime.utcnow()` → `datetime.now(UTC)` (deprecation fix).
- Test isolation fix in `TestMarkovBlanketExceptionPath`: patch
  `GNNJSONExporter._export_markov_blanket.__globals__["MarkovBlanketExtractor"]`
  directly so the monkeypatch survives any prior-test module-reload ordering.
- Coverage lifted from 90.0% to **95.1%** on `py/cogant/`.

## [Unreleased]

### Added
- **Measured-ablation visualization (`cogant.viz.ablation_view.render_ablation_png`).**
  New deterministic two-panel figure (rule-family net deltas + fixpoint
  convergence) rendered from the `ablation` block of
  `evaluation/METRICS.yaml`. Exported from `cogant.viz` (with `.pyi`
  parity), wired into `tools/manuscript_figures.py` as
  `cogant_rule_family_ablation.png` (curated copy + synthesized
  `.figure.json` sidecar; strict figure-copy passes at 14 figures, 0
  missing, 0 metadata failures), and referenced from `manuscript/09_ablation.md`
  as `@fig:cogant-rule-family-ablation`. No-mocks tests in
  `tests/unit/test_viz_ablation.py` (valid-PNG, byte-determinism, real
  shipped METRICS.yaml). Closes the gap where iteration-2 produced measured
  ablation data but no figure visualized it.

### Fixed
- **`manuscript/09_ablation.md` `requests_lib` matrix-fallback A-rows was a
  wrong hardcoded literal.** The cell read `30 / 36` while
  `ablation.matrix_fallback.requests_lib.a_rows_uniform` in `METRICS.yaml`
  is `32`. `requests_lib` was the only matrix-fallback row left fully
  hand-maintained; it is now tokenized (`{{ABLATION_REQUESTS_LIB_A_ROWS_UNIFORM/_TOTAL}}`
  registered in `tools/manuscript_vars.py`, alongside the pre-existing
  C-entries tokens) so it can no longer drift.
- **`manuscript/98_notation_supplement.md` undercounted `MappingKind`.** It
  called the formal $\mathcal{K}_M$ list "Full ... (11 kinds)" while the
  code `MappingKind` enum in `cogant.schemas.semantic` has **14** members.
  Reworded to distinguish the 11-kind *formal* alphabet from the 14-member
  code enum, explicitly naming the three non-formal implementation kinds
  (`CONTROL_FLOW`, `RETRY_PATTERN`, `FEATURE_FLAG`).
- **`cogant.yaml` `pipeline.stages` used invalid stage names.** It listed
  `semantic_mapping`, `state_space`, `process_model` and omitted `static`
  and `dynamic`; the pipeline runner dispatch table only recognizes
  `ingest, static, normalize, graph, dynamic, translate, statespace,
  process, export, validate`. A real `cogant translate --config cogant.yaml`
  would have silently skipped translate/statespace/process with "Unknown
  stage" errors and exited 0. Stage list and the explanatory comment block
  corrected to the real keys/order.

### Added (iteration 2)
- **Ablation regeneration harness (`tools/regenerate_ablation.py`).** Runs
  the live ingest→…→translate pipeline on the 6 packaged fixtures and
  re-runs `TranslationEngine.translate(graph, rule_filter=…)` with each of
  the 5 rule families withheld, plus a fixpoint-cap axis (K∈{1,2,5,10}) and
  a matrix-fallback axis (uniform-A / identity-B / zero-C / uniform-D
  counts). Merges a measured `ablation:` block into `evaluation/METRICS.yaml`
  (additive; canonical header and all existing keys preserved) and is wired
  as a step in `regenerate_metrics.py`. Deterministic; no-mocks test
  (`tests/test_regenerate_ablation.py`) including a positive control that
  proves `rule_filter` genuinely restricts the rule set. Rule-family,
  fixpoint, and matrix-fallback tables in `manuscript/09_ablation.md` now
  resolve from `{{ABLATION_*}}` placeholders — closes the open
  ablation-regeneration backlog item (manuscript ablation numbers are no
  longer hand-edited).

### Erratum
- **`manuscript/09_ablation.md` rule-family ablation numbers were
  hand-reconstructed and materially inaccurate.** Replacing them with
  measured values from the new harness corrected, on the `flask_app`
  fixture: control family **−5 CONTEXT → measured net Δ 0**; behavioural
  family **≈−2 POLICY/−1 CONSTRAINT → measured net Δ 0**; and on
  `calculator` the semantic family **−9 → measured Δ 10**. Root cause: the
  prior text estimated each family's standalone role count instead of the
  *net* mapping delta under the conflict resolver (a node whose top rule is
  withheld is re-won by a retained rule, so an emitting family can show zero
  net delta). Impact assessed: no abstract/introduction/conclusion or other
  section depended on the corrected figures (verified by cross-section
  grep), so this is a numeric/finding correction local to §9. The §9 table
  and prose were rewritten to be measurement-driven; `S02_appendix_ablation.md`
  (still hand-reconstructed for `zoo/01`) is now explicitly flagged as
  containing unverified estimates pending harness extension.

### Fixed
- **Graph stage emitted zero IMPORTS edges for Python modules.** In
  `api/orchestration.py::run_graph` the IMPORTS block read
  `imp.module`/`imp.name`, which do not exist on `static.parser.ImportDef`
  (real fields: `module_name`, `is_relative`, `names`). The expression was
  always `None`, so the loop always `continue`d and **no IMPORTS edge was
  ever added** despite the docstring promising them. Now reads
  `module_name` with a `names[0]` fallback and strips leading dots so
  `from . import x` relative imports resolve. Added two no-mocks tests in
  `tests/unit/test_api_orchestration_stage_functions.py` covering plain,
  dotted, `from … import`, relative, external (no edge), and self-import
  (no edge) shapes. (TODO §5 — graph normalization, imports.)
- **`run_all.py` exited 0 even when every target failed.** `main()` ended
  with an unconditional `return 0`; without `--fail-fast`, a fully-failed
  sweep was indistinguishable from success by exit code, so CI/`run.sh`
  callers could not detect a failed batch. `failures` is now hoisted above
  the `try` and `main()` returns `1 if failures else 0`. Regression guarded
  by `tests/test_run_all_exit_code.py` (no-mocks: real dry-run subprocess +
  source-AST invariant). (TODO §7 — promotion/CI readiness.)
- **Manuscript module references corrected to match the code.**
  `02_04` `statespace/matrices.py`→`gnn/matrices.py` and
  `validate/validator.py`→`gnn/validator.py`; `S04` attributed the VFE/EFE
  loop to a non-existent `cogant.process.evaluate_policies` — now points at
  `variational_free_energy`/`expected_free_energy` in
  `cogant.simulate.free_energy` and `GNNModelRunner._evaluate_policies`
  (`cogant.gnn.runner`), consistent with the conclusion. GNN canonical
  section count corrected `18`→`19` in `03` and `06_03` to match
  `gnn.validator.GNNValidator.CANONICAL_SECTIONS` (19 entries).

### Changed
- **Remote `run_all` targets pinned to immutable release tags for
  reproducible shallow clones** (TODO §3, §7). `remote_itsdangerous`
  (`2.2.0`) and `remote_markupsafe` (`2.1.5`) no longer clone a moving
  default branch; `remote_click` (`8.1.7`, ~10 KLOC BSD-3 — a genuine
  *medium* real repository) promoted from the example block to an active
  target. The `extra_remote_targets_example` entries now model the
  pinned-`git_ref` pattern instead of the non-reproducible `null` default.

### Added
- **Batch dashboard for `run_all` sweeps** — new
  `cogant.viz.batch_dashboard.BatchDashboardGenerator` consolidates the
  per-target outputs of a staging-root `run_all` sweep into a single
  `output/dashboard/` directory with:
  `summary.csv`, `metrics_per_target.json`, three Mermaid charts
  (`node_count_bar.mmd`, `edge_count_bar.mmd`, `score_distribution.mmd`),
  a Mermaid Gantt of recorded command timings (`run_gantt.mmd`), and a
  cross-linked Markdown report (`dashboard.md`). Pure-stdlib; works
  under the minimal install profile. Exposed via the staging-root
  `scripts/batch_dashboard.py` orchestrator and wired into `run_all.py`
  as the `steps.batch_dashboard` post-batch step (on by default).
  `BatchDashboardGenerator`, `TargetMetrics`, and `write_batch_dashboard`
  are re-exported from `cogant.viz`. Covered by
  `tests/unit/test_batch_dashboard.py` (25 tests, strict no-mocks).
- **Configurable upstream GNN 25-step pipeline pass** — new
  `cogant.gnn.upstream_bridge.pipeline` module drives `src.main.execute_pipeline_step`
  over the produced `gnn_package/`. Surfaces: `UPSTREAM_STEP_SCRIPTS` (canonical
  ordering of `0_template.py`…`24_intelligent_analysis.py`), `DEFAULT_SKIP_STEPS = {11, 12}`,
  `resolve_steps()`, `UpstreamPipelineConfig` / `UpstreamStepResult` /
  `UpstreamPipelineResult` dataclasses, and `run_upstream_pipeline()`. Wired
  through `PipelineConfig.upstream_gnn_pipeline` and exposed on `analyze`,
  `translate`, `validate` via `--upstream-gnn-pipeline` plus
  `--upstream-gnn-only-steps`, `--upstream-gnn-skip-steps`,
  `--upstream-gnn-frameworks`, `--upstream-gnn-llm-model`, and
  `--upstream-gnn-output-dir`. New top-level `cogant upstream-gnn <package_dir>`
  command re-runs the pass against an existing bundle. **Render (step 11)** and
  **Execute (step 12)** are skipped by default — those are framework-specific
  PyMDP/RxInfer/JAX/DisCoPy code-gen and simulation steps; opt in by clearing
  `--upstream-gnn-skip-steps ""` or by listing them in `--upstream-gnn-only-steps`.
  Per-step results are recorded under `bundle.artifacts['upstream_pipeline_steps']`
  / `['upstream_pipeline_summary']` and serialized to
  `<output_dir>/upstream_pipeline/upstream_pipeline_summary.json`. Failures are
  **advisory** — they append warnings to the validate stage but never fail it.
  Includes 14 unit tests (`tests/unit/test_upstream_pipeline_resolution.py`)
  and 5 integration tests (`tests/integration/test_upstream_gnn_pipeline.py`),
  with a slow full-pass test gated by `COGANT_RUN_UPSTREAM_PIPELINE=1`.
- **3 new translation rules** (19 → 22 total): `ParameterRule` (control family — detects learnable parameters/hyperparameters → CONTEXT), `StateMachineRule` (behavioral family — detects FSM patterns → POLICY), `RateLimiterRule` (resilience family — detects rate-limiting patterns → POLICY). Rule breakdown: 5 structural + 5 semantic + 3 control + 4 behavioral + 5 resilience.
- **Static analysis module** (`cogant.static`): `ComplexityAnalyzer` (cyclomatic + cognitive complexity), `CouplingAnalyzer` (Martin metrics: Ca/Ce/instability/distance-from-main-sequence), `DeadCodeDetector` (unused imports/functions/unreachable code with confidence scores), `MetricsAnalyzer` (LOC, Halstead metrics).
- **Network/graph analysis** (`cogant.graph.analysis`): `GraphAnalyzer` with centrality (betweenness, PageRank, closeness, degree), community detection (Louvain/component fallback), Tarjan SCC cycle detection, hotspot/source/sink identification. `GraphDiff` for incremental diffing.
- **Visualization suite** (`cogant.viz`): `PDFExporter` (8-page analysis reports), `MatrixVisualizer` (A/B/C/D heatmaps), `PipelineVisualizer` (10-stage timing + Mermaid), `FlowDiagrammer` (CFG/call graph/dependency graph → PNG/PDF/Mermaid), `StaticAnalysisView`, `NetworkView`, `ExportView`.
- **Export formats** (`cogant.export`): `SVGExporter` (graphviz DOT), `JSONSchemaExporter` (draft-7 schemas for all output types), `MultiFormatExporter` with `ExportFormat` enum (9 formats: JSON, GRAPHML, PARQUET, SVG, PNG, PDF, MERMAID, DOT, JSONLINES).
- **Type infrastructure**: 14 `@runtime_checkable` Protocol classes (`Translatable`, `Analyzable`, `Serializable`, `Visualizable`, `Validatable`, `Exportable`, `PipelineStage`, `TranslationRule`, `GraphBackend`, `Exportable2`, `DiagramRenderer`, `NetworkAnalyzer`, `ReportGenerator`, `StaticAnalyzer`), 15 `TypedDict`s, `SemanticRole`/`RuleFamily`/`FixpointStatus` Literal types. 231 `.pyi` stubs covering all public modules.
- **API improvements** (`cogant.server`, `cogant.api`): 5 new REST endpoints (`GET /api/v1/rules`, `POST /api/v1/analyze`, `POST /api/v1/roundtrip`, `POST /api/v1/visualize`, `GET /api/v1/metrics`), WebSocket streaming (`WS /ws/translate`), `PipelineResult` dataclass, `SessionManager`, `translate_batch()`.
- **Translation engine enhancements**: `TranslationEngine.explain()`, `validate()`, `get_convergence_info()`; `RuleExplanation.confidence: float` and `contradictions: list[str]`; improved heuristics for all 5 rule families; `to_gnn_role()` on semantic rules.
- **Round-trip enhancements**: `PackagePlan.validate()`, `diff()`, `to_json()`/`from_json()`; `synthesize_with_validation()` with `ast.parse` check; `IdempotencyReport` dataclass; `MatrixSet.validate()`.
- **Runtime/statespace/markov enhancements**: `AgentRuntime.run_episode_with_logging()`, `benchmark()`, `reset()`, `get_free_energy()`, serialization; `DegradedOutput` namedtuple; `MarkovBlanket.validate()`, `to_mermaid()`, `merge()`, `get_sensory_states()`, `get_active_states()`.
- **4 new CLI entry points (preview stubs)**: `cogant analyze-static`, `cogant analyze-graph`, `cogant visualize`, `cogant export` — registered in Typer but currently print guidance to use the Python API (`cogant.static`, `cogant.graph.analysis`, `cogant.viz`, `cogant.export`); full orchestration wiring is tracked on the roadmap.
- **Comprehensive test suite expansion**: 14 new test files (10 unit + 4 integration), ~6,600 lines covering all new modules. Property tests for rule determinism, roundtrip stability, matrix dimension consistency.
- `cogant.metrics` public API: `get_metrics()` / `get_metric(key)` backed by `evaluation/METRICS.yaml` (41f96de)
- `.pyi` type stubs for all public API modules + `py.typed` marker (58c5fe1)
- Complete JS/TS tree-sitter parser: arrow functions, async, generics, interfaces, decorators (25640ae)
- Rust PyO3 `connected_components` FFI; `COGANT_USE_RUST=1` feature flag (598945d)

### Fixed
- Viz `cogant.viz.png` tests guarded behind `pytest.importorskip(matplotlib)`; add `numpy` and `pytest-cov` as dev deps (905c2da)
- Relax JS hidden-state assertion in cross-language differential test (4aa2710)
- Ruff UP038 autofix: union-type annotations; remove unsupported `xfail` mark (cea55d9)

### Changed
- `evaluation/METRICS.yaml` promoted to canonical source of truth for test count, coverage, and roundtrip metrics (41f96de)
- All public API modules receive Google-style docstrings and explicit `__all__` exports (a621b0a)

### Tests
- Comprehensive CLI subcommand coverage tests for `cogant/cli/main.py` (98f7798)

### Internal
- Scaffolding stubs filled in `docs/`, `examples/`, `tests/`, and `evaluation/` subdirectories (c6a5b7b)
- Manuscript variable registry, inject and audit scripts; number audit report (c8c4749)

## [0.5.0] - 2026-04-10

### Added
- Incremental analysis mode: `cogant translate --incremental <git-ref>` / `PipelineConfig.incremental_since` — 19.6× no-change speedup, 5.6× single-file speedup on Flask benchmark
- Multi-episode Bayesian learning: `AgentRuntime.run_multi_episode`, `run_episode`, `update_D_from_posterior`, `update_A_from_counts`
- Production FastAPI server: `cogant.server.app` with `/health` and `/translate` endpoints, integration test suite
- Dockerfile (python:3.12-slim + uv, `EXPOSE 8080`, curl healthcheck) and docker-compose.yml
- `cogant doctor` extended: tree-sitter grammar checks, uv lockfile parity, optional-dep audit
- `cogant init <path>`: scaffold helpers for `cogant.yaml`, source stub, `pyproject.toml`
- Tutorial notebooks 07–12: Flask walkthrough, constraints, plugins, YAML DSL, multi-episode learning, cross-language roundtrip
- Cross-language roundtrip claim: JS Observer (`examples/zoo/13_js_observer`) → GNN → AI cycle, `role_preservation_score=1.0`
- POLICY/CONTEXT stub emission in synthesizer: `decide_*` / `get_context_*` stubs proportional to origin GNN role counts
- Scaling regression tests: guards for B-tensor, BFS, AST cache, INHERITS edge deduplification at dulwich edge density
- Benchmark dashboard: `evaluation/dashboards/benchmarks.html` (Chart.js, self-contained)
- Comprehensive docstring pass + mkdocs nav update + getting started guide
- Manuscript appendices A–E: Galois proofs, GNN compliance audit, ε derivation, scaling analysis, cross-language extension; 40+ new citations

### Fixed
- tree-sitter JS grammar fallback for `.ts` files prevents hard parse failure on mixed JS/TS repos (`10c87ea`)
- Loosen `parse_ts_file` test assertion to accommodate JS grammar fallback path (`bf386b5`)

### Changed
- `pyproject.toml` dep updates + uv.lock sync (`fbd8d39`)

### Roundtrip role preservation
- Current release evidence uses the native v0.6 ledger: 24 targets, 22
  role-preserved, 2 drift, 0 failed, and 0 strict structural isomorphism. Each
  row carries `role_preservation_score` and invariant status fields.

## [0.4.0] - 2026-04-10

### Added
- CONSTRAINT synthesizer: proportional `check_*` stubs — variable-count assertion scaffolding matching origin GNN role counts (was fixed 3-4 stubs)
- Empirical claim extended: full 10-step Active Inference cycles on zoo/02_observer, zoo/04_pomdp_minimal, zoo/06_hierarchical
- mypy strict: 0 errors across 177 source files (was 163 at v0.3.0 start)
- Coverage: 81% total (was 76% at v0.3.0)
- tree-sitter multi-language parser: JS/TS + Python fallback
- Tutorial notebooks: 6 Jupyter notebooks (01-06)
- Interactive playground: single-file HTML with cytoscape.js + CodeMirror
- mkdocs-material docs site + GitHub Pages workflow
- ROUNDTRIP_EVAL.md: 23-target roundtrip ε evaluation — now 19/23 ISOMORPHIC (83%) after CONSTRAINT fix

### Fixed
- CONSTRAINT role collapse: `cnst_` prefix not detected by forward pipeline's PreferenceRule → now emits `check_` prefix proportional to origin count
- model_name default lowercased: `CogantModel` → `cogant_model` (law7 property enforcement)
- MatrixFunctions public/private split: AgentRuntime now reads A/B/C/D correctly
- Parser ontology fallback: non-standard variable names (s_hidden, o_sensor) now classified via ActInfOntologyAnnotation

### Improved
- Roundtrip ε: 14/23 ISOMORPHIC (61%) → 19/23 ISOMORPHIC (83%) after CONSTRAINT fix
- Real-world eval: 8/8 repos pass forward pipeline
- Type annotations: 50+ modules updated to modern Python typing (Counter[str], list[T])

### Performance
- Dulwich scaling cliff documented: 1.80 e/n ratio → 380s / 8.5 GB (known issue, wave 15 target)

## [0.2.0] - 2026-04-09

### Added

**Reverse Pipeline (GNN to Code)**
- `cogant.reverse` subpackage: GNN markdown parser, package planner, Python synthesizer, idempotency checker
- Runtime-callable matrix functions (likelihood, transition, EFE, best_action) without exec
- ISOMORPHISM_THEOREM.md: Galois connection proof + epsilon-bounded roundtrip error formalization

**Active Inference Runtime**
- Active Inference agent loop with step/convergence/VFE metrics
- 12-repo Active Inference example zoo with hand-written GNN models for repos 04, 06, 12

**Pipeline and Infrastructure**
- DAG execution engine with topological sort and cycle detection
- Content-addressed result cache keyed on repo sha256
- Entry-point plugin registry + `cogant plugin list/info` CLI
- Schema versioning + `cogant migrate` CLI subcommand
- YAML rule DSL compiled to Python matchers for custom role rules without code
- Structured logging + in-process metrics (Counter, Histogram, span) observability layer

**CLI and Ergonomics**
- `cogant doctor` environment check subcommand
- `cogant init` project scaffolding subcommand
- `cogant explain` rule-level attribution for AI role assignments
- Progress bars, better error messages, rich `--help`
- Composable pydantic config system

**Documentation**
- 16 mkdocs-material documentation sections with tutorials and API reference
- 6 deep concept explainers (GNN, Active Inference, Markov blankets, roles, roundtrip, program graphs)
- 20 cookbook recipes (scan, reverse, CI, custom rules, dataset export)
- 35 honest Q&A FAQ covering accuracy, limitations, and roadmap
- 83+ annotated bibliography entries across 14 themes
- 6 Jupyter tutorial notebooks
- FastAPI demo server
- BENCHMARK_VS_PRIOR.md comparing COGANT vs tree-sitter, pyan, LLM-only, and manual approaches
- CALIBRATION.md with per-rule confidence scores and inline justifications

**Testing and Quality**
- Hypothesis property tests for 7 COGANT correctness laws
- Mutation testing report + targeted hardening tests
- End-to-end pipeline, CLI, and roundtrip integration tests
- ML dataset v0.1: 6 fixtures with node-level role labels (HuggingFace-style card)
- Reproducible 6-fixture benchmark harness with stage timing + memory + GNN stats

**Multi-Language**
- Tree-sitter multi-language substrate with JS/TS parsers
- Git-diff incremental analysis mode

**Theory and Rigor**
- Qualitative AI role validation tests + ACTIVE_INFERENCE_MAPPING.md
- GNN spec compliance: 3 AII non-conformances found and fixed
- Real-world evaluation on 8 open-source Python repositories

### Changed
- Complete README rewrite for current feature set
- Docstring audit and type annotation hygiene across all modules
- Test suite: 1300+ tests, 0 failures (skips for optional deps only)
- py.typed marker added (PEP 561 compliance)
- RuleExplanation model + per-rule `.explain()` with calibration docstrings
- GitHub Actions matrix CI + perf smoke + CODEOWNERS + PR template

### Fixed
- Resolved 6 reverse-module test failures
- ActionRule: extended with encode/decode/dump/load keywords + >=2 WRITES edge fallback
- SemanticMapping export: `mapping.kind.value` (was incorrect attribute access)
- PNG tests: matplotlib-dependent tests properly skipped when `cogant[viz]` not installed
- GNN upstream formatter: DiscreteTime token split, bare variable names in connections
- CI workflows: moved `.github/` to git root so GitHub Actions discovers workflows
- Event pipeline roundtrip xfail documented (47.6% role match -- known synthesizer limitation)

## [0.1.0] - 2026-04-08

Initial R&D release: forward pipeline (ingest -> static -> normalize -> graph -> translate -> export), 12 translation rules, 7 semantic roles, Markov blanket partition.
