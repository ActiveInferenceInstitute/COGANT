## Architecture Overview

```
Source Code
    ↓ [Per-language parsers]
Syntax Trees + Type Info
    ↓ [Extraction layer]
Repo IR
    ↓ [Graph construction - Rust]
Program Graph IR
    ↓ [Translation rules]
Semantic Mapping IR
    ↓ [Behavioral analysis]
State Space IR
    ↓ [Higher-level patterns]
Process Model IR
    ↓ [Validation]
Validation IR
    ↓ [Export formatters - Rust]
GNN Bundles (JSON, PyG, DGL, etc.)
```

### Components

**Python Components**:
- `cogant.api`: Main public API (Session, PipelineRunner, Bundle, ReviewAPI, orchestration)
- `cogant.ingest`: Repository ingest, file discovery, and language detection
- `cogant.static`: Python AST parsing, symbol extraction, imports, calls, types, dataflow
- `cogant.normalize`: Canonical name normalization and identity resolution
- `cogant.graph`: Program graph construction, queries, and merge
- `cogant.translate`: Translation rules engine, confidence model, review
- `cogant.statespace`: State space compilation (compiler, variables, temporal)
- `cogant.process`: Process model extraction (extractor, timeline, policies)
- `cogant.dynamic`: Dynamic analysis (coverage, traces, enrichment)
- `cogant.validate`: IR validation, integrity checks, provenance checks, reports
- `cogant.export`: Export format handlers (typed_export, graphml, parquet, bundle)
- `cogant.gnn`: GNN formatting and JSON export
- `cogant.viz`: Visualization (mermaid, plots, html_renderer, diff_view, graph_view, semantic_view, boundary, gantt)
- `cogant.scoring`: Drift analysis
- `cogant.simulate`: Simulation runner
- `cogant.plugins`: Plugin system (language, trace, normalizer, rule, export, validation, visualization)
- `cogant.provenance`: Provenance tracking
- `cogant.config`: Configuration loading (schema, defaults)
- `cogant.schemas`: IR type definitions (core, graph, semantic, bundle, state_space, process_model, provenance, validation, gnn_export)
- `cogant.cli`: Command-line interface (Typer app)

**Rust Components**:
- `cogant-core`: Core types (StableId, NodeKind, SemanticRole)
- `cogant-graph`: Program graph implementation
- `cogant-translate`: Translation engine
- `cogant-statespace`: State space modeling
- `cogant-gnn`: GNN export formatting
- `cogant-ffi`: Python FFI via PyO3

