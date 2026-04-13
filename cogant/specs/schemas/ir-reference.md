# Internal Representation (IR) Schema Reference

Complete field documentation for all COGANT internal representations.

## Common Types

### StableId

Persistent identifier for program entities.

```json
{
  "short_id": "fn_8f2a1b",
  "uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Fields**:
- `short_id` (string): Human-readable hash (deterministic from source + entity name)
- `uuid` (string, UUIDv4): Collision-resistant globally unique identifier

### Provenance

Origin and derivation method of an assertion.

```json
{
  "type": "SourceCode",
  "file": "src/main.py",
  "line": 42,
  "column": 10
}
```

**Variants**:
- `SourceCode`: Explicit in source code
  - `file`: Relative path to source file
  - `line`: 1-based line number
  - `column`: 1-based column number

- `TypeSystem`: From type checker/inference
  - `reason`: Description of how inferred
  - `tool`: Type checker name (mypy, pylint, etc.)

- `ControlFlow`: From CFG analysis
  - `reason`: Analysis description
  - `algorithm`: Which algorithm (dominance, etc.)

- `DataFlow`: From DFG analysis
  - `reason`: Analysis description

- `Heuristic`: Rule-based detection
  - `rule_id`: Which heuristic rule (rule_001, etc.)

- `External`: From external tool output
  - `tool`: Tool name
  - `version`: Tool version

- `Aggregated`: Combined from multiple sources
  - `sources`: Array of other Provenance objects

- `Unknown`: Not tracked

### SourceLocation

Location in source code.

```json
{
  "file": "src/main.py",
  "line": 10,
  "column": 1,
  "end_line": 45,
  "end_column": 5
}
```

**Fields**:
- `file` (string): Relative path to file
- `line` (integer): 1-based starting line
- `column` (integer): 1-based starting column
- `end_line` (integer, optional): 1-based ending line
- `end_column` (integer, optional): 1-based ending column

### Confidence

Certainty level of an assertion (0.0 to 1.0).

```json
{
  "value": 0.85,
  "level": "HIGH"
}
```

**Levels**:
- `1.0` / `CERTAIN`: Explicit source code evidence
- `0.8-0.99` / `HIGH`: Heuristic with strong signals
- `0.6-0.8` / `MEDIUM`: Multiple weak signals or one medium-confidence heuristic
- `0.0-0.6` / `LOW`: Speculative or single weak signal

## Node Types

### NodeKind Enumeration

```
FUNCTION | VARIABLE | TYPE | MODULE | CONTROLFLOW_NODE | 
DATA_STRUCTURE | ERRORHANDLER | CONSTANT | EXTERNAL | 
TEST | DOCUMENTATION | CONFIGURATION | UNKNOWN
```

### SemanticRole Enumeration

```
FUNCTION_DEF | FUNCTION_CALL | VARIABLE_DEF | VARIABLE_USE |
CONTROL_FLOW | TYPE_DEF | TYPE_REF | DATA_ACCESS |
ERROR_HANDLING | MODULE_DEF | MODULE_IMPORT |
METHOD_DEF | METHOD_CALL | INTERFACE | IMPLEMENTATION |
INHERITANCE | POLYMORPHISM | DEPENDENCY_INJECT |
CONFIG_PARAM | LOGGING_STMT | PERF_CRITICAL |
SECURITY_CRITICAL | TEST_CODE | DOCUMENTATION |
CONSTANT | ANNOTATION | GENERIC_PARAM | TYPE_CONSTRAINT |
UNKNOWN
```

## Edge Types

### EdgeKind Enumeration

```
CALLS | USES | DEFINES | HAS_TYPE | DATA_FLOW |
CONTROL_DEPENDENCY | MEMBER_OF | INHERITS | IMPLEMENTS |
INSTANTIATES | PARAMETERIZES | OVERRIDES | DEPENDS_ON |
EXTERNAL_REF | CONFIG_REF | ERROR_FLOW | RETURNS |
PARAMETER | UNKNOWN
```

## Program Graph IR Fields

### Node Object

```json
{
  "id": "StableId",
  "short_id": "fn_process",
  "name": "process",
  "kind": "FUNCTION",
  "role": "FUNCTION_DEF",
  "type_name": "Callable[[list, int], dict]",
  "confidence": 0.98,
  "provenance": "Provenance",
  "attributes": {
    "async": "true",
    "visibility": "public",
    "is_recursive": "false"
  },
  "documentation": "Process input data with timeout.",
  "file": "src/main.py",
  "line": 10,
  "column": 1
}
```

**Fields**:
- `id` (StableId): Unique identifier
- `short_id` (string): Human-readable part of ID
- `name` (string): Entity name (function name, variable name, etc.)
- `kind` (NodeKind): Type of entity
- `role` (SemanticRole): Semantic classification
- `type_name` (string, optional): Type annotation as string
- `confidence` (number 0-1): Certainty of classification
- `provenance` (Provenance): Source of truth
- `attributes` (object): Language/context-specific attributes
- `documentation` (string, optional): Docstring or comment
- `file` (string, optional): Source file path
- `line` (integer, optional): Starting line number
- `column` (integer, optional): Starting column number

### Edge Object

```json
{
  "source": "550e8400-e29b-41d4-a716-446655440000",
  "target": "550e8401-e29b-41d4-a716-446655440001",
  "kind": "CALLS",
  "confidence": 0.95,
  "label": "direct_call",
  "provenance": "Provenance",
  "attributes": {
    "is_recursive": "false",
    "call_count_estimate": "1"
  },
  "type_flow": "str"
}
```

**Fields**:
- `source` (UUID): Source node UUID
- `target` (UUID): Target node UUID
- `kind` (EdgeKind): Type of relationship
- `confidence` (number 0-1): Certainty of relationship
- `label` (string, optional): Edge label (e.g., "success", "error", "branch_taken")
- `provenance` (Provenance): Source of truth
- `attributes` (object): Additional properties
- `type_flow` (string, optional): Data type flowing through edge

## Semantic Mapping IR Fields

### Mapping Object

```json
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
    "extract_signature": true,
    "compute_complexity": true
  }
}
```

**Fields**:
- `id` (string): Unique rule identifier
- `source` (object): Source pattern
  - `kind` (NodeKind): Node kind to match
  - `role` (SemanticRole): Semantic role to match
- `target` (object): Target classification
  - `role` (SemanticRole): Assigned role
- `confidence` (number 0-1): Base confidence of this rule
- `conditions` (array of strings): Applicability predicates
- `transformations` (object): Feature enrichments to apply

## State Space IR Fields

### StateVariable Object

```json
{
  "id": "StableId",
  "name": "data",
  "type": "list",
  "domain": ["[]", "[item]", "[item, item]"],
  "observable": true,
  "scope": "local",
  "lifecycle": {
    "defined_at": { "file": "main.py", "line": 10 },
    "last_used_at": { "file": "main.py", "line": 35 }
  }
}
```

**Fields**:
- `id` (StableId): Variable identifier
- `name` (string): Variable name
- `type` (string): Data type
- `domain` (array of strings, optional): Possible values
- `observable` (boolean): Whether observable in execution
- `scope` (string, optional): local, global, parameter, field
- `lifecycle` (object, optional): Definition and usage locations

### Action Object

```json
{
  "id": "StableId",
  "name": "call_process",
  "parameters": {
    "data": "list",
    "timeout": "int"
  },
  "outcomes": ["success", "timeout", "error"],
  "affected_variables": ["data", "result"]
}
```

**Fields**:
- `id` (StableId): Action identifier
- `name` (string): Action name
- `parameters` (object): Parameter types
- `outcomes` (array of strings): Possible outcomes
- `affected_variables` (array of strings, optional): Which variables modified

### Transition Object

```json
{
  "from_state": { "data": "[]" },
  "action": "StableId",
  "to_state": { "data": "[item]" },
  "probability": 0.8,
  "provenance": "Provenance",
  "infeasible": false,
  "reason": "call_process succeeds with data"
}
```

**Fields**:
- `from_state` (object): State variable → value map
- `action` (StableId): Action taken
- `to_state` (object): Resulting state
- `probability` (number 0-1): Transition probability
- `provenance` (Provenance): How determined
- `infeasible` (boolean): Whether this transition is impossible
- `reason` (string): Explanation of transition

### Observation Object

```json
{
  "variable_id": "StableId",
  "value": "[1, 2, 3]",
  "modality": "StaticAnalysis",
  "timestamp": 1000,
  "confidence": 0.7,
  "source_file": "main.py",
  "source_line": 15
}
```

**Fields**:
- `variable_id` (StableId): Variable being observed
- `value` (string): Observed value
- `modality` (string): How captured (StaticAnalysis, DynamicTrace, Instrumentation, etc.)
- `timestamp` (integer): When observed (microseconds)
- `confidence` (number 0-1): Confidence in observation
- `source_file` (string, optional): Where observation came from
- `source_line` (integer, optional): Source line number

## Validation IR Fields

### Metric Object

```json
{
  "name": "coverage",
  "value": 99.67,
  "unit": "percent",
  "threshold": 95.0,
  "status": "PASS"
}
```

**Fields**:
- `name` (string): Metric name
- `value` (number): Measured value
- `unit` (string): Unit of measurement
- `threshold` (number, optional): Target threshold
- `status` (string): PASS, WARN, FAIL

### Issue Object

```json
{
  "level": "WARNING",
  "code": "W001",
  "message": "Node fn_helper has no callers",
  "node_id": "StableId",
  "file": "src/helpers.py",
  "line": 50,
  "suggested_action": "Consider removing or documenting as utility"
}
```

**Fields**:
- `level` (string): INFO, WARNING, ERROR
- `code` (string): Issue code (W001, E002, etc.)
- `message` (string): Description
- `node_id` (StableId, optional): Related node
- `file` (string, optional): Source file
- `line` (integer, optional): Line number
- `suggested_action` (string, optional): Remediation

## Serialization Rules

### JSON Serialization

- All timestamps: ISO 8601 format
- All numbers: No scientific notation
- All UUIDs: Standard hyphenated format
- All paths: Forward slashes (/)
- All enums: SCREAMING_SNAKE_CASE

### Field Presence

- **Required**: Must be present in every instance
- **Optional**: May be omitted (null in JSON)
- **Computed**: Derived from other fields, can be omitted if not used

## Validation Rules

### Schema Validation

Every IR must pass JSON schema validation (schema files available separately).

### Semantic Validation

1. All referenced node/edge IDs must exist
2. No cycles in MEMBER_OF relationships
3. All edges have non-null source and target
4. Confidence values in range [0.0, 1.0]
5. Timestamps in valid ISO 8601 format

## Backward Compatibility

- New optional fields are always added with defaults
- Removed fields are deprecated for 2 major versions
- Renamed fields have migration rules defined
- New enum values are backward compatible

## Type Definitions

### StringifiedType

Types represented as strings (language-specific):

```
"int", "str", "list", "dict"                      # Python
"int", "String", "List<T>", "Map<K, V>"          # Java
"number", "string", "Array<T>", "Object"         # JavaScript
"i32", "String", "Vec<T>", "HashMap<K, V>"       # Rust
```

Language prefix optional when unambiguous:

```
"py:Dict[str, list]"    # Explicitly Python
"java:List<String>"     # Explicitly Java
"dict"                  # Context-determined
```

## References

- [IR Schema RFC](../rfc/0002-ir-schemas.md)
- [Pipeline Architecture](../architecture/pipeline.md)
- [Translation Rules](../mappings/code-to-gnn.md)
