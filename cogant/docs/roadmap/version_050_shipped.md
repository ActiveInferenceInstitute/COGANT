# Version 0.5.0 and wave-21 — Shipped

> This file covers the full arc from v0.1.0 through v0.5.0 (released 2026-04-10)
> plus the wave-21 comprehensive improvement batch (merged 2026-04-13).
> See `CHANGELOG.md` for the authoritative diff-level record.

---

## v0.1.0 (Initial R&D Release — 2026-04-08)

Established the forward pipeline and basic tooling.

- [x] Forward pipeline: ingest → static → normalize → graph → translate → export
- [x] Python AST parser (`cogant.parsers.python`)
- [x] `ProgramGraph` with typed nodes and edges
- [x] 12+ translation rules in 5 families (grew to 22 by wave-21: 5 structural + 5 semantic + 3 control + 4 behavioral + 5 resilience)
- [x] Markov blanket partition (`cogant.markov`), O(V+E), 5 seed strategies
- [x] State space compiler (A/B/C/D matrices from SemanticMappings)
- [x] GNN markdown bundle emission (AII-spec-compliant)
- [x] AII validator scoring 0–100 (all 6 fixtures score 100/100)
- [x] Typer CLI (grew to 26 subcommands by v0.5.0; `cogant --help`)
- [x] `cogant.server.app` FastAPI `/health` + `/translate`
- [x] Dockerfile + docker-compose (EXPOSE 8080)
- [x] mkdocs-material docs site with 20 sections
- [x] 6 Jupyter tutorial notebooks (01–06)
- [x] Hypothesis property tests for 7 correctness laws

---

## v0.2.0 (Reverse Pipeline — 2026-04-09)

Added the reverse synthesis arm and closed the GNN→code→GNN loop.

- [x] `cogant.reverse`: GNN markdown parser, package planner, Python synthesizer, idempotency checker
- [x] `cogant roundtrip` CLI + `ISOMORPHISM_THEOREM.md`: historical Galois-connection proof sketch + bounded-error formalization
- [x] Active Inference agent runtime: `AgentRuntime`, `run_episode`, EFE/VFE metrics
- [x] 12-repo Active Inference example zoo (`examples/zoo/`)
- [x] DAG execution engine with topological sort and cycle detection
- [x] Content-addressed result cache (SHA256 key)
- [x] Entry-point plugin registry (`cogant plugin list/info`)
- [x] Schema versioning + `cogant migrate` CLI subcommand
- [x] YAML rule DSL compiled to Python matchers
- [x] Structured logging + in-process metrics (Counter, Histogram, span)
- [x] `cogant doctor` / `cogant init` / `cogant explain` CLI additions
- [x] Roundtrip role preservation: 14/23 → 19/23 ROLE_PRESERVED (83%) after CONSTRAINT fix

---

## v0.4.0 (Multi-Language + Strict Typing — 2026-04-10)

- [x] JS/TS tree-sitter parser: arrow functions, async, generics, interfaces, decorators
- [x] JS grammar fallback for `.ts` files (prevents hard parse failure on mixed repos)
- [x] Rust PyO3 `connected_components` FFI; `COGANT_USE_RUST=1` feature flag
- [x] `mypy --strict`: 0 errors across 177 source files
- [x] Coverage: 81% total (gate: 75%)
- [x] Tutorial notebooks 01–06 + mkdocs nav update
- [x] Cross-language roundtrip claim: JS Observer → GNN → AI cycle, `role_preservation_score=1.0`
- [x] ROUNDTRIP_EVAL.md: 23-target role-preservation evaluation
- [x] Benchmark dashboard: `evaluation/dashboards/benchmarks.html` (Chart.js)
- [x] CONSTRAINT synthesizer with proportional `check_*` stubs (was fixed 3-4)
- [x] Historical roundtrip role-preservation benchmark: 19/23 → 23/23
      role-preserved targets after POLICY/CONTEXT stub emission; current v0.6
      release metrics require a native refreshed ledger before reusing this as
      fresh evidence

