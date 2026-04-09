## Version 0.1.0 (current)

### Core Components

- [x] Rust workspace structure
- [x] Core types (StableId, NodeKind, SemanticRole, Confidence, Provenance)
- [x] Program graph implementation (nodes, edges, queries)
- [x] Translation rules engine
- [x] State space types
- [x] Storage abstraction layer
- [x] Trace types
- [x] GNN export (JSON, Markdown)
- [x] PyO3 FFI bridge
- [x] Comprehensive documentation

### Python Components

- [x] Main API (Session / PipelineRunner / Bundle)
- [ ] Configuration system (YAML loader) — partial
- [x] File discovery (ingest / enumeration)
- [x] Python parser (AST pipeline)
- [x] Repo IR construction — partial by design
- [ ] Translation rule implementations — coverage varies
- [ ] State space analyzer — partial
- [ ] Validation system — partial
- [ ] PyTorch Geometric exporter
- [x] CLI interface (`cogant` Typer app)

### Documentation

- [x] RFC 0001: Naming & Scope
- [x] RFC 0002: IR Schemas
- [x] Architecture documentation
- [x] Specs: Pipeline, Mappings, Ontology, Reference
- [x] Top-level docs: SPEC, ARCHITECTURE, RULES, EXPORT, VALIDATION, PLUGIN_API
- Narrative docs track CLI subcommands, `validate` routing, and export/`gnn_package` behavior in [CLI_GUIDE](../cli/README.md), [API_GUIDE](../api/README.md), and [VALIDATION](../validation/README.md) (see [SPEC § Implementation status](../reference/README.md)).

