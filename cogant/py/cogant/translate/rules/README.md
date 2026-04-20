# `cogant.translate.rules`

Bundled `TranslationRule` implementations consumed by
[`cogant.translate.engine.TranslationEngine`](../AGENTS.md). Rules are
pure functions over a `ProgramGraph` that emit zero or more
`SemanticMapping` records assigning Active Inference roles
(HIDDEN_STATE, OBSERVATION, ACTION, …) to code elements.

## Rule families

Each module groups thematically related rules. The umbrella package
re-exports every class so `from cogant.translate.rules import *`
continues to work as before.

| Module | Rules |
| --- | --- |
| `structural`  | `ReadOnlyInputRule`, `ContainmentRule`, `InheritanceRule`, `MutatingSubsystemRule`, `DataPipelineRule` |
| `behavioral`  | `OrchestratorRule`, `EventBusRule`, `TestAssertionRule`, `StateMachineRule` |
| `control`     | `ConfigRule`, `FeatureFlagRule`, `ParameterRule` |
| `semantic`    | `ObservationRule`, `ActionRule`, `PolicyRule`, `PreferenceRule`, `ContextRule` |
| `resilience`  | `RetryPatternRule`, `ErrorBoundaryRule`, `SingletonAccessRule`, `CircuitBreakerRule`, `RateLimiterRule` |

Total: **22 built-in rules**, all subclasses of
`cogant.translate.engine.TranslationRule`.

## Conventions

* Rules are pure: no I/O, no globals; their output depends only on the
  input `ProgramGraph` and the rule's own constructor parameters.
* Each rule returns a list of `SemanticMapping` instances; an empty
  list means "did not fire". The engine deduplicates and resolves
  conflicts across rules.
* Confidence is reported per mapping; the engine respects
  `TranslationConfig.confidence_threshold`.
* Every rule has at least one unit test under
  `tests/unit/translate/test_rules_*.py`.

See [`AGENTS.md`](AGENTS.md) for per-rule semantics and the parent
engine doc in [`../AGENTS.md`](../AGENTS.md).
