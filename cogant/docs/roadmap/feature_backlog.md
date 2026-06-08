# Feature Backlog

Last updated: 2026-06-06 (v0.6.0). Items are grouped by status and priority.
The authoritative source for what is **shipped** is `CHANGELOG.md` and `evaluation/METRICS.yaml`.

---

## Implemented Capabilities

These items are implemented and tested in the current tree.

| Item | Shipped in | Notes |
|------|-----------|-------|
| JS/TS tree-sitter parser (arrow fns, async, generics, interfaces, decorators) | v0.4.0 | JS grammar fallback for `.ts` |
| Rust PyO3 `connected_components` FFI; `COGANT_USE_RUST=1` gate | v0.4.0 | Pure-Python fallback default |
| Incremental analysis: `--incremental <git-ref>` / `PipelineConfig.incremental_since` | v0.5.0 | 19.6× no-change, 5.6× single-file speedup on Flask |
| Multi-episode Bayesian learning: `run_multi_episode`, `update_D_from_posterior`, `update_A_from_counts` | v0.5.0 | |
| Production FastAPI server with `/health` + `/translate`; Dockerfile + docker-compose | v0.5.0 | EXPOSE 8080 |
| Roundtrip role-preservation benchmark | v0.6.0 | Native v0.6 ledger records 24/24 ROLE_PRESERVED, 0/24 DRIFT, 0 non-native rows, and 0 strict structural-isomorphism rows |
| Parquet export (`cogant.export.parquet`) | wave-21 | PyArrow optional dep |
| Static analysis module: `ComplexityAnalyzer`, `CouplingAnalyzer`, `DeadCodeDetector`, `MetricsAnalyzer` | wave-21 | Halstead, Martin metrics |
| Network/graph analysis: `GraphAnalyzer` with centrality, community detection, Tarjan SCC | wave-21 | Louvain + component fallback |
| Visualization suite: `PDFExporter`, `MatrixVisualizer`, `PipelineVisualizer`, `FlowDiagrammer` | wave-21 | 8-page PDF report |
| Export formats: `SVGExporter`, `JSONSchemaExporter`, `MultiFormatExporter` (9 formats) | wave-21 | Graceful dep fallback |
| 14 `@runtime_checkable` Protocol classes; 15 TypedDicts; Literal type aliases | wave-21 | 231 .pyi stubs |
| 5 new REST endpoints + WebSocket streaming; `SessionManager`; `translate_batch()` | wave-21 | |
| `AgentRuntime`: `run_episode_with_logging()`, `benchmark()`, `reset()`, `get_free_energy()` | wave-21 | |
| `MarkovBlanket`: `validate()`, `to_mermaid()`, `merge()`, `get_sensory_states()` | wave-21 | |
| 3 new translation rules: `ParameterRule`, `StateMachineRule`, `RateLimiterRule` (19 → 22 total) | wave-21 | |
| 4 analysis/export CLI commands: `analyze-static`, `analyze-graph`, `visualize`, `export` | v0.6 hardening | Real command paths now cover static metrics, graph analysis, visualization, and exports |
| `cogant.metrics` public API: `get_metrics()` / `get_metric(key)` from `METRICS.yaml` | wave-21 | |
| Content-addressed result cache keyed on repo SHA256 | v0.2.0 | |
| Hypothesis property tests (7 COGANT correctness laws) | v0.2.0 | |
| YAML rule DSL compiled to Python matchers | v0.2.0 | |
| Tutorial Jupyter notebooks 01–12 | v0.4.0–v0.5.0 | |
| mkdocs-material docs site with 20 sections | v0.2.0 | |

---

## Backlog — High Priority (next minor: v0.6.x)

### 1. Java parser (tree-sitter)
**Effort:** L | **Complexity:** medium | **Value:** high
Full tree-sitter Java parser with type-inference integration. Priority because Java is the #1 language in enterprise codebases that most benefit from Active Inference modeling.
- [ ] `parsers/java.py` with `JavaParser` and `JavaSymbolExtractor`
- [ ] Java-specific translation rules (Spring/DI patterns → POLICY, JPA → HIDDEN_STATE)
- [ ] Cross-language tests comparing Java vs Python roundtrip ε