---

## v0.5.0 (Production Hardening — 2026-04-10)

- [x] Incremental analysis: `cogant translate --incremental <git-ref>` / `PipelineConfig.incremental_since`
  - 19.6× no-change speedup, 5.6× single-file speedup on Flask benchmark
- [x] Multi-episode Bayesian learning: `run_multi_episode`, `update_D_from_posterior`, `update_A_from_counts`
- [x] Production FastAPI server with `/health` + `/translate`; full integration test suite
- [x] `cogant doctor` extended: tree-sitter grammar checks, uv lockfile parity, optional-dep audit
- [x] Tutorial notebooks 07–12: Flask walkthrough, constraints, plugins, YAML DSL, multi-episode learning, cross-language roundtrip
- [x] Scaling regression tests: B-tensor, BFS, AST cache, INHERITS edge deduplification guards
- [x] Comprehensive docstring pass + mkdocs nav update + getting started guide
- [x] Manuscript appendices A–E: Galois proof sketch, GNN compliance audit, role-preservation derivation, scaling analysis, cross-language extension
- [x] Historical roundtrip role-preservation benchmark: 23/23 role-preserved
      targets at s_role=1.0; not current native v0.6 evidence until ledger
      refresh

---

## wave-21 (Comprehensive Improvements — 2026-04-13)

The largest single improvement batch since the initial release.

### Translation rules: 19 → 22 total

- [x] `ParameterRule` (control family): detects learnable parameters / hyperparameters → CONTEXT
- [x] `StateMachineRule` (behavioral family): detects FSM patterns → POLICY
- [x] `RateLimiterRule` (resilience family): detects rate-limiting patterns → POLICY
- [x] `TranslationEngine.explain()`, `validate()`, `get_convergence_info()`
- [x] `RuleExplanation.confidence: float` and `contradictions: list[str]`
- [x] max_iterations raised 10 → 100

### Static analysis (`cogant.static`) — all new

- [x] `ComplexityAnalyzer`: cyclomatic + cognitive complexity
- [x] `CouplingAnalyzer`: Martin metrics (Ca, Ce, instability I = Ce/(Ca+Ce), distance from main sequence)
- [x] `DeadCodeDetector`: unused imports/functions/variables with confidence scores (0.95/0.8/0.7)
- [x] `MetricsAnalyzer`: LOC, Halstead metrics (vocabulary, length, volume, difficulty, effort)
- [x] `DataFlowGraph.find_sources()`, `find_sinks()`, `get_taint_paths()`, `to_dict()`
- [x] `SymbolTable.get_public_api()`, `get_entry_points()`, `to_json()`
- [x] `static/AGENTS.md`: 447-line comprehensive guide

### Network/graph analysis (`cogant.graph.analysis`) — all new

- [x] `GraphAnalyzer`: betweenness, PageRank, closeness, degree centrality
- [x] Community detection: Louvain algorithm with component fallback
- [x] Tarjan SCC cycle detection
- [x] Hotspot / source / sink / hub / bottleneck identification
- [x] `GraphDiff` dataclass for incremental diffing
- [x] `GraphMetrics`, `CentralityScores`, `HotspotAnalysis`, `CommunityDetection`, `PathAnalysis` dataclasses
- [x] `queries.py`: `find_by_role()`, `get_neighborhood()`, `filter_by_edge_type()`, `get_interface_nodes()`

### Visualization (`cogant.viz`) — all new files

