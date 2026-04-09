## Pipeline Stages

### Stage 1: Ingest

**Input**: Directory path  
**Output**: File manifest with metadata

Load target codebase, enumerate files, detect languages, load configuration.

### Stage 2: Static

**Input**: File manifest + source files  
**Output**: AST + types + symbols + imports + call graph + data flow per file

Extract AST, types, symbols, imports, call graph, and data flow per file using language-specific parsers (tree-sitter, Python AST, etc.).

### Stage 3: Normalize

**Input**: Per-file static analysis results  
**Output**: Canonical entities

Normalize cross-language representations to canonical form. Resolve identities, de-duplicate entities, merge type information.

### Stage 4: Graph

**Input**: Canonical entities  
**Output**: Program Graph IR

Build program dependency graph with nodes, edges, confidence, and provenance.

### Stage 5: Dynamic

**Input**: Program Graph IR + runtime traces (optional, skip_on_error)  
**Output**: Enriched Program Graph IR

Enrich graph with runtime coverage and trace data. This stage is optional and will be skipped on error if no trace data is available.

### Stage 6: Translate

**Input**: Program Graph IR (possibly enriched)  
**Output**: Translated graph + semantic roles

Apply translation rules via fixpoint iteration, resolve conflicts, assign semantic roles, compute confidence.

### Stage 7: Statespace

**Input**: Translated graph  
**Output**: State Space Model

Compile state-space model: identify variables, extract actions, infer transitions, collect observations.

### Stage 8: Process

**Input**: State Space Model + translated graph  
**Output**: Process Model

Extract process model: identify stages, connections, patterns, and build timeline.

### Stage 9: Export

**Input**: All IRs + models  
**Output**: Artifact bundles (JSON, GraphML, Parquet, HTML, Mermaid)

Export all artifacts in multiple formats and generate manifest.

### Stage 10: Validate

**Input**: All IRs + exported artifacts  
**Output**: Validation IR (metrics, issues)

Run integrity, schema, and provenance checks. Analyze confidence distribution and generate report.

