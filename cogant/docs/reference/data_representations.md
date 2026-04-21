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
- `id`: Stable identifier (short_id + UUID)
- `kind`: FUNCTION, VARIABLE, TYPE, MODULE, etc.
- `role`: FUNCTION_DEF, FUNCTION_CALL, etc. (semantic)
- `confidence`: 0.0-1.0 (certainty of classification)
- `provenance`: Origin of the assertion

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
- `kind`: CALLS, USES, DEFINES, HAS_TYPE, DATA_FLOW, etc.
- `confidence`: Certainty of relationship
- `label`: Semantic label (success, error, etc.)

### Node Kinds

```
FUNCTION | VARIABLE | TYPE | MODULE | CONTROLFLOW_NODE |
DATA_STRUCTURE | ERRORHANDLER | CONSTANT | EXTERNAL |
TEST | DOCUMENTATION | CONFIGURATION | UNKNOWN
```

### Semantic Roles

Core roles for GNN training:

```
FUNCTION_DEF | FUNCTION_CALL | VARIABLE_DEF | VARIABLE_USE |
TYPE_DEF | METHOD_DEF | METHOD_CALL | CONTROL_FLOW |
ERROR_HANDLING | MODULE_DEF | MODULE_IMPORT | INHERITANCE |
IMPLEMENTATION | POLYMORPHISM | DATA_ACCESS | TYPE_REF |
CONSTANT | ANNOTATION | DOCUMENTATION | TEST_CODE |
CONFIG_PARAM | LOGGING_STMT | PERF_CRITICAL |
SECURITY_CRITICAL | INTERFACE | GENERIC_PARAM |
DEPENDENCY_INJECT | UNKNOWN
```
