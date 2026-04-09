## Semantic Roles

Roles classify entities for GNN training. Key roles:

| Role | Meaning | Example |
|------|---------|---------|
| FUNCTION_DEF | Function definition | `def foo():` |
| FUNCTION_CALL | Function invocation | `foo()` |
| VARIABLE_DEF | Variable definition | `x = 5` |
| VARIABLE_USE | Variable reference | `print(x)` |
| TYPE_DEF | Type definition | `class A:` |
| METHOD_DEF | Method definition | `def method(self):` |
| CONTROL_FLOW | Control structure | `if x:` |
| ERROR_HANDLING | Exception handling | `try: ... except:` |
| DATA_ACCESS | Data access | `obj.field` |
| INHERITANCE | Type hierarchy | `class B(A):` |
| POLYMORPHISM | Virtual dispatch | `obj.method()` (overridden) |

See [GNN Roles Ontology](../specs/ontology/gnn-roles.md) for complete taxonomy.

