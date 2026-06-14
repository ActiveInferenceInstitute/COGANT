# RFC 0002: Internal Representation Schemas

**Status**: Accepted
**Date**: 2024-2026
**Author**: COGANT Development Team

## Summary

This RFC defines the complete schema for all internal representations (IRs) used in the COGANT pipeline, including versioning, migration, provenance tracking, and stability guarantees.

## IR Hierarchy

COGANT uses six progressive IRs, each adding semantic detail:

```
Source Code
    ↓ [Per-language parser]
Syntax Trees + Type Info
    ↓ [Extraction layer]
Repo IR (raw entities and relationships)
    ↓ [Graph construction]
Program Graph IR (semantic graph with confidence)
    ↓ [Translation rules]
Semantic Mapping IR (role assignments)
    ↓ [Behavioral analysis]
State Space IR (transitions and observations)
    ↓ [Higher-order analysis]
Process Model IR (control structures)
    ↓ [Validation]
Validation IR (quality metrics)
```

Each IR is independently versioned and can be persisted to JSON.

## Schema Definitions

### 1. Repo IR (Repository Structure)

**Purpose**: Raw code entities and their basic relationships, extracted from source.

```json
{
  "version": "1.0.0",
  "format": "repo-ir",
  "repository": {
    "name": "project-name",
    "root_path": "/path/to/repo",
    "language": "python",
    "language_version": "3.9+",
    "file_count": 42,
    "total_lines": 15000
  },
  "files": [
    {
      "path": "src/main.py",
      "language": "python",
      "lines_of_code": 240,
      "entities": [
        {
          "id": "file_main.py#func_process",
          "type": "function",
          "name": "process",
          "location": { "line": 10, "column": 1, "end_line": 45 },
          "modifiers": ["async"],
          "parameters": [
            { "name": "data", "type": "list" },
            { "name": "timeout", "type": "int", "default": "30" }
          ],
          "return_type": "dict",
          "docstring": "Process input data with timeout."
        }
      ],
      "relationships": [
        {
          "from": "file_main.py#func_process",
          "to": "file_main.py#func_validate",
          "kind": "calls",
          "line": 15
        }
      ]
    }
  ],
  "extracted_at": "2024-10-01T12:00:00Z",
  "extractor_version": "cogant-0.1.0"
}
```

**Key Fields**:
- `version`: Semantic version of schema
- `repository`: Project-level metadata
- `files`: Per-file entity and relationship declarations
- `entities`: Functions, classes, variables, types, modules
- `relationships`: Type/call/use/define/inherits relationships

**Persistence**: JSON, max 500MB per file
**Lifetime**: 1 extraction run
**Mutability**: Immutable after creation

### 2. Program Graph IR

**Purpose**: Unified semantic graph with node/edge metadata, confidence, and provenance.

```json
{
  "version": "1.0.0",
  "format": "program-graph-ir",
  "graph": {
    "id": "graph_pyproject",
    "description": "Main project graph",
    "created_at": "2024-10-01T12:30:00Z",
    "nodes": [
      {
        "id": "node_abc123#uuid",
        "short_id": "fn_process",
        "name": "process",
        "kind": "FUNCTION",
        "role": "FUNCTION_DEF",
        "type_name": "Callable[[list, int], dict]",
        "confidence": 0.98,
        "provenance": {
          "type": "SourceCode",
          "file": "src/main.py",
          "line": 10,
          "column": 1
        },
        "attributes": {
          "async": "true",
          "visibility": "public"
        },
        "documentation": "Process input data..."
      }
    ],
    "edges": [
      {
        "source": "node_abc123#uuid",
        "target": "node_def456#uuid",
        "kind": "CALLS",
        "confidence": 0.95,
        "label": "direct_call",
        "provenance": {
          "type": "SourceCode",
          "file": "src/main.py",
          "line": 15,
          "column": 5
        }
      }
    ]
  },
  "statistics": {
    "node_count": 320,
    "edge_count": 1250,
    "node_kinds": {
      "FUNCTION": 89,
      "VARIABLE": 145,
      "TYPE": 42,
      "MODULE": 8,
      "CONSTANT": 36
    },
    "edge_kinds": {
      "CALLS": 450,
      "USES": 380,
      "DEFINES": 210,
      "HAS_TYPE": 180,
      "DATA_FLOW": 40
    }
  }
}
```

**Key Fields**:
- `nodes`: Entity nodes with semantic role
- `edges`: Relationships with confidence and provenance
- `confidence`: 0.0-1.0, explicit for every assertion
- `provenance`: Source of truth (file, line, tool, inference method)

**Confidence Tiers**:
- 1.0 (CERTAIN): Explicit in source, syntactically verified
- 0.8-0.99 (HIGH): Heuristic with strong signals
- 0.6-0.8 (MEDIUM): Multiple weak signals
- 0.0-0.6 (LOW): Speculative, single heuristic

