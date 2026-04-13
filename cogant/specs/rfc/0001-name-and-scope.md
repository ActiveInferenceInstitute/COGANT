# RFC 0001: COGANT - Naming, Scope, and Architecture

**Status**: Accepted  
**Date**: 2024-2026  
**Author**: COGANT Development Team

## Summary

This RFC establishes the foundational naming, scope, and architectural principles for **COGANT** (Codebase-to-GNN Translation), a system for translating arbitrary source code into representations compatible with the Active Inference Institute's **Generalized Notation Notation** (GNN) — a structured notation for Active Inference state-space and process models (not graph neural networks).

## Motivation

Existing systems for code analysis and machine learning fall into two camps:

1. **Language-specific tools** (AST parsers, type checkers) that are powerful but fragmented
2. **Generic ML frameworks** (PyTorch, TensorFlow) that work with any data but require significant manual translation

COGANT bridges this gap by providing a translation pipeline that:
- Accepts code in any language via pluggable parsers
- Translates to a unified internal representation (Program Graph IR)
- Exports to GNN-optimized formats (PyTorch Geometric, DGL, custom formats)
- Remains transparent about provenance and confidence

## Naming: COGANT

**COGANT** = **Co**debase-to-**G**NN **AN**alysi**s** **T**ranslation

The name encodes the system's core purpose: systematically translating codebases into graph neural network inputs. Alternatives considered:
- "code2gnn" (too narrow, ignores intermediate IRs)
- "GraphCodebase" (doesn't emphasize GNN focus)
- "SemanticGraphPipeline" (overly verbose)

## Scope

### In Scope

1. **Language Support**
   - Initially: Python, Java, JavaScript/TypeScript, Rust, C/C++
   - Extensible via pluggable parsers
   - Per-language version tracking and deprecation policies

2. **Semantic Extraction**
   - Function/method definitions and calls
   - Variable definitions and uses
   - Type hierarchies and implementations
   - Control flow and data flow edges
   - Error handling paths
   - Module/namespace structure

3. **Representations**
   - **Repo IR**: Repository-level code structure
   - **Program Graph IR**: Semantic graph (nodes, edges, roles)
   - **Semantic Mapping IR**: Translation rules and role assignments
   - **State Space IR**: Behavioral models and transitions
   - **Process Model IR**: Higher-order control structures
   - **Validation IR**: Quality metrics and checks

4. **Export Formats**
   - JSON (for archival and debugging)
   - Markdown (for human review)
   - PyTorch Geometric data format (for GNN training)
   - DGL format (for DGL ecosystems)
   - Custom HDF5 format (for large-scale studies)

5. **Configuration System**
   - Per-project configuration (YAML-based)
   - Per-language settings
   - Custom rule registration
   - Confidence thresholds
   - Output filtering

### Out of Scope

1. **Execution or interpretation** of code (analysis-only)
2. **Type inference** beyond existing language type systems
3. **Optimization or transformation** of code
4. **Machine learning model training** (we provide data, not models)
5. **IDE integration** (except as plugins for analysis tools)
6. **Real-time processing** of live codebases (batch-oriented)
7. **Private/proprietary language support** without open specs

## Vocabulary: Translation-Centric

Rather than using traditional compiler terminology, COGANT emphasizes translation and mapping:

| Traditional Term | COGANT Term | Reason |
|---|---|---|
| Token | Atom | Indivisible source unit |
| AST | Syntax Tree | Maps directly to parser output |
| Symbol | Entity | Emphasizes that symbols have semantic properties |
| Binding | Mapping | Bidirectional association |
| Type Inference | Role Assignment | We assign semantic roles, not just infer types |
| Graph Node | Entity | Used in "program entities" |
| Annotation | Label | Used in graph labeling |
| Confidence Score | Confidence | Used explicitly in all outputs |
| Trace | Trace | Execution trace, unchanged |

## Target Artifacts

### Primary Artifacts

1. **Program Graph Bundle**
   - JSON/MessagePack serialization of ProgramGraph
   - Includes all node/edge metadata
   - Versioned and checksummed
   - Reproducible from source + config

2. **GNN-Ready Format**
   - PyTorch Geometric: node features, edge indices, edge features
   - DGL: node tensors, edge tensors, heterogeneous graphs
   - JSON-Lines: one entity per line for streaming

3. **Validation Report**
   - Confidence distribution over all assertions
   - Coverage metrics (% of code analyzed)
   - Error/warning log
   - Reproducibility checkpoint (input, config, version)

4. **Trace Archive**
   - Execution traces (if dynamic analysis enabled)
   - State space exploration logs
   - Performance profiling data

### Secondary Artifacts

- Analysis summaries (Markdown)
- Statistics dashboards (JSON)
- Rule activation logs (for debugging)
- Debugging bundles (intermediate IRs)

## Non-Goals

1. **100% semantic precision** — some ambiguity is inevitable in polyglot analysis
2. **Multi-language type unification** — types are language-specific
3. **Distributed analysis** — single-machine focused (but architecturally compatible)
4. **Plugin marketplace** — we don't operate a registry
5. **Automatic model generation** — ML model design remains manual
6. **Security scanning** — analysis only, no threat modeling

## Architecture Decision: Python + Rust

### Decision

- **User-facing components**: Python (scikit-learn-like API)
- **Performance-critical components**: Rust (graph operations, export)
- **Integration**: PyO3-based FFI bridge

### Rationale

1. **Python Benefits**
   - Data science ecosystem integration
   - Easy prototyping of translation rules
   - Lower barrier to contribution
   - Jupyter notebook compatibility

2. **Rust Benefits**
   - Memory safety for graph operations
   - Deterministic performance (critical for large graphs)
   - FFI stability (interface evolution doesn't break Python)
   - Parallelizable without GIL constraints

3. **FFI Strategy**
   - Core graph operations in Rust
   - Rule engine and orchestration in Python
   - Data exchange via JSON or Parquet
   - No holding Python objects in Rust

## Pipeline Overview

```
┌─────────────────────────────────────────────────────┐
│ Source Code (multi-language)                        │
└─────────────────┬─────────────────────────────────┘
                  │ [Per-language parsers]
                  ▼
┌─────────────────────────────────────────────────────┐
│ Syntax Trees & Type Information                     │
└─────────────────┬─────────────────────────────────┘
                  │ [Python extraction layer]
                  ▼
┌─────────────────────────────────────────────────────┐
│ Repo IR (entities, raw relationships)               │
└─────────────────┬─────────────────────────────────┘
                  │ [Rust graph construction]
                  ▼
┌─────────────────────────────────────────────────────┐
│ Program Graph IR (nodes, edges, roles)              │
└─────────────────┬─────────────────────────────────┘
                  │ [Translation rules engine]
                  ▼
┌─────────────────────────────────────────────────────┐
│ Translated Graph (semantic roles assigned)          │
└─────────────────┬─────────────────────────────────┘
                  │ [State space analysis]
                  ▼
┌─────────────────────────────────────────────────────┐
│ State Space Model (behavioral representation)       │
└─────────────────┬─────────────────────────────────┘
                  │ [GNN export formatters]
                  ▼
┌─────────────────────────────────────────────────────┐
│ GNN Bundles (JSON, PyG, DGL, etc.)                  │
└─────────────────────────────────────────────────────┘
```

## Deliverables

1. **Core Rust Libraries**
   - `cogant-core`: Types (StableId, NodeKind, SemanticRole)
   - `cogant-graph`: Program graph implementation
   - `cogant-translate`: Translation rules and engine
   - `cogant-statespace`: State space and behavioral models
   - `cogant-store`: Bundle persistence
   - `cogant-trace`: Execution trace types
   - `cogant-gnn`: GNN export formats

2. **Python Package**
   - `cogant.api`: Main user-facing API
   - `cogant.parsers`: Language-specific extraction
   - `cogant.rules`: Translation rule implementations
   - `cogant.export`: Export format handlers
   - `cogant.cli`: Command-line tools

3. **Documentation**
   - Architecture specifications (this RFC + follow-ups)
   - API reference
   - Translation rules reference
   - Examples and tutorials

4. **Tooling**
   - Rust workspace with all crates
   - Python package structure
   - Test suites for all components
   - Benchmark suite

## Related RFCs

- [RFC 0002](0002-ir-schemas.md): Internal Representation Schemas
- Architecture docs: specs/architecture/
- Translation rules: specs/mappings/

## References

- [Program Graph Representation](../architecture/pipeline.md)
- [Python AST Module](https://docs.python.org/3/library/ast.html)
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/)
- [Semantic Code Analysis](https://en.wikipedia.org/wiki/Semantic_analysis_(compilers))
