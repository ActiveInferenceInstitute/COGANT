# Code-to-GNN Translation Rules

## Overview

This document specifies the translation rules that map program graph entities to GNN-compatible semantic roles. Rules are language-agnostic where possible, with language-specific variants documented separately.

## Translation Rule Structure

```python
TranslationRule = {
    "id": str,                    # Unique identifier (e.g., "rule_001")
    "description": str,            # Human-readable description
    "source": {
        "kind": NodeKind,         # e.g., FUNCTION, VARIABLE
        "role": SemanticRole,     # e.g., FUNCTION_DEF
    },
    "target_role": SemanticRole,  # Target semantic role for GNN
    "confidence": float,           # Base confidence (0.0-1.0)
    "conditions": [Condition],    # Applicability conditions
    "transformations": [Transform], # Feature enrichments
}

Condition = {
    "field": str,                 # Node field to check
    "operator": str,              # "equals", "contains", "exists", "regex"
    "value": Any,                 # Value to compare
}

Transform = {
    "name": str,                  # "add_feature", "compute_metric"
    "parameters": Dict,           # Transformation-specific parameters
}
```

## Core Translation Rules

### Rule 1: Function Definition → Function Node

**ID**: `rule_fn_def_001`  
**Match**: NodeKind=FUNCTION, SemanticRole=FUNCTION_DEF  
**Target**: SemanticRole.FUNCTION_DEF  
**Base Confidence**: 1.0 (CERTAIN)  
**Conditions**:
- Node.type_name is not None
- Node.provenance.type == "SourceCode"

**Transformations**:
- `extract_signature`: Parse function signature for parameters/returns
- `compute_complexity`: Estimate cyclomatic complexity from control flow
- `identify_side_effects`: Annotate if function has side effects

**Example**:
```python
def process_data(data: list, timeout: int) -> dict:
    """Process input data."""
    ...
```
→ Node with role=FUNCTION_DEF, confidence=1.0

### Rule 2: Function Call → Call Edge

**ID**: `rule_fn_call_001`  
**Match**: EdgeKind=CALLS with confidence >= 0.8  
**Target**: EdgeKind.Calls  
**Base Confidence**: 0.85 (HIGH)  
**Conditions**:
- source.kind == FUNCTION or METHOD
- target.kind == FUNCTION or METHOD
- edge.confidence >= 0.8

**Transformations**:
- `infer_parameter_types`: Map actual → formal parameters
- `detect_recursion`: Mark if recursive call
- `estimate_frequency`: Heuristic call count

**Example**:
```python
def foo():
    helper()  # Edge: foo → helper, kind=CALLS, confidence=1.0
```

### Rule 3: Variable Definition → Variable Node

**ID**: `rule_var_def_001`  
**Match**: NodeKind=VARIABLE, SemanticRole=VARIABLE_DEF  
**Target**: SemanticRole.VARIABLE_DEF  
**Base Confidence**: 0.9 (HIGH)  
**Conditions**:
- Node has assignment in source
- type_name is provided or inferrable

**Transformations**:
- `track_scope`: Local, parameter, global, field
- `infer_range`: Possible value ranges
- `identify_lifecycle`: Definition to last use

### Rule 4: Type Definition → Type Node

**ID**: `rule_type_def_001`  
**Match**: NodeKind=TYPE, SemanticRole=TYPE_DEF  
**Target**: SemanticRole.TYPE_DEF  
**Base Confidence**: 1.0 (CERTAIN)  
**Conditions**:
- Node is class, struct, interface, or type alias
- Provenance.type == "SourceCode"

**Transformations**:
- `extract_fields`: All data fields/properties
- `extract_methods`: All member methods
- `identify_hierarchy`: Inheritance/implementation relationships

### Rule 5: Control Flow Edge

