## COGANT Pipeline Index

Quick reference guide to the ingest and static analysis pipeline implementation.

### Quick Links

- **[SPEC.md](../reference/README.md)** — Ingest/static milestone and high-level overview
- **[ARCHITECTURE.md](../architecture/README.md)** — Complete pipeline user guide and API reference
- **[examples/example_pipeline.py](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/examples/example_pipeline.py)** - Runnable API example
- **[tests/integration/test_pipeline_runner_e2e.py](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/tests/integration/test_pipeline_runner_e2e.py)** - Integration tests

### Module Overview

#### Ingest Pipeline (Read & Analyze Repositories)

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `ingest/repo.py` | Repository ingestion | `RepoIngester`, `RepoMetadata`, `RepoSnapshot` |
| `ingest/files.py` | File discovery | `FileEnumerator`, `FileInfo` |
| `ingest/manifest.py` | Dependency parsing | `ManifestParser`, `Dependency` |

#### Static Analysis Pipeline (Parse & Extract Code Structure)

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `static/parser.py` | Python AST parsing | `PythonASTParser`, `PythonModule`, `FunctionDef`, `ClassDef` |
| `static/symbols.py` | Symbol extraction | `SymbolExtractor`, `SymbolInfo`, `SymbolTable` |
| `static/imports.py` | Import analysis | `ImportAnalyzer`, `ImportEdge` |
| `static/calls.py` | Call graph building | `CallGraphBuilder`, `CallEdge`, `CallExtractorVisitor` |
| `static/types.py` | Type inference | `TypeInferencer`, `TypeInfo` |
| `static/dataflow.py` | Data flow analysis | `DataFlowAnalyzer`, `DataFlowEdge`, `DataFlowVisitor` |

### Common Usage Patterns

#### Pattern 1: Ingest a Local Repository

```python
from cogant.ingest import RepoIngester
from pathlib import Path

ingester = RepoIngester()
snapshot = ingester.ingest_local(Path("/path/to/repo"))