**Provenance Types**:
- `SourceCode`: Direct from source (file, line, column)
- `TypeSystem`: Inferred from type checker
- `ControlFlow`: From CFG analysis
- `DataFlow`: From DFG analysis
- `Heuristic`: Rule-based (rule_id required)
- `External`: From tool output (tool, version required)
- `Aggregated`: Combined from multiple sources

**Persistence**: JSON or MessagePack, indexed for fast lookup
**Lifetime**: Per translation run (recomputed from Repo IR)
**Mutability**: Immutable after creation

### 3. Semantic Mapping IR

**Purpose**: Translation rules and role assignments for a specific graph.

```json
{
  "version": "1.0.0",
  "format": "semantic-mapping-ir",
  "mappings": [
    {
      "id": "map_001_funcdef_to_gnn",
      "source": {
        "kind": "FUNCTION",
        "role": "FUNCTION_DEF"
      },
      "target": {
        "role": "FUNCTION_DEF"
      },
      "confidence": 1.0,
      "conditions": [
        "node.type_name is not None",
        "node.documentation is not None"
      ],
      "transformations": {
        "add_feature_embedding": "true",
        "add_code_summary": "true"
      }
    }
  ],
  "rule_set_id": "rule_set_default_py39",
  "language": "python",
  "language_version": "3.9+",
  "applied_to_graph": "graph_pyproject",
  "application_date": "2024-10-01T13:00:00Z",
  "statistics": {
    "total_nodes": 320,
    "mapped_nodes": 318,
    "mapping_coverage": 0.9938
  }
}
```

**Key Fields**:
- `mappings`: Translation rules (source → target role)
- `conditions`: Boolean expressions for applicability
- `transformations`: Semantic enrichments to apply
- `rule_set_id`: Version identifier for rules
- `applied_to_graph`: Graph ID this mapping applies to

**Persistence**: JSON, linked to Program Graph IR
**Lifetime**: Tied to graph (recomputed if rules change)
**Mutability**: Immutable after creation

### 4. State Space IR

**Purpose**: Behavioral model of program execution.

```json
{
  "version": "1.0.0",
  "format": "state-space-ir",
  "state_space": {
    "id": "ss_pyproject",
    "name": "Main Program State Space",
    "graph_id": "graph_pyproject",
    "variables": [
      {
        "id": "var_data",
        "name": "data",
        "type": "list",
        "domain": ["[]", "[item]", "[item, item]"],
        "observable": true
      }
    ],
    "actions": [
      {
        "id": "action_call_process",
        "name": "call_process",
        "parameters": {
          "data": "list",
          "timeout": "int"
        },
        "outcomes": ["success", "timeout", "error"]
      }
    ],
    "transitions": [
      {
        "from_state": { "var_data": "[]" },
        "action": "action_call_process",
        "to_state": { "var_data": "[item]" },
        "probability": 0.8,
        "provenance": {
          "type": "DynamicTrace",
          "trace_id": "trace_001"
        }
      }
    ],
    "initial_state": { "var_data": "[]" },
    "accepting_states": [
      { "var_data": "[final_result]" }
    ],
    "observations": [
      {
        "variable_id": "var_data",
        "value": "[1, 2, 3]",
        "modality": "StaticAnalysis",
        "timestamp": 1000,
        "confidence": 0.7
      }
    ]
  }
}
```

**Key Fields**:
- `variables`: Observable state variables
- `actions`: Possible program actions
- `transitions`: State-to-state transitions with probability
- `observations`: Collected observations and their modality
- `initial_state`: Starting state
- `accepting_states`: Terminal states

**Observation Modalities**:
- `StaticAnalysis`: From code inspection
- `DynamicTrace`: From execution trace
- `Instrumentation`: From logging/monitoring
- `TypeInference`: From type system
- `Heuristic`: From rule-based estimation
- `ExternalTool`: From linters, profilers, etc.

**Persistence**: JSON, may be large
**Lifetime**: Per analysis session
**Mutability**: Immutable after completion

### 5. Process Model IR

**Purpose**: High-level control structures and patterns.

```json
{
  "version": "1.0.0",
  "format": "process-model-ir",
  "processes": [
    {
      "id": "proc_data_pipeline",
      "name": "Data Processing Pipeline",
      "description": "Main ETL flow",
      "steps": [
        {
          "id": "step_1",
          "label": "Extract",
          "type": "sequential",
          "entities": ["fn_extract"],
          "next": "step_2"
        },
        {
          "id": "step_2",
          "label": "Transform",
          "type": "parallel",
          "entities": ["fn_transform_a", "fn_transform_b"],
          "next": "step_3"
        },
        {
          "id": "step_3",
          "label": "Load",
          "type": "sequential",
          "entities": ["fn_load"],
          "next": null
        }
      ],
      "error_handling": [
        {
          "step": "step_1",
          "handler": "fn_error_handler",
          "handler_type": "catch"
        }
      ]
    }
  ],
  "patterns": [
    {
      "id": "pattern_retry",
      "name": "Retry Pattern",
      "description": "Exponential backoff retry logic",
      "instances": [
        {
          "entity": "fn_api_call",
          "max_retries": 3,
          "backoff_multiplier": 2.0
        }
      ]
    }
  ]
}
```

