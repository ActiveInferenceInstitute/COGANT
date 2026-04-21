# Translation Rule Taxonomy

The 22 translation rules are organized into 5 families based on the program-graph patterns they match and the semantic roles they produce.

## Rule families overview

| Family | Count | Semantic Roles Produced | Rules |
|--------|-------|------------------------|-------|
| **Structural** | 5 | HIDDEN_STATE, OBSERVATION, ACTION, DATA_FLOW | `ContainmentRule`, `DataPipelineRule`, `InheritanceRule`, `MutatingSubsystemRule`, `ReadOnlyInputRule` |
| **Semantic** | 5 | ACTION, CONTEXT, OBSERVATION, POLICY, CONSTRAINT | `ActionRule`, `ContextRule`, `ObservationRule`, `PolicyRule`, `PreferenceRule` |
| **Behavioral** | 4 | ACTION, HIDDEN_STATE, POLICY, OBSERVATION | `EventBusRule`, `OrchestratorRule`, `StateMachineRule`, `TestAssertionRule` |
| **Control** | 3 | PARAMETER, CONTEXT | `ConfigRule`, `FeatureFlagRule`, `ParameterRule` |
| **Resilience** | 5 | ACTION, POLICY, ERROR_HANDLING, CONTEXT, HIDDEN_STATE | `CircuitBreakerRule`, `ErrorBoundaryRule`, `RateLimiterRule`, `RetryPatternRule`, `SingletonAccessRule` |

### Structural rules (5)

Match graph topology patterns like inheritance chains, data flow paths, and read-only access.

- **ContainmentRule** — Class contains 5+ methods → aggregates method roles via majority vote
- **DataPipelineRule** — Function reads A, writes B (A ≠ B) → DATA_FLOW
- **InheritanceRule** — Class inherits from Abstract/Handler → POLICY
- **MutatingSubsystemRule** — Class has WRITES/MUTATES edges → HIDDEN_STATE
- **ReadOnlyInputRule** — Module reads, zero writes → OBSERVATION

### Semantic rules (5)

Match naming conventions and keyword signatures to assign semantic meaning.

- **ActionRule** — Name matches `set`, `update`, `create`, `delete`, `send`, `push`, `execute`, `run`, `process`, `handle`, `dispatch` → ACTION
- **ContextRule** — Name matches `config`, `settings`, `env`, `options`, `params` → CONTEXT
- **ObservationRule** — Name matches `get`, `read`, `fetch`, `query`, `display`, `show`, `status`, `info`, `list` → OBSERVATION
- **PolicyRule** — Name matches `middleware`, `handler`, `controller`, `manager`, `router`, `dispatcher`, `scheduler` → POLICY
- **PreferenceRule** — Name matches `validate`, `check`, `test_`, `assert_`, `Validator`, `Checker` → CONSTRAINT

### Behavioral rules (4)

Match event, orchestration, state, and test patterns that reveal reactive behavior.

- **EventBusRule** — Node kind is EVENT with subscribers → OBSERVATION
- **OrchestratorRule** — Node has 3+ outgoing CALLS edges → ORCHESTRATION (POLICY-like)
- **StateMachineRule** — Name/metadata matches `state`, `transition`, `machine`, or state enum patterns → HIDDEN_STATE
- **TestAssertionRule** — Function name contains `test` and has CALLS edges → CONSTRAINT

### Control rules (3)

Match knobs, toggles, and tunable parameters that steer program behavior.

- **ConfigRule** — Node kind is CONFIGURATION → CONTEXT
- **FeatureFlagRule** — Node kind is FEATURE_FLAG → CONTEXT
- **ParameterRule** — Tunable numeric/string constants (`learning_rate`, `threshold`, `epsilon`, etc.) → PARAMETER

### Resilience rules (5)

Match defensive patterns like error handling, retries, rate limiting, and singleton access.

- **CircuitBreakerRule** — Has GUARDS edge plus retry keyword/metadata → CIRCUIT_BREAKER (POLICY-like)
- **ErrorBoundaryRule** — Function has CATCHES or THROWS edges → ERROR_HANDLING
- **RateLimiterRule** — Name matches `rate`, `limit`, `throttle`, `quota`, or decorator pattern → ACTION
- **RetryPatternRule** — Name matches `retry`, `backoff`, `circuit`, `breaker`, `timeout`, `fallback` → POLICY
- **SingletonAccessRule** — Variable/class read by 3+ modules across 3+ paths → CONTEXT

## How rules are applied

The translation engine in [`cogant.translate.engine`](../api/translate.md#engine) drives rule application via a **fixpoint loop**:

1. **Priority dispatch** — Rules are sorted by `priority` (lower value = earlier application). Structural rules run first (highest priority); semantic and behavioral rules run mid-loop; resilience rules (lowest priority) run last to refine earlier outputs.

2. **Conflict resolution** — When multiple rules fire on the same node, the engine retains the mapping with the highest confidence score. If scores tie, the lower-priority rule wins.

3. **Convergence** — Each iteration applies all fired rules and aggregates new mappings. The loop terminates when:
   - No new mappings are added (convergence), or
   - `max_iterations` is reached (default: 10)

4. **Provenance** — Every mapping carries metadata: the rule name, confidence, firing condition, and iteration count.

See [`cogant.translate` → Engine](../api/translate.md#engine) for the priority/confidence loop details and the per-rule `.explain()` API for debugging why a rule fired or was rejected.

## Adding a custom rule

Custom rules extend the pipeline without modifying core code. Follow these three steps:

### 1. Subclass TranslationRule

```python
from cogant.translate.engine import TranslationRule
from cogant.graph import Node, NodeKind
from cogant.semantics import SemanticRole

class MyCustomRule(TranslationRule):
    """Short docstring."""

    name = "MyCustomRule"
    priority = 50  # 0–100; lower fires earlier
    family = "semantic"  # or "structural", "behavioral", "control", "resilience"
```

### 2. Implement apply() and explain()

```python
def apply(self, node: Node, context: "TranslationContext") -> Optional[SemanticRole]:
    """
    Return a SemanticRole if the rule matches, else None.
    """
    # Check node properties
    if node.kind == NodeKind.FUNCTION and "my_pattern" in node.name:
        return SemanticRole.ACTION
    return None

def explain(self, node: Node) -> str:
    """One-line explanation of why the rule did or didn't fire."""
    return f"Matched 'my_pattern' in {node.name}"
```

### 3. Register with the engine

```python
from cogant.translate.engine import TranslationEngine

engine = TranslationEngine()
engine.register_rule(MyCustomRule())
```

For production rules, add them to the appropriate family module under `py/cogant/translate/rules/` and update the rule manifest in the `cogant.translate` package (see the [translate API](../api/translate.md) and repository `py/cogant/translate/__init__.py`).

## References

- [Translation Rules Reference](../reference/translation_rules.md) — Complete table with all 22 rules, confidence scores, and implementing modules
- [Semantic Roles](../reference/semantic_roles.md) — The seven-role taxonomy (HIDDEN_STATE, OBSERVATION, etc.)
- [Role Assignment Concepts](../concepts/role_assignment.md) — Conceptual walkthrough of how rules assign roles
- [`cogant.translate` API](../api/translate.md) — Engine, rules, and rule modules
- Rule source: `py/cogant/translate/rules/` in the repository (structural.py, semantic.py, behavioral.py, control.py, resilience.py)
