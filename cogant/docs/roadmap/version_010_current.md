## Version 0.1.0 shipped baseline

This file keeps its recorded name for link stability. It no longer describes
the current COGANT tree. Current shipped capability is tracked by the package
changelog, `evaluation/METRICS.yaml`, generated run manifests, strict figure
sidecars, and the manuscript validation gates.

### Recorded core components

- [x] Rust workspace structure
- [x] Core types: `StableId`, `NodeKind`, `SemanticRole`, `Confidence`, and
  provenance records
- [x] Program graph implementation for nodes, edges, and basic queries
- [x] Translation rule engine
- [x] State-space type definitions
- [x] Storage abstraction layer
- [x] Trace types
- [x] GNN export in JSON and Markdown forms
- [x] PyO3 FFI bridge
- [x] Initial documentation set

### Recorded Python surface

- [x] Main API: `Session`, `PipelineRunner`, and `Bundle`
- [x] File discovery and Python AST parsing
- [x] CLI interface through the `cogant` Typer app
- [~] Configuration, repository IR construction, translation-rule coverage,
  state-space analysis, and validation were partial early surfaces
- [ ] PyTorch Geometric export was not part of the Generalized Notation
  Notation path and remains out of scope unless built as a separate adapter

### Current-status handoff

Use the current roadmap, TODO/taskboard, and generated artifacts instead of this
page for release decisions. In particular, benchmark and publication claims must
come from the generated run manifests, `METRICS.yaml`, figure sidecars, and
strict manuscript audits rather than recorded version-plan prose.
