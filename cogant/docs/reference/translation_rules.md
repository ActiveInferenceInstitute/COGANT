## Translation Rules

Translation rules map (NodeKind, SemanticRole) → target semantic role.

**Example rule**:
```python
Rule: FUNCTION + FUNCTION_DEF → FUNCTION_DEF
Confidence: 1.0 (syntactic)
Conditions:
  - type_name is not None
  - provenance.type == "SourceCode"
Transformations:
  - extract_signature: Parse signature
  - compute_complexity: Estimate complexity
  - identify_side_effects: Annotate side effects
```

Rules are:
- **Composable**: Apply multiple rules, aggregate results
- **Extensible**: User can define custom rules
- **Traceable**: Log all rule matches in provenance
- **Versioned**: Rules evolve with language versions

See [Translation Rules](https://github.com/cogant-contributors/cogant/blob/main/cogant/specs/mappings/code-to-gnn.md) for full reference.

## Rule families and their implementing modules

The 19 active translation rules are organized into five families. Each family lives in its own module under `py/cogant/translate/rules/` and is documented in [`cogant.translate` → Rules](../api/translate.md#rules). The rule engine that drives them — including the priority/confidence conflict-resolution loop — lives in [`cogant.translate.engine`](../api/translate.md#engine).

| Rule | Family | Fires when | Produces | Confidence | Implementing module | API reference |
|------|--------|------------|----------|------------|---------------------|---------------|
| `ReadOnlyInputRule` | structural | Module has READS edges, zero WRITES | OBSERVATION | 0.70 | `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules) |
| `MutatingSubsystemRule` | structural | Class has any WRITES/MUTATES edge | HIDDEN_STATE | 0.75 | `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules) |
| `InheritanceRule` | structural | Class has INHERITS edges | POLICY (when base is Abstract/Handler) | 0.70 | `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules) |
| `ContainmentRule` | structural | Class contains 5+ methods | Majority vote across method roles | 0.75 | `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules) |
| `DataPipelineRule` | structural | Function reads from A, writes to B (A ≠ B) | DATA_FLOW | 0.75 | `py/cogant/translate/rules/structural.py` | [`cogant.translate` → Structural rules](../api/translate.md#structural-rules) |
| `ObservationRule` | semantic | Name matches `get`, `read`, `fetch`, `query`, `display`, `show`, `status`, `info`, `list` | OBSERVATION | 0.85 (keyword) / 0.70 (edge-only) | `py/cogant/translate/rules/semantic.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules) |
| `ActionRule` | semantic | Name matches `set`, `update`, `create`, `delete`, `send`, `push`, `execute`, `run`, `process`, `handle`, `dispatch` | ACTION | 0.80 | `py/cogant/translate/rules/semantic.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules) |
| `PolicyRule` | semantic | Name matches `middleware`, `handler`, `controller`, `manager`, `router`, `dispatcher`, `scheduler` | POLICY | 0.80 | `py/cogant/translate/rules/semantic.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules) |
| `PreferenceRule` | semantic | Name matches `validate`, `check`, `test_`, `assert_`, `Validator`, `Checker` | CONSTRAINT | 0.85 | `py/cogant/translate/rules/semantic.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules) |
| `ContextRule` | semantic | Name matches `config`, `settings`, `env`, `options`, `params` | CONTEXT | 0.80 | `py/cogant/translate/rules/semantic.py` | [`cogant.translate` → Semantic rules](../api/translate.md#semantic-rules) |
| `OrchestratorRule` | behavioral | Node has 3+ outgoing CALLS edges | ORCHESTRATION (POLICY-like) | 0.80 | `py/cogant/translate/rules/behavioral.py` | [`cogant.translate` → Behavioral rules](../api/translate.md#behavioral-rules) |
| `TestAssertionRule` | behavioral | Function name contains `test` and has CALLS edges | CONSTRAINT | 0.85 | `py/cogant/translate/rules/behavioral.py` | [`cogant.translate` → Behavioral rules](../api/translate.md#behavioral-rules) |
| `EventBusRule` | behavioral | Node kind is `EVENT` with subscribers | OBSERVATION | 0.75 | `py/cogant/translate/rules/behavioral.py` | [`cogant.translate` → Behavioral rules](../api/translate.md#behavioral-rules) |
| `ConfigRule` | control | Node kind is `CONFIGURATION` | CONTEXT | 0.90 | `py/cogant/translate/rules/control.py` | [`cogant.translate` → Control-flow rules](../api/translate.md#control-flow-rules) |
| `FeatureFlagRule` | control | Node kind is `FEATURE_FLAG` | CONTEXT | 0.85 | `py/cogant/translate/rules/control.py` | [`cogant.translate` → Control-flow rules](../api/translate.md#control-flow-rules) |
| `RetryPatternRule` | resilience | Name matches `retry`, `backoff`, `circuit`, `breaker`, `timeout`, `fallback` | POLICY | 0.70 | `py/cogant/translate/rules/resilience.py` | [`cogant.translate` → Resilience rules](../api/translate.md#resilience-rules) |
| `ErrorBoundaryRule` | resilience | Function has CATCHES or THROWS edges | ERROR_HANDLING | 0.70 | `py/cogant/translate/rules/resilience.py` | [`cogant.translate` → Resilience rules](../api/translate.md#resilience-rules) |
| `SingletonAccessRule` | resilience | Variable/class read by 3+ modules across 3+ paths | CONTEXT | 0.65 | `py/cogant/translate/rules/resilience.py` | [`cogant.translate` → Resilience rules](../api/translate.md#resilience-rules) |
| `CircuitBreakerRule` | resilience | Has GUARDS edge plus a retry keyword/metadata | CIRCUIT_BREAKER (POLICY-like) | 0.80 | `py/cogant/translate/rules/resilience.py` | [`cogant.translate` → Resilience rules](../api/translate.md#resilience-rules) |

For the conceptual walkthrough of how these rules fire in priority order, see [How COGANT assigns roles](../concepts/role_assignment.md). For the seven-role taxonomy that the rules emit, see [Semantic roles](semantic_roles.md). For the engine itself — the priority/confidence conflict-resolution loop and the per-rule `.explain()` API — see [`cogant.translate` → Engine](../api/translate.md#engine).

