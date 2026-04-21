# COGANT Pipeline Architecture

## Overview

The COGANT pipeline transforms source code into Generalized Notation Notation (GNN) state-space and process-model representations — the structured Active Inference notation maintained by the Active Inference Institute, not graph neural networks — through nine progressive stages, each with explicit data contracts and error handling.

## Pipeline Stages

### Stage 1: Input & Discovery

**Input**: Directory of source files
**Output**: File manifest with metadata
**Owned by**: Python `cogant.discovery`

**Operations**:
1. Discover all files matching language patterns
2. Categorize by language and type (source, test, config)
3. Compute file hashes for change detection
4. Load language-specific configurations
5. Validate permissions and accessibility

**Error Handling**:
- Missing files → Error, halt
- Inaccessible files → Warning, skip
- Unsupported language → Skip (if optional)
- Config errors → Error, halt

**Data Contract**:
```python
{
    "files": [
        {
            "path": str,
            "language": str,
            "type": Literal["source", "test", "config"],
            "hash": str,
            "size_bytes": int,
        }
    ],
    "config": Dict[str, Any],
}
```

### Stage 2: Parsing & AST Extraction

**Input**: File manifest + source files
**Output**: Syntax trees + type information
**Owned by**: Language-specific parsers (Python, Rust, JavaScript)

**Operations**:
1. Load appropriate parser for each language
2. Parse to syntax tree (using tree-sitter, Python AST, etc.)
3. Extract type information (annotations, type checker output)
4. Identify basic entities (functions, classes, variables)
5. Record source locations for all entities

**Error Handling**:
- Parse error → Record error node, continue
- Type resolution failure → Mark low confidence, continue
- Timeout → Skip file, warning

**Data Contract**:
```python
{
    "file": str,
    "language": str,
    "entities": [
        {
            "id": str,
            "name": str,
            "kind": NodeKind,
            "location": SourceLocation,
            "type_annotation": Optional[str],
        }
    ],
    "relationships": [
        {
            "from": str,
            "to": str,
            "kind": str,
            "location": SourceLocation,
        }
    ],
}
```

### Stage 3: Repo IR Construction

**Input**: Parsed syntax trees
**Output**: Repo IR (raw entities and relationships)
**Owned by**: Python `cogant.extraction`

**Operations**:
1. Aggregate all parsed entities across files
2. De-duplicate entities (same entity from different paths)
3. Merge type information with entities
4. Build initial relationship graph
5. Extract docstrings and comments
6. Serialize to Repo IR JSON

**Error Handling**:
- Duplicate detection → Use first occurrence, log
- Broken references → Skip edge, warning
- Type mismatches → Mark low confidence

**Data Contract**:
```python
RepoIR = {
    "version": "1.0.0",
    "repository": {...},
    "files": [FileIR],
    "extracted_at": ISO8601,
}
```

### Stage 4: Program Graph Construction

**Input**: Repo IR
**Output**: Program Graph IR (semantic graph)
**Owned by**: Rust `cogant-graph`

**Operations** (via Rust):
1. Create nodes for each entity
2. Add edges for relationships
3. Assign confidence scores
4. Track provenance (source file, line, inference method)
5. Validate graph integrity
6. Compute statistics

**Error Handling**:
- Invalid node kind → Default to Unknown
- Circular references → Accept, mark
- Missing edges → Warn, continue

**Data Contract**:
```json
{
  "version": "1.0.0",
  "nodes": [Node],
  "edges": [Edge],
  "statistics": {...}
}
```

### Stage 5: Translation & Role Assignment

**Input**: Program Graph IR
**Output**: Translated graph with semantic roles
**Owned by**: Rust `cogant-translate`

**Operations** (via Rust FFI):
1. Load translation rule set
2. Match rules against each node
3. Assign semantic role (FunctionDef, FunctionCall, etc.)
4. Apply rule-specific transformations
5. Update confidence scores
6. Generate Semantic Mapping IR

**Error Handling**:
- No matching rule → Use heuristic default, mark LOW confidence
- Conflicting rules → Use first match, log all
- Confidence threshold violation → Skip, log

**Data Contract**:
```python
{
    "nodes": [...],  # Updated with roles
    "mappings": [
        {
            "id": str,
            "source_kind": str,
            "target_role": str,
            "confidence": float,
        }
    ],
}
```

### Stage 6: State Space Analysis

**Input**: Translated graph + (optional) execution traces
**Output**: State Space Model (behavioral model)
**Owned by**: Python `cogant.statespace`

**Operations**:
1. Identify observable state variables
2. Extract actions (function calls, mutations)
3. Infer transitions (from control flow)
4. Integrate execution traces (if available)
5. Compute probabilities
6. Identify accepting states

**Error Handling**:
- Unfeasible transition → Mark impossible, skip
- Probabilistic inconsistency → Normalize, warn
- No trace data → Use heuristic estimates

**Data Contract**:
```python
StateSpaceModel = {
    "variables": [StateVariable],
    "actions": [Action],
    "transitions": [Transition],
    "observations": [Observation],
}
```

### Stage 7: Validation

**Input**: All IRs + State Space Model
**Output**: Validation IR (metrics, issues, health)
**Owned by**: Python `cogant.validation`