**Key Fields**:
- `processes`: Identified workflows/pipelines
- `patterns`: Detected code patterns (retry, circuit-breaker, etc.)
- `steps`: Sequence of process steps
- `error_handling`: Exception handling flows

**Persistence**: JSON
**Lifetime**: Per analysis session
**Mutability**: Immutable after creation

### 6. Validation IR

**Purpose**: Quality metrics, coverage, and health checks.

```json
{
  "version": "1.0.0",
  "format": "validation-ir",
  "validation_run": {
    "id": "val_001",
    "timestamp": "2024-10-01T14:00:00Z",
    "analyzed_graph": "graph_pyproject"
  },
  "metrics": {
    "coverage": {
      "lines_analyzed": 14950,
      "lines_total": 15000,
      "coverage_percent": 99.67,
      "uncovered_files": ["tests/mock_data.py"]
    },
    "confidence": {
      "mean_confidence": 0.92,
      "median_confidence": 0.95,
      "min_confidence": 0.3,
      "distribution": {
        "CERTAIN": 280,
        "HIGH": 35,
        "MEDIUM": 4,
        "LOW": 1
      }
    },
    "consistency": {
      "duplicate_nodes": 0,
      "orphaned_nodes": 0,
      "disconnected_components": 1
    }
  },
  "issues": [
    {
      "level": "WARNING",
      "code": "W001",
      "message": "Node fn_helper has no callers",
      "node_id": "node_xyz"
    },
    {
      "level": "INFO",
      "code": "I001",
      "message": "Type information missing for 3 parameters",
      "count": 3
    }
  ],
  "reproducibility": {
    "cogant_version": "0.1.0",
    "input_files_hash": "sha256:abc123...",
    "config_hash": "sha256:def456...",
    "output_timestamp": "2024-10-01T14:00:00Z"
  }
}
```

**Key Fields**:
- `metrics`: Coverage, confidence distribution, consistency
- `issues`: Warnings, errors, info messages
- `reproducibility`: Version and input checksums

**Persistence**: JSON, lightweight
**Lifetime**: Audit trail (kept indefinitely)
**Mutability**: Immutable after creation

## Stable IDs

All entities across all IRs use **StableId**, which combines:

1. **Short ID**: Human-readable hash (e.g., `fn_8f2a1b`)
2. **UUID**: Collision-resistant identifier (e.g., `550e8400-e29b-41d4-a716-446655440000`)

**Purpose**: Enables stable references across transformations without collision risk.

**Format**: `{short_id}#{uuid}`

**Generation**:
- Short ID: Hash(filepath + entity_type + entity_name)
- UUID: UUIDv4 (random, unique)

**Invariant**: If source code and entity name unchanged, short_id remains the same. If collision detected, both long names printed with warning.

## Versioning Strategy

### Semantic Versioning

All IRs use semver: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking schema changes (require migration)
- **MINOR**: New optional fields or enum variants (backward compatible)
- **PATCH**: Bug fixes, clarifications (transparent)

### Forward Compatibility

- Unknown enum values are preserved as-is
- Unknown object fields are preserved
- Default values for missing fields (if defined)

### Migration Rules

For major version changes, provide:

```json
{
  "migration": {
    "from_version": "1.0.0",
    "to_version": "2.0.0",
    "script": "migrate_v1_to_v2.py",
    "rules": [
      { "old_field": "type", "new_field": "kind", "transform": "uppercase" },
      { "removed_field": "removed_role", "reason": "Consolidated into role" }
    ]
  }
}
```

## Provenance Minimums

To ensure reproducibility, minimum provenance:

| IR | Required Provenance Fields |
|----|----|----|
| Repo | file, line, language_version |
| Program Graph | type (SourceCode/Heuristic/etc.) |
| Semantic Mapping | source_kind, source_role |
| State Space | variable_id, modality |
| Process Model | entity_ids, step_type |
| Validation | version, timestamp |

## Serialization Guarantees

- JSON: Human-readable, archival
- MessagePack (Rust): Fast binary, typed
- Parquet (Python): Columnar, analytics-friendly
- All formats must round-trip losslessly

## References

- [Stable Identifiers](../schemas/ir-reference.md)
- [Program Graph Design](../architecture/pipeline.md)
