# cogant (Python Core)

The Python implementation of COGANT: parsers, graph construction, translation, validation, and export.

## Contents
- **api/** — Stable Python entry points (Session, PipelineRunner, Bundle)
- **cli/** — Command-line interface
- **ingest/** — File discovery, manifest, and repository scanning
- **parsers/** — Language-specific AST extractors (Python, Rust, and stubs for others)
- **schemas/** — Core type definitions (Graph, Bundle, Provenance, GNN export)
- **graph/** — In-memory program graph with builder, queries, and merge logic
- **normalize/** — Cross-language symbol identity and reference resolution
- **process/** — Timeline extraction and process-model policies
- **static/** — Shared static analysis helpers (symbols, types, calls, dataflow)
- **dynamic/** — Hooks for execution-informed facts (coverage, traces)
- **translate/** — Rule-driven graph transforms and confidence scoring
- **scoring/** — Calibrated edge/node confidence and drift detection
- **validate/** — Schema checks, integrity audits, and provenance verification
- **statespace/** — Control-flow and state-machine compilation
- **export/** — Writers for Markdown, JSON, GraphML, Parquet
- **config/** — Configuration schema and defaults
- **viz/** — HTML rendering for graphs, reports, and diffs
- **plugins/** — Extension points and plugin base classes
- **provenance/** — Source attribution and run metadata tracking

## Usage

All modules are importable from the root cogant package:

```python
from cogant import PipelineRunner, Session
from cogant.schemas import Bundle, ProgramGraph
from cogant.graph import GraphBuilder
from cogant.export import export_json
```

Subsystem-specific imports:

```python
from cogant.ingest import Repository
from cogant.translate import RuleEngine
from cogant.validate import ValidationReport
```

## Dependencies
- networkx — graph representation and algorithms
- pydantic — schema validation
- PyYAML — configuration files
- pyarrow — columnar export
- jinja2 — HTML rendering
- All modules depend on schemas/ and static/