**ID**: `rule_control_flow_001`  
**Match**: EdgeKind=CONTROL_DEPENDENCY  
**Target**: EdgeKind.ControlDependency  
**Base Confidence**: 0.7 (MEDIUM)  
**Conditions**:
- source.kind in [CONTROL_FLOW_NODE, FUNCTION]
- target.kind in [CONTROL_FLOW_NODE, FUNCTION]

**Transformations**:
- `label_branch`: Condition that determines branch
- `estimate_probability`: Success/failure likelihood

**Example**:
```python
if condition:
    process()
else:
    error_handler()
```
→ Two control flow edges with branch labels

### Rule 6: Data Flow Edge

**ID**: `rule_data_flow_001`  
**Match**: EdgeKind=DATA_FLOW  
**Target**: EdgeKind.DataFlow  
**Base Confidence**: 0.6 (MEDIUM)  
**Conditions**:
- Edge connects output to input variables
- One node defines, other uses

**Transformations**:
- `extract_flow_type`: Type of data flowing
- `mark_taint`: If sensitive data involved

### Rule 7: Type Reference → HasType Edge

**ID**: `rule_has_type_001`  
**Match**: EdgeKind=HAS_TYPE  
**Target**: EdgeKind.HasType  
**Base Confidence**: 0.95 (HIGH)  
**Conditions**:
- source is VARIABLE, FUNCTION (for returns), or FIELD
- target is TYPE

**Transformations**:
- `generic_parameters`: Instantiation parameters if generic
- `nullability`: Nullable or not

### Rule 8: Inheritance Edge

**ID**: `rule_inherits_001`  
**Match**: EdgeKind=INHERITS  
**Target**: EdgeKind.Inherits  
**Base Confidence**: 1.0 (CERTAIN)  
**Conditions**:
- source.kind == TYPE
- target.kind == TYPE
- Provenance.type == "SourceCode"

**Transformations**:
- `method_override_detection`: Identify overridden methods
- `interface_satisfaction`: Check all methods implemented

### Rule 9: Module Membership

**ID**: `rule_member_of_001`  
**Match**: EdgeKind=MEMBER_OF  
**Target**: EdgeKind.MemberOf  
**Base Confidence**: 1.0 (CERTAIN)  
**Conditions**:
- target.kind == MODULE
- source not in [UNKNOWN]

**Transformations**:
- `compute_module_coupling`: Import edge density

### Rule 10: External Reference

**ID**: `rule_external_001`  
**Match**: EdgeKind=EXTERNAL_REF  
**Target**: EdgeKind.ExternalRef  
**Base Confidence**: 0.8 (HIGH)  
**Conditions**:
- target.kind == EXTERNAL
- source references external library

**Transformations**:
- `identify_library`: Which external package
- `track_version`: Library version if known

## Heuristic Rules (Lower Confidence)

### Heuristic 1: Implicit Calls (Reflection, Dynamic Dispatch)

**ID**: `heuristic_implicit_call_001`  
**Pattern**: Function called via string name or dynamic reference  
**Target Role**: FUNCTION_CALL  
**Base Confidence**: 0.4 (LOW)  
**Heuristics**:
- String contains function name? +0.2
- Function name appears in context? +0.1
- Type inference suggests callable? +0.15

### Heuristic 2: Inferred Dependencies

**ID**: `heuristic_inferred_dep_001`  
**Pattern**: No explicit import, but code uses external API  
**Target Role**: EXTERNAL_REF  
**Base Confidence**: 0.5 (MEDIUM)  
**Heuristics**:
- API method called directly? +0.2
- Module referenced? +0.15
- Type from external package? +0.15

## Language-Specific Variants

### Python Specializations

#### Rule: Decorator Detection
- Match: Function with @decorator annotation
- Transform: Add `is_decorated`, `decorator_names`
- Confidence boost: +0.1 for explicit metadata

#### Rule: Generator/Coroutine
- Match: Function with `yield` or `async def`
- Target: Mark as COROUTINE in attributes
- Confidence: 1.0 (syntactic marker)

#### Rule: Property Access
- Match: @property method
- Transform: Treat as DATA_ACCESS edge instead of FUNCTION_CALL
- Confidence: 0.95