- [x] `PDFExporter`: 8-page analysis report (program graph, matrices, Markov blanket, pipeline, roundtrip)
- [x] `MatrixVisualizer`: A/B/C/D heatmaps, bar charts, 2×2 combined view
- [x] `PipelineVisualizer`: Mermaid + timing charts + memory usage + stage grid
- [x] `FlowDiagrammer`: CFG / call graph / dependency graph → PNG/PDF/Mermaid
- [x] `StaticAnalysisView`: complexity heatmaps, coupling scatter, Halstead radar, Mermaid pie
- [x] `NetworkView`: degree distribution, centrality ranking, community graphs, adjacency heatmap
- [x] `ExportView`: format size charts, export pipeline diagram
- [x] `mermaid.py`: `render_active_inference_diagram()`, `render_rule_firing_trace()`, `render_markov_blanket()`

### Export (`cogant.export`) — new files + improvements

- [x] `SVGExporter`: DOT language output, graphviz optional fallback
- [x] `JSONSchemaExporter`: draft-7 schemas for GNN bundle, ProgramGraph, SemanticMappings
- [x] `MultiFormatExporter` with `ExportFormat` enum (9 formats: JSON, GRAPHML, PARQUET, SVG, PNG, PDF, MERMAID, DOT, JSONLINES)
- [x] `bundle.py`: `export_zip()`, `export_with_provenance()` with SHA256 hash
- [x] `typed_export.py`: `to_jsonlines()`, `to_arrow_ipc()` (pyarrow optional)
- [x] 4 analysis/export CLI entry points: `cogant analyze-static`, `cogant analyze-graph`, `cogant visualize`, `cogant export` — registered in the v0.5 era and wired to real command paths in the v0.6 hardening pass

### Type infrastructure — all new

- [x] `protocols.py`: 14 `@runtime_checkable` Protocol classes (Translatable, Analyzable, Serializable, Visualizable, Validatable, Exportable, PipelineStage, TranslationRule, GraphBackend, Exportable2, DiagramRenderer, NetworkAnalyzer, ReportGenerator, StaticAnalyzer)
- [x] `types.py`: 15 TypedDicts, 11+ type aliases
- [x] `translate/types.py`: `SemanticRole` Literal (11 values), `RuleFamily` (5), `FixpointStatus` (3), `TranslationTier` (3)
- [x] 231 `.pyi` stubs covering all public modules

### API/Server

- [x] 5 new REST endpoints: `GET /api/v1/rules`, `POST /api/v1/analyze`, `POST /api/v1/roundtrip`, `POST /api/v1/visualize`, `GET /api/v1/metrics`
- [x] WebSocket streaming: `WS /ws/translate`
- [x] 9 new Pydantic v2 models with `ConfigDict(strict=True)`
- [x] `SessionManager` with TTL/cleanup/stats
- [x] `translate_stream()` async generator; `translate_batch()`

### Round-trip / statespace / markov enhancements

- [x] `PackagePlan.validate()`, `diff()`, `to_json()`/`from_json()`
- [x] `synthesize_with_validation()` with `ast.parse` check
- [x] `IdempotencyReport` dataclass; `MatrixSet.validate()`
- [x] `StateSpace.validate()`, `to_summary()`, `compile_incremental()`
- [x] `DegradedOutput` NamedTuple for explicit fallback tracking
- [x] `MarkovBlanket.validate()`, `to_mermaid()`, `merge()`, `get_sensory_states()`, `get_active_states()`

### Test suite expansion

- [x] 14 new test files (~6,600 lines): 10 unit + 4 integration
- [x] Property tests: rule determinism, roundtrip stability, matrix dimension consistency
- [x] Coverage remains ≥83% (canonical: 83.42%)
- [x] Total passing tests: ~2,129

### Documentation

- [x] CHANGELOG.md: full [Unreleased] section documenting all wave improvements
- [x] All "19 rules" references updated to "22 rules" across 20+ files
- [x] 5 AGENTS.md files updated (static, graph, viz, export, server)
- [x] `docs/reference/static_analysis.md`, `docs/reference/network_analysis.md`, `docs/reference/visualization.md`
- [x] All ruff violations fixed: F811, F821, B904, F401, UP037, F541