### 2. Rust parser (tree-sitter)
**Effort:** M | **Complexity:** medium | **Value:** high
Given the existing Rust workspace, a Rust parser is natural. Ownership/borrowing semantics map cleanly onto Active Inference precision weighting.
- [ ] `parsers/rust_parser.py` (tree-sitter-rust grammar)
- [ ] Ownership annotations → CONSTRAINT mappings
- [ ] Trait implementations → OBSERVATION/ACTION role heuristics

### 3. Streaming export for large graphs (>100k nodes)
**Effort:** M | **Complexity:** medium | **Value:** high
Current Parquet/JSONLINES/GraphML exporters build full in-memory structures. Streaming versions needed for production repo analysis.
- [ ] Chunked Parquet writer using PyArrow `RecordBatchWriter`
- [ ] Streaming GraphML: emit nodes pass then edges pass
- [ ] JSONLINES streaming with per-batch flush
- [ ] Benchmark on 100k, 500k, 1M-node graphs

### 4. Dynamic analysis integration {#4}
**Effort:** XL | **Complexity:** high | **Value:** very high
Static analysis alone misses runtime dispatch, monkey-patching, and probabilistic branching. Combining static + runtime traces dramatically improves confidence scores.
- [ ] Coverage-trace ingestion (`cogant.dynamic.trace_loader`)
- [ ] Call-sequence-based rule refinement (observed transitions update A matrix)
- [ ] `ConfidenceTier.STATIC_PLUS_RUNTIME` promotion path from runtime traces
- [ ] `PipelineConfig.trace_paths: list[Path]` for trace injection
- [ ] Integration with Python coverage (`coverage.py`) and profiling (`cProfile`)

### 5. Type inference engine (intra-procedural)
**Effort:** L | **Complexity:** medium | **Value:** high
Currently reliant on explicit annotations. Intra-procedural type inference (Hindley-Milner-lite for Python) would reduce `OBSERVATION` false negatives for un-annotated codebases.
- [ ] `cogant.static.type_inference.TypeInferrer`
- [ ] Propagate literal types, return-type narrowing, attribute access chains
- [ ] Integrate into `ComplexityAnalyzer` and translation rules
- [ ] Benchmark annotation coverage improvement on real-world repos

### 6. Cross-repository analysis
**Effort:** XL | **Complexity:** high | **Value:** high
Many real systems span multiple repos (microservices, monorepos with multiple packages). Cross-repo edges would let COGANT model service boundaries as Markov blanket boundaries.
- [ ] Multi-root `ProgramGraph` with `INTER_REPO` edge kind
- [ ] Shared symbol registry across multiple `cogant translate` runs
- [ ] `cogant translate --repo-root A --repo-root B` CLI multi-target
- [ ] `MarkovBlanket.from_service_boundary()` seed strategy

### 7. Alias analysis
**Effort:** M | **Complexity:** high | **Value:** medium
Assignment aliasing (`x = y`) creates false WRITES edges. Alias tracking would reduce graph noise and improve precision of `MutatingSubsystemRule` and `DataPipelineRule`.
- [ ] Flow-insensitive alias set computation
- [ ] Merge alias sets through `READS`/`WRITES` edge propagation
- [ ] Prune redundant edges in `ProgramGraph`

---

## Backlog — Medium Priority (v0.7.x–v0.8.x)

### 8. VSCode extension
**Effort:** L | **Complexity:** medium | **Value:** high (developer experience)
- [ ] Language server protocol integration: hover → show SemanticRole
- [ ] Inline gutter icons for translation rule matches
- [ ] "Export to GNN" command palette entry
- [ ] Depends on: stable public API (v1.0 freeze target)

### 9. Interactive web dashboard
**Effort:** M | **Complexity:** medium | **Value:** medium
Current `cogant render` HTML is static. Interactive graph exploration would accelerate adoption.
- [ ] Cytoscape.js or D3-force layout with filter controls
- [ ] Role-color overlay toggle (HIDDEN_STATE/OBSERVATION/ACTION)
- [ ] Markov blanket boundary highlighting
- [ ] Drill-down from graph node → source file + line number

### 10. Plugin / rule registry
**Effort:** M | **Complexity:** medium | **Value:** high
Entry-point plugin system exists (v0.2.0) but rule registration is still manual. A registry would let third parties ship custom rule families without forking.
- [ ] `cogant.plugins.RulePlugin` ABC + `cogant_rules` entry-point group
- [ ] Hot-reload rules without restart (dev mode)
- [ ] Rule conflict resolution policy (priority/override/merge)
- [ ] Plugin marketplace docs

