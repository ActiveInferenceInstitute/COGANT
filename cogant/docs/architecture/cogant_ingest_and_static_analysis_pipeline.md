## COGANT Ingest and Static Analysis Pipeline

This guide describes the ingest and static analysis pipeline stages that form the first layers of the COGANT codebase-to-GNN translation engine.

### Architecture Overview

The pipeline is organized into two main stages:

1. **Ingest Stage** (`cogant.ingest`): Repository reading, manifest parsing, and file enumeration
2. **Static Analysis Stage** (`cogant.static`): Python AST parsing, symbol extraction, and code relationship analysis

#### Data Flow

```
Repository
    ↓
[RepoIngester] → RepoSnapshot (metadata, files, dependencies)
    ↓
[FileEnumerator] → List[FileInfo] (language-detected source files)
    ↓
[ManifestParser] → List[Dependency] (extracted from setup.py, package.json, etc.)
    ↓
[PythonASTParser] → PythonModule (functions, classes, imports, assignments)
    ↓
[SymbolExtractor] → SymbolTable (qualified names, scopes, types)
    ↓
[ImportAnalyzer] → List[ImportEdge] (stdlib/3rd-party/local classification)
    ↓
[CallGraphBuilder] → List[CallEdge] (function call relationships)
    ↓
[TypeInferencer] → List[TypeInfo] (type annotations and inference)
    ↓
[DataFlowAnalyzer] → List[DataFlowEdge] (reads/writes/mutations)
```

### Ingest Stage

#### RepoIngester

**Location:** `cogant.ingest.repo.RepoIngester`

Main entry point for repository ingestion. Supports both local and remote repositories.

##### Features:
- Clone remote Git repositories
- Extract Git metadata (commit hash, author, message)
- Detect primary programming language
- Aggregate dependencies from manifest files
- Return complete `RepoSnapshot`

##### Usage:

```python
from cogant.ingest import RepoIngester
from pathlib import Path