#### Rule: Metaclass Usage
- Match: Class inherits from ABCMeta or uses __new__
- Transform: Mark as INTERFACE pattern
- Confidence: 0.8

### Java Specializations

#### Rule: Interface Implementation
- Match: `implements` keyword
- Transform: Create IMPLEMENTS edge
- Confidence: 1.0 (syntactic)

#### Rule: Annotation Presence
- Match: @Annotation (including @Override, @Deprecated)
- Transform: Add semantic flags
- Confidence: 1.0

#### Rule: Generic Type Parameters
- Match: `<T>` notation
- Transform: Track type constraints
- Confidence: 0.95

### JavaScript/TypeScript Specializations

#### Rule: Promise/Async
- Match: `async function` or `Promise<T>`
- Transform: Mark as COROUTINE
- Confidence: 1.0 (syntactic)

#### Rule: Object Method
- Match: Method inside object literal
- Transform: Create both FUNCTION_DEF and MEMBER_OF edge
- Confidence: 0.95

#### Rule: Dynamic Property Access
- Match: `obj[key]` notation
- Transform: Mark as LOW confidence DATA_ACCESS
- Confidence: 0.3

## Confidence Adjustment Rules

All rules subject to modification based on context:

### Bonus Factors

- **+0.1**: Explicit type annotation
- **+0.1**: Docstring/comment present
- **+0.05**: Consistent naming (camelCase for methods, etc.)
- **+0.05**: Referenced multiple times in code

### Penalty Factors

- **-0.2**: Inferred from weak heuristic only
- **-0.15**: Type mismatch between expected and actual
- **-0.1**: Unused or unreachable code
- **-0.1**: Deprecated API usage

## Conflict Resolution

When multiple rules match the same node:

1. **Priority**: Use rule with highest base confidence
2. **Aggregation**: If same confidence, merge transformations
3. **Logging**: Record all matches in provenance
4. **User Override**: Allow explicit rule selection via config

## Rule Set Versioning

Rule sets are versioned independently:

```yaml
rule_set:
  id: "default_py39"
  version: "1.0.0"
  language: "python"
  language_version: "3.9+"
  created: "2024-01-01"
  rules:
    - rule_fn_def_001
    - rule_fn_call_001
    - ...
  custom_rules:
    - path: "my_rules.py"
      enabled: true
```

## Custom Rules

Users can define custom rules:

```python
# my_rules.py
from cogant.translate import TranslationRule, SemanticMapping

class MyCustomRule(TranslationRule):
    def id(self) -> str:
        return "custom_my_pattern"
    
    def matches(self, node) -> bool:
        return "special_" in node.name
    
    def apply(self, node) -> SemanticMapping:
        return SemanticMapping(
            id=self.id(),
            source_kind=node.kind,
            source_role=node.role,
            target_role=SemanticRole.ANNOTATION,
            confidence=0.7,
        )
```

## Testing & Validation

Each rule has test cases:

```python
def test_rule_fn_def_001():
    node = NodeData.new(
        id=StableId.new("fn_test"),
        name="test_func",
        kind=NodeKind.FUNCTION,
        role=SemanticRole.FUNCTION_DEF,
        provenance=Provenance.source_code("test.py", 1, 1),
    )
    rule = RuleFnDef001()
    assert rule.matches(node)
    mapping = rule.apply(node)
    assert mapping.confidence == 1.0
    assert mapping.target_role == SemanticRole.FUNCTION_DEF
```

## Performance Notes

Rule application order matters for performance:

1. Fast rules first (syntactic checks)
2. Expensive rules later (heuristics, CFG analysis)
3. Parallelizable rules grouped

For 100K functions, typical rule application: <5s on 4 cores.

## References

- [Translation Engine](../../rust/cogant-translate/src/lib.rs)
- [Semantic Roles](../ontology/gnn-roles.md)
- [IR Schemas](../rfc/0002-ir-schemas.md)