**Operations**:
1. Check coverage (% lines analyzed)
2. Analyze confidence distribution
3. Detect inconsistencies (duplicates, orphans, cycles)
4. Validate against schema versions
5. Compute reproducibility hash
6. Generate issue report

**Error Handling**:
- Low coverage warning → Include in report
- Schema violations → Fail with details
- Hash mismatch → Note in reproducibility section

**Data Contract**:
```python
ValidationIR = {
    "metrics": {...},
    "issues": [Issue],
    "reproducibility": {...},
}
```

### Stage 8: Export

**Input**: Program Graph + Validation IR
**Output**: GNN bundles (JSON, PyTorch Geometric, DGL, etc.)
**Owned by**: Rust `cogant-gnn`

**Operations** (via Rust):
1. Format nodes as feature vectors
2. Create edge index tensors
3. Serialize in target format
4. Add metadata and checksums
5. Generate export manifest

**Error Handling**:
- Format unsupported → Error, suggest alternatives
- Feature encoding error → Skip problematic nodes, warn
- Tensor overflow → Downsample, log

**Data Contract**:
```python
GnnBundle = {
    "nodes": [GnnNode],
    "edges": [GnnEdge],
    "node_features": Tensor,
    "edge_features": Tensor,
    "metadata": {...},
}
```

## Stage Contracts

Each stage has explicit input/output types and error handling:

### Input Contract

- Type: Must match expected schema
- Completeness: May have missing optional fields
- Integrity: checksums verified if available

### Output Contract

- Type: Always matches output schema
- Completeness: All required fields present
- Integrity: Checksummed for verification

### Configuration Contract

Each stage reads from `config.yaml`:

```yaml
discovery:
  include_patterns: ["**/*.py", "**/*.java"]
  exclude_patterns: ["**/test_*.py"]

parsing:
  language_versions:
    python: "3.9+"
    java: "11+"
  timeout_seconds: 30

translation:
  rule_set: "default"
  min_confidence: 0.6
  include_low_confidence: true

export:
  formats: ["json", "pytorch_geometric"]
  compression: "gzip"
```

## Error Handling Strategy

### Error Levels

1. **FATAL**: Halt pipeline, must be user-fixed
   - Missing config file
   - Parse error on critical file
   - Schema violation

2. **ERROR**: Skip component, continue pipeline
   - Individual file parse failure
   - Missing dependencies
   - Format conversion error

3. **WARNING**: Log and continue
   - Low confidence detection
   - Partial type information
   - Skipped entities due to config

4. **INFO**: Log only
   - Processing milestones
   - Statistics
   - Optional analysis results

### Recovery & Rollback

- Partial results saved at each stage
- Can resume from last successful stage
- Validation IR tracks which stages completed

## Performance Considerations

### Stage Parallelization

- **Stage 1**: Sequential (discovery fast)
- **Stage 2**: Parallel per file (parse independent)
- **Stage 3**: Parallel per file + reduce step
- **Stage 4**: Sequential (graph construction needs global state)
- **Stage 5**: Parallel over rule set + merge
- **Stage 6**: Sequential (state space analysis)
- **Stage 7**: Sequential (validation aggregation)
- **Stage 8**: Parallel per format

### Benchmarks (Target)

- 10K functions: <30s on 4-core machine
- 100K functions: <5min on 4-core machine
- 1M functions: <1hr on 4-core machine

## Configuration System

### Precedence (lowest to highest)

1. Defaults (built-in)
2. Global config (`~/.cogant/config.yaml`)
3. Project config (`$PROJECT_ROOT/cogant.yaml`)
4. Stage-specific config (`cogant.{stage}.yaml`)
5. CLI arguments (`--option value`)

### Configuration Example

```yaml
# cogant.yaml - Project-level configuration

version: 1

discovery:
  languages: [python, javascript, rust]
  include_tests: false

parsing:
  python_version: "3.11"

translation:
  rule_set: "default"
  custom_rules:
    - path: "my_rules.py"
      enabled: true

statespace:
  trace_file: "execution_trace.json"

validation:
  min_coverage: 0.95
  max_warnings: 10

export:
  formats: [json, pytorch_geometric, dgl]
  compression: gzip
  output_dir: "./gnn_bundles"
```

## Pipeline Execution Model

### Single-Run Mode

```
discovery → parsing → repo_ir → graph → translate → statespace → validate → export
```

Sequential execution, all stages required.

### Incremental Mode

```
[Load cached IRs] → [Skip unchanged stages] → validate → export
```

- Hash source files
- Check if Repo IR cache valid
- Skip to translate or export if appropriate
- Useful for rapid iteration

### Dry-Run Mode

```
Simulate all stages, output metrics/warnings without writing files
```

## Reproducibility

Each pipeline run captures:

```json
{
  "run_id": "uuid",
  "timestamp": "2024-10-01T12:00:00Z",
  "cogant_version": "0.1.0",
  "input_hash": "sha256:abc123...",
  "config_hash": "sha256:def456...",
  "stages_completed": ["discovery", "parsing", "repo_ir", "graph"],
  "total_duration_seconds": 45.2,
  "stage_durations": {
    "discovery": 1.2,
    "parsing": 30.5,
    ...
  }
}
```

This enables verification that the same code + config produces the same output.

## References

- [IR Schemas RFC](../rfc/0002-ir-schemas.md)
- [Translation Rules](../mappings/code-to-gnn.md)
