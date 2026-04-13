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

See [GNN Roles Ontology](https://github.com/cogant-contributors/cogant/blob/main/cogant/specs/ontology/gnn-roles.md) for complete taxonomy.

## Active Inference roles → detection rules

The seven Active Inference semantic roles emitted into a [GNN](../concepts/gnn.md) are detected by rules in `cogant.translate.rules`. Each row links to the rule family's API entry and to the per-rule reference page.

| Role | Detected by | Rule family / module | API reference |
|------|-------------|----------------------|---------------|
| HIDDEN_STATE | `MutatingSubsystemRule` | structural — `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules), [translation rules reference](translation_rules.md) |
| OBSERVATION | `ObservationRule`, `ReadOnlyInputRule`, `EventBusRule` | semantic / structural / behavioral — `py/cogant/translate/rules/{semantic,structural,behavioral}.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [`cogant.translate` → Structural rules](../api/translate.md#structural-rules), [`cogant.translate` → Behavioral rules](../api/translate.md#behavioral-rules), [translation rules reference](translation_rules.md) |
| ACTION | `ActionRule` | semantic — `py/cogant/translate/rules/semantic.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [translation rules reference](translation_rules.md) |
| POLICY | `PolicyRule`, `InheritanceRule`, `RetryPatternRule`, `CircuitBreakerRule` | semantic / structural / resilience — `py/cogant/translate/rules/{semantic,structural,resilience}.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [`cogant.translate` → Structural rules](../api/translate.md#structural-rules), [`cogant.translate` → Resilience rules](../api/translate.md#resilience-rules), [translation rules reference](translation_rules.md) |
| CONSTRAINT | `PreferenceRule`, `TestAssertionRule` | semantic / behavioral — `py/cogant/translate/rules/{semantic,behavioral}.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [`cogant.translate` → Behavioral rules](../api/translate.md#behavioral-rules), [translation rules reference](translation_rules.md) |
| CONTEXT | `ContextRule`, `ConfigRule`, `FeatureFlagRule`, `SingletonAccessRule` | semantic / control / resilience — `py/cogant/translate/rules/{semantic,control,resilience}.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [`cogant.translate` → Control-flow rules](../api/translate.md#control-flow-rules), [`cogant.translate` → Resilience rules](../api/translate.md#resilience-rules), [translation rules reference](translation_rules.md) |
| DATA_FLOW | `DataPipelineRule` | structural — `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules), [translation rules reference](translation_rules.md) |

For the conceptual narrative, see [How COGANT assigns roles](../concepts/role_assignment.md). For the engine that runs every rule against every node, see [`cogant.translate` → Engine](../api/translate.md#engine).