### 11. Dataflow analysis (interprocedural)
**Effort:** XL | **Complexity:** very high | **Value:** high
Taint/reach analysis across call boundaries. Needed to correctly classify HIDDEN_STATE variables that are written in one function and read in another.
- [ ] Callgraph construction from `graph/` edges
- [ ] Interprocedural READS/WRITES propagation
- [ ] Taint source/sink labelling integration with `DataFlowGraph`
- [ ] `TranslationRule.with_dataflow()` mixin

### 12. C/C++ parser (tree-sitter)
**Effort:** L | **Complexity:** medium | **Value:** medium
Enables COGANT analysis of systems-level code, robotics firmware, and ML inference engines written in C++.
- [ ] tree-sitter-c / tree-sitter-cpp grammar wiring
- [ ] Macro expansion stubs (limited)
- [ ] C++ class → HIDDEN_STATE heuristics

### 13. DuckDB query interface
**Effort:** S | **Complexity:** low | **Value:** medium
Parquet export already works. A thin DuckDB wrapper would let analysts run SQL on exported graph data without leaving the `cogant` CLI.
- [ ] `cogant query "SELECT * FROM nodes WHERE role='HIDDEN_STATE'"` subcommand
- [ ] Auto-load from latest bundle's Parquet files
- [ ] Export query results as CSV/JSON

### 14. Schema versioning + migration (hardening)
**Effort:** M | **Complexity:** medium | **Value:** medium
`cogant migrate` subcommand exists. Full versioned schema registry with forward/back migration would let bundles survive version upgrades.
- [ ] `BundleManifest.schema_version` bump policy
- [ ] Automated migration tests for v0.1→v0.5→v1.0 bundles
- [ ] `cogant validate-bundle` with schema version check

---

## Backlog — Lower Priority (v0.9.x / post-1.0)

### 15. Distributed / parallel file processing
**Effort:** XL | **Complexity:** very high | **Value:** medium
Multiprocess pipeline for repos >500 files. Ray or ProcessPoolExecutor sharding of `ingest` + `parsers` stages.
- [ ] File-level parallelism in `pipeline/stages.py`
- [ ] Shared `ProgramGraph` builder with merge step
- [ ] Benchmark: worker count vs. throughput scaling

### 16. Cloud/serverless deployment
**Effort:** M | **Complexity:** medium | **Value:** medium
- [ ] AWS Lambda handler for `translate` endpoint
- [ ] GCP Cloud Run deployment docs
- [ ] Terraform module for auto-scaling inference cluster

### 17. Pre-trained GNN node encoder
**Effort:** XL | **Complexity:** very high | **Value:** high (long-term)
Train a GNN on COGANT's own exported graphs to learn semantic embeddings. Would bootstrap the `CONTEXT` role assignment with learned representations.
- [ ] PyG `HeteroData` loader from Parquet bundles
- [ ] Message-passing GNN trained on role labels
- [ ] `cogant.ml.encoder.GNNEncoder` with `.embed(graph)` → node embeddings
- [ ] Integration with translation rule confidence scoring

