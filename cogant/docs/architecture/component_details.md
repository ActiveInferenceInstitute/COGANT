## Component Details

### Python Orchestration (`cogant/`)

**Entry Points**: `cogant.api.pipeline.PipelineRunner` (orchestrated) and `cogant.api.session.Session` (step-by-step)

Responsibilities:
- Load and validate configuration
- Coordinate stage execution
- Manage data flow between stages
- Implement incremental processing
- Handle errors and recovery

**Key Modules**:
- `cogant.api`: Main public API (Session, PipelineRunner, Bundle, ReviewAPI, orchestration)
- `cogant.cli`: Command-line interface (Typer app)
- `cogant.config`: Configuration loading and validation (schema, defaults)
- `cogant.schemas`: IR type definitions (core, graph, semantic, bundle, state_space, process_model, provenance, validation, gnn_export)
- `cogant.ingest`: Repository ingest and file discovery (repo, files, manifest)
- `cogant.static`: Python AST parsing and symbol extraction (parser, symbols, imports, calls, types, dataflow)
- `cogant.normalize`: Canonical name normalization (canonical, identities)
- `cogant.graph`: Program graph construction and queries (builder, queries, merge)
- `cogant.translate`: Translation rules and confidence (engine, rules, confidence, review)
- `cogant.statespace`: State space compilation (compiler, variables, temporal)
- `cogant.process`: Process model extraction (extractor, timeline, policies)
- `cogant.dynamic`: Dynamic analysis (coverage, traces, enrichment)
- `cogant.validate`: IR validation and integrity checks (schema_check, provenance_check, integrity, report)
- `cogant.export`: Format handlers (typed_export, graphml, parquet, bundle)
- `cogant.gnn`: GNN formatting and export (formatter, json_export, [`GNNPackageBuilder`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/package.py)); the Python **`export`** stage ([`run_export`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/api/orchestration.py)) writes flat JSON under the run output dir and, when graph + state-space + process model + semantic mappings dict exist, materializes **`gnn_package/`** for validator and downstream tools (details: [GNN_EXPORT](../export/README.md))
- `cogant.viz`: Visualization (mermaid, plots, html_renderer, diff_view, graph_view, semantic_view, boundary, gantt)
- `cogant.scoring`: Drift analysis (drift)
- `cogant.simulate`: Simulation (runner)
- `cogant.plugins`: Plugin system (base: LanguagePlugin, ExportPlugin, ValidationPlugin, etc.)
- `cogant.provenance`: Provenance tracking (tracker)

### Rust Core (`rust/`)

**Workspace Crates**:

#### cogant-core
Core types used throughout:
- `StableId`: Persistent entity identifiers
- `NodeKind`: Entity type enumeration
- `EdgeKind`: Relationship type enumeration
- `SemanticRole`: Semantic classification
- `Confidence`: Certainty scoring
- `Provenance`: Origin tracking

#### cogant-graph
Program graph implementation:
- `ProgramGraph`: Directed graph with metadata
- `NodeData`: Node representation
- `EdgeData`: Edge representation
- Query methods (by name, by kind, by role)
- Graph traversal (callees, callers, transitive)

#### cogant-translate
Translation rules engine:
- `TranslationRule`: Rule trait
- `RuleSet`: Rule collection
- `TranslationEngine`: Orchestrates rule application
- `SemanticMapping`: Rule output
- `TranslationConfig`: Behavior configuration

#### cogant-statespace
State space and behavioral modeling:
- `StateVariable`: Observable variable
- `Action`: Possible action
- `Transition`: State-to-state change
- `StateSpaceModel`: Complete behavioral model
- `Observation`: Collected observations

#### cogant-store
Persistent storage abstraction:
- `BundleStore`: Trait for storage backends
- `FileStore`: File-based implementation
- `Bundle`: Artifact container
- `BundleArtifact`: Artifact metadata

#### cogant-trace
Execution trace types:
- `TraceEvent`: Single execution event
- `TraceSession`: Collection of events
- Event types: function entry/exit, state change, branch, exception, log

#### cogant-gnn
GNN export and formatting:
- `GnnBundle`: GNN data container
- `format_json()`: JSON export
- `format_markdown()`: Markdown export
- `node_kind_to_gnn_type()`: Kind → GNN type
- `edge_kind_to_gnn_type()`: Kind → GNN type

#### cogant-ffi
Python FFI via PyO3:
- `PyStableId`: Python wrapper
- `PyConfidence`: Python wrapper
- `PyNodeData`: Python wrapper
- `PyProgramGraph`: Python wrapper
- `cogant` module: PyO3 module definition
