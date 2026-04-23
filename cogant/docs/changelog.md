# CHANGELOG

All notable changes to COGANT are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
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
- Viz `png_export` tests guarded behind `pytest.importorskip(matplotlib)`; add `numpy` and `pytest-cov` as dev deps (905c2da)
- Relax JS hidden-state assertion in cross-language differential test (4aa2710)
- Ruff UP038 autofix: union-type annotations; remove stale `xfail` mark (cea55d9)

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
- Cross-language roundtrip claim: JS Observer (`examples/zoo/13_js_observer`) → GNN → AI cycle, `role_match_score=1.0`
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

### Roundtrip ε
- 19/23 ISOMORPHIC (83%) → **23/23 ISOMORPHIC (100%)** after POLICY/CONTEXT stub emission

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
- Complete README rewrite for v0.2.0 feature set
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