### 18. Real-time / LSP analysis (live code)
**Effort:** XL | **Complexity:** very high | **Value:** medium
Incremental analysis on keystroke events via LSP. Would power IDE inline feedback.
- [ ] Dependency on VSCode extension (#8 above)
- [ ] Incremental partial parse triggered by file-save events
- [ ] Debounced rule evaluation for open documents

### 19. Custom ML models bundled with GNN
**Effort:** XL | **Complexity:** very high | **Value:** medium
Allow users to attach trained classifiers (e.g. a fine-tuned CodeBERT) as additional confidence sources for translation rules.
- [ ] `ExternalClassifier` Protocol in `protocols.py`
- [ ] `ConfidenceModel.with_classifier()` fusion method
- [ ] Serialization of classifier config into bundle manifest

---

## Refactoring / Streamlining Targets

These are internal quality items that don't add user-facing features but reduce entropy and technical debt.

### R1. Consolidate `cogant/` dual-directory confusion (sidecar -> template render path)
**Priority:** High | **Effort:** S
The sidecar-root / package-root split (`projects/working/cogant/` vs `projects/working/cogant/cogant/`) creates orientation cost for every new contributor. The render-location checklist in `PROMOTION.md` should stay current before any public beta.
- [ ] Verify sidecar/template linking exposes `projects/working/cogant`
- [ ] Fix any remaining hard-coded render-path literals in docs, scripts, CI
- [ ] Verify `./run.sh` and `scripts/execute_pipeline.py` discover the project
- [ ] End-to-end PDF rendering via `scripts/03_render_pdf.py --project working/cogant`

### R2. Flatten roadmap version docs to reflect actual release history
**Priority:** High | **Effort:** S
Roadmap docs still describe v0.1.0 as "current". All version plan files need to be updated to match CHANGELOG reality (v0.5.0 shipped).
- [ ] Rename `version_010_current.md` → `version_010_shipped.md`
- [ ] Write `version_060_planned.md` (see dedicated file)
- [ ] Write `version_100_planned.md` with hardening/public API freeze scope

### R3. Decouple `cogant.viz` matplotlib imports at module level
**Priority:** Medium | **Effort:** S
Several `viz/` modules do `import matplotlib.pyplot as plt` at module level, causing `ImportError` on bare install. All viz imports should be gated inside functions with graceful fallback.
- [ ] Audit all `import matplotlib`, `import PIL`, `import reportlab` at module level
- [ ] Wrap each in `try/except ImportError` with `cogant[viz]` hint message
- [ ] Add `pytest.importorskip("matplotlib")` guards to all affected tests

### R4. Reduce `translate/rules/` duplication in heuristic keyword lists
**Priority:** Medium | **Effort:** M
All 22 rule classes maintain their own keyword lists as module-level constants. Extracting a shared `cogant.translate.vocabulary` module would let rules compose heuristics and simplify addition of new rule families.
- [ ] `cogant/translate/vocabulary.py`: `OBSERVATION_KEYWORDS`, `ACTION_VERBS`, `STATE_NOUNS`, etc.
- [ ] Refactor all 22 rule `matches()` methods to use shared vocabulary
- [ ] Add property tests: no keyword appears in two competing role lists

### R5. Unify confidence computation across static and runtime paths
**Priority:** Medium | **Effort:** M
`ConfidenceModel` (translate) and the static analysis confidence scores (dead code: 0.95/0.8/0.7) use different scales and models. A unified `CogantConfidence` abstraction would let all evidence sources compose cleanly.
- [ ] `cogant/confidence.py`: `ConfidenceScore`, `EvidenceSource`, `fuse_scores()` using log-odds
- [ ] Migrate `ConfidenceModel`, `DeadCodeDetector`, `GraphAnalyzer` to unified type
- [ ] Update `BundleManifest.validation_score` to use the same scale

### R6. Replace `@dataclass` with `@dataclass(slots=True)` throughout
**Priority:** Low | **Effort:** S
Python 3.11+ `__slots__` on dataclasses reduces memory significantly for large graphs (many thousands of `SemanticMapping`, `NodeAttrs` instances). Simple mechanical change.
- [ ] Enable `slots=True` on `SemanticMapping`, `NodeAttrs`, `EdgeAttrs`, `AgentConfig`, `EpisodeMetrics`
- [ ] Verify no dynamic attribute assignment breaks (mypy catches most)
- [ ] Benchmark: memory reduction on `flask_app` fixture graph

### R7. Converge `.pyi` stub generation to `stubgen` + CI check
**Priority:** Medium | **Effort:** M
231 `.pyi` stubs are hand-maintained and drift on refactors. Auto-generating them via `mypy --stubgen` and checking in a CI diff would prevent silent type regressions.
- [ ] `make gen-stubs` target: `mypy.stubgen --package cogant -o stubs/`
- [ ] CI job: run `gen-stubs`, diff against checked-in stubs, fail on unexpected delta
- [ ] Decide: hand-curated stubs (more precise) vs. generated (less drift)

---

## Won't Fix / Out of Scope {#wont-fix--out-of-scope}

| Item | Reason |
|------|--------|
| PyTorch Geometric exporter | GNN term refers to Generalized Notation Notation (AII spec), not Graph Neural Network; PyG integration would require rebranding or a separate adapter package |
| Browser-native real-time parsing (WASM) | Compile-time cost and WASM Python runtime limitations outweigh value for current user base |
| Full IDE UI (not extension) | Out of scope; VSCode extension (#8) covers the IDE use case |
| HDF5 export | Parquet covers the analytics use case more ergonomically; HDF5 adds a heavy dep for marginal benefit |
