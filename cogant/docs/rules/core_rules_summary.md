## Core Rules Summary

### Functions

| Rule ID | Pattern | Target Role | Confidence | Conditions |
|---------|---------|-------------|------------|-----------|
| rule_fn_def_001 | FUNCTION + FUNCTION_DEF | FUNCTION_DEF | 1.0 | type_name exists, source code |
| rule_fn_call_001 | CALLS edge | CALLS | 0.85 | explicit call in source |
| rule_method_def_001 | FUNCTION in class | METHOD_DEF | 1.0 | parent is TYPE |
| rule_method_call_001 | METHOD call | METHOD_CALL | 0.90 | receiver type known |
| rule_polymorphism_001 | Virtual method | POLYMORPHISM | 0.6 | inferred from type hierarchy |

### Variables

| Rule ID | Pattern | Target Role | Confidence |
|---------|---------|-------------|------------|
| rule_var_def_001 | VARIABLE + VARIABLE_DEF | VARIABLE_DEF | 0.9 |
| rule_var_use_001 | VARIABLE + VARIABLE_USE | VARIABLE_USE | 0.95 |
| rule_field_access_001 | Field access | DATA_ACCESS | 0.8 |

### Types

| Rule ID | Pattern | Target Role | Confidence |
|---------|---------|-------------|------------|
| rule_type_def_001 | TYPE + TYPE_DEF | TYPE_DEF | 1.0 |
| rule_type_ref_001 | Type annotation | TYPE_REF | 0.95 |
| rule_generic_param_001 | Generic parameter | GENERIC_PARAM | 1.0 |

### Control Flow

| Rule ID | Pattern | Target Role | Confidence |
|---------|---------|-------------|------------|
| rule_control_flow_001 | if/while/for | CONTROL_FLOW | 0.7 |
| rule_error_handling_001 | try/catch | ERROR_HANDLING | 0.95 |
| rule_error_flow_001 | Exception propagation | ERROR_FLOW | 0.6 |

### Relationships

| Rule ID | Pattern | Target Edge | Confidence |
|---------|---------|-------------|------------|
| rule_inherits_001 | Class inheritance | INHERITS | 1.0 |
| rule_implements_001 | Interface implementation | IMPLEMENTS | 1.0 |
| rule_has_type_001 | Type annotation | HAS_TYPE | 0.95 |
| rule_member_of_001 | Module membership | MEMBER_OF | 1.0 |
