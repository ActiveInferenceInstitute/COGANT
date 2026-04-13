## Heuristic Rules

### Implicit Calls

**ID**: `heuristic_implicit_call_001`

Detect calls via reflection or dynamic dispatch.

**Pattern**:
- Function called by string name
- Dynamic reference
- Function pointer passed

**Base Confidence**: 0.4 (LOW)

**Confidence Adjustments**:
- String contains function name: +0.2
- Function appears in context: +0.1
- Type inference suggests callable: +0.15

### Inferred Dependencies

**ID**: `heuristic_inferred_dep_001`

External API used without explicit import.

**Pattern**:
- API method called
- Module referenced
- Type from external package

**Base Confidence**: 0.5 (MEDIUM)

**Confidence Adjustments**:
- API method called directly: +0.2
- Module referenced: +0.15
- Type from external package: +0.15

