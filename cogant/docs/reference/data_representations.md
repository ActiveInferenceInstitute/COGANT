## Data Representations

### Nodes

Each node represents a program entity:

```json
{
  "id": "fn_8f2a1b#550e8400-e29b-41d4-a716-446655440000",
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
  "documentation": "Process input data with timeout.",
  "attributes": { "async": true, "visibility": "public" }
}
```

**Key fields**:
- `id`: Stable identifier.
- `kind`: a `NodeKind` value such as `MODULE`, `CLASS`, `FUNCTION`, `METHOD`, `VARIABLE`,
  `PARAMETER`, `CONFIGURATION`, `FEATURE_FLAG`, `TEST`, `ASSERTION`, `POLICY`, or `ACTION`.
- `role`: optional semantic mapping label when a graph node has been translated into a
  `MappingKind` such as `HIDDEN_STATE`, `OBSERVATION`, `ACTION`, `POLICY`, `CONSTRAINT`,
  `CONTEXT`, `DATA_FLOW`, `ERROR_HANDLING`, `ORCHESTRATION`, or `CIRCUIT_BREAKER`.
- `confidence`: 0.0-1.0 (certainty of classification).
- `provenance`: Origin of the assertion.

### Edges

Relationships between nodes:

```json
{
  "source": "550e8400-...",
  "target": "550e8401-...",
  "kind": "CALLS",
  "confidence": 0.95,
  "label": "direct_call",
  "provenance": {
    "type": "SourceCode",
    "file": "src/main.py",
    "line": 15
  }
}
```

**Key fields**:
- `kind`: an `EdgeKind` value such as `CONTAINS`, `IMPORTS`, `INHERITS`, `DEPENDS_ON`,
  `READS`, `WRITES`, `RETURNS`, `CALLS`, `THROWS`, `CATCHES`, `YIELDS`, `OBSERVES`,
  `EMITS`, `TRIGGERS`, `GUARDS`, `HANDLES`, or `MUTATES`.
- `confidence`: Certainty of relationship.
- `label`: Optional semantic label (success, error, etc.).

### Node Kinds

```
REPO | MODULE | FILE | CLASS | FUNCTION | METHOD | VARIABLE |
ENDPOINT | EVENT | PARAMETER | RETURN_VALUE | DATA_STRUCTURE |
CONFIGURATION | FEATURE_FLAG | TEST | ASSERTION | POLICY | ACTION
```

### Semantic Roles

Current `MappingKind` values:

```
OBSERVATION | ACTION | HIDDEN_STATE | CONTEXT | POLICY |
CONSTRAINT | PREFERENCE | DATA_FLOW | CONTROL_FLOW |
ERROR_HANDLING | ORCHESTRATION | RETRY_PATTERN |
CIRCUIT_BREAKER | FEATURE_FLAG
```
