## Semantic Roles

COGANT's `SemanticMapping.kind` values are Active Inference-oriented roles emitted by
`py/cogant/translate/rules/`, not NLP-style code roles such as `FUNCTION_DEF` or
`VARIABLE_USE`. Seven labels form the Active Inference contract:
`HIDDEN_STATE`, `OBSERVATION`, `ACTION`, `POLICY`, `PREFERENCE`, `CONSTRAINT`, and `CONTEXT`. Supporting
roles such as `DATA_FLOW`, `ERROR_HANDLING`, `ORCHESTRATION`, and `CIRCUIT_BREAKER` preserve
additional evidence for connections, diagnostics, and dashboards.

## Active Inference roles → detection rules

The core Active Inference semantic roles emitted into a [GNN](../concepts/gnn.md) are detected by rules in `cogant.translate.rules`. Each row links to the rule family's API entry and to the per-rule reference page.

| Role | Detected by | Rule family / module | API reference |
|------|-------------|----------------------|---------------|
| HIDDEN_STATE | `MutatingSubsystemRule` | structural — `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules), [translation rules reference](translation_rules.md) |
| OBSERVATION | `ObservationRule`, `ReadOnlyInputRule`, `EventBusRule` | semantic / structural / behavioral — `py/cogant/translate/rules/{semantic,structural,behavioral}.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [`cogant.translate` → Structural rules](../api/translate.md#structural-rules), [`cogant.translate` → Behavioral rules](../api/translate.md#behavioral-rules), [translation rules reference](translation_rules.md) |
| ACTION | `ActionRule` | semantic — `py/cogant/translate/rules/semantic.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [translation rules reference](translation_rules.md) |
| POLICY | `PolicyRule`, `InheritanceRule`, `RetryPatternRule`, `CircuitBreakerRule` | semantic / structural / resilience — `py/cogant/translate/rules/{semantic,structural,resilience}.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [`cogant.translate` → Structural rules](../api/translate.md#structural-rules), [`cogant.translate` → Resilience rules](../api/translate.md#resilience-rules), [translation rules reference](translation_rules.md) |
| PREFERENCE | Explicit preference metadata or custom rules; validators/tests use CONSTRAINT in the shipped rule set | GNN import/export / extension point | [`cogant.gnn`](../api/gnn.md), [translation rules reference](translation_rules.md) |
| CONSTRAINT | `PreferenceRule`, `TestAssertionRule` | semantic / behavioral — `py/cogant/translate/rules/{semantic,behavioral}.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [`cogant.translate` → Behavioral rules](../api/translate.md#behavioral-rules), [translation rules reference](translation_rules.md) |
| CONTEXT | `ContextRule`, `ConfigRule`, `FeatureFlagRule`, `SingletonAccessRule` | semantic / control / resilience — `py/cogant/translate/rules/{semantic,control,resilience}.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules), [`cogant.translate` → Control-flow rules](../api/translate.md#control-flow-rules), [`cogant.translate` → Resilience rules](../api/translate.md#resilience-rules), [translation rules reference](translation_rules.md) |
| DATA_FLOW | `DataPipelineRule` | structural — `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules), [translation rules reference](translation_rules.md) |

For the conceptual narrative, see [How COGANT assigns roles](../concepts/role_assignment.md). For the engine that runs every rule against every node, see [`cogant.translate` → Engine](../api/translate.md#engine).
