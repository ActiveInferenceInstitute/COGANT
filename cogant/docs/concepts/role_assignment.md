# How COGANT assigns roles

COGANT's rule engine is the component that looks at a [program graph](program_graph.md) and decides: "This function is an observation. That class is hidden state. This validator is a constraint." This page explains the engine, the rule families, how conflicts are resolved, and what each of the seven semantic roles means.

## The rule engine

The engine lives in `py/cogant/translate/engine.py`. It takes a `ProgramGraph` and a list of `TranslationRule` instances, runs every rule against every node, collects the resulting `SemanticMapping` records, and resolves conflicts when multiple rules fire on the same node.

Each rule implements two methods:

- `matches(graph, query)` -- returns a list of matched patterns (node IDs + evidence)
- `apply(graph, match)` -- converts a match into a `SemanticMapping` with a confidence score, provenance, and a `MappingKind` label

Rules also carry a `priority` and a `confidence_score`. When two rules assign different roles to the same code fragment, the engine picks the one with the higher `(priority, confidence_score)` tuple. This is how COGANT handles ambiguity: a function named `handle_request` triggers both `ActionRule` (keyword "handle") and `PolicyRule` (keyword "handle"), and the conflict is resolved by whichever rule produces stronger evidence.

## The five rule families

Rules are organized into five families, each in its own module under `py/cogant/translate/rules/`:

### Structural rules (`structural.py`)

These rules look at graph topology -- edges, degree, containment -- without reading node names.

| Rule | Fires when | Produces | Confidence |
| --- | --- | --- | --- |
| ReadOnlyInputRule | Module has READS edges, zero WRITES | OBSERVATION | 0.70 |
| MutatingSubsystemRule | Class has any WRITES/MUTATES edge | HIDDEN_STATE | 0.75 |
| InheritanceRule | Class has INHERITS edges | POLICY (if base is Abstract/Handler) | 0.70 |
| ContainmentRule | Class contains 5+ methods | Majority vote across method names | 0.75 |
| DataPipelineRule | Function reads from A, writes to B (A != B) | DATA_FLOW | 0.75 |

### Semantic rules (`semantic.py`)

These rules match on function/class names using curated keyword lists.

| Rule | Keywords | Produces | Confidence |
| --- | --- | --- | --- |
| ObservationRule | get, read, fetch, query, display, show, status, info, list | OBSERVATION | 0.85 (keyword) / 0.70 (edge-only) |
| ActionRule | set, update, create, delete, send, push, execute, run, process, handle, dispatch | ACTION | 0.80 |
| PolicyRule | middleware, handler, controller, manager, router, dispatcher, scheduler | POLICY | 0.80 |
| PreferenceRule | validate, check, test_, assert_, Validator, Checker | CONSTRAINT | 0.85 |
| ContextRule | config, settings, env, options, params | CONTEXT | 0.80 |

### Behavioral rules (`behavioral.py`)

These rules detect runtime patterns from graph structure.

| Rule | Fires when | Produces | Confidence |
| --- | --- | --- | --- |
| OrchestratorRule | Node has 3+ outgoing CALLS edges | ORCHESTRATION | 0.80 |
| TestAssertionRule | Function name contains "test" + has CALLS edges | CONSTRAINT | 0.85 |
| EventBusRule | Node kind is EVENT with subscribers | OBSERVATION | 0.75 |

### Control rules (`control.py`)

These rules detect configuration and feature management.

| Rule | Fires when | Produces | Confidence |
| --- | --- | --- | --- |
| ConfigRule | Node kind is CONFIGURATION | CONTEXT | 0.90 |
| FeatureFlagRule | Node kind is FEATURE_FLAG | CONTEXT | 0.85 |

### Resilience rules (`resilience.py`)

These rules detect error handling and fault tolerance patterns.

| Rule | Fires when | Produces | Confidence |
| --- | --- | --- | --- |
| RetryPatternRule | Name contains retry, backoff, circuit, breaker, timeout, fallback | POLICY | 0.70 |
| ErrorBoundaryRule | Function has CATCHES or THROWS edges | ERROR_HANDLING | 0.70 |
| SingletonAccessRule | Variable/class read by 3+ modules across 3+ paths | CONTEXT | 0.65 |
| CircuitBreakerRule | Has GUARDS edge + retry keyword/metadata | CIRCUIT_BREAKER | 0.80 |

## How rules fire: a worked example

Consider this Python class:

```python
class UserService:
    def __init__(self):
        self._cache = {}           # MutatingSubsystemRule fires (WRITES edge)

    def get_user(self, id: str):   # ObservationRule fires (keyword "get")
        return self._cache.get(id)

    def update_user(self, id, data):  # ActionRule fires (keyword "update")
        self._cache[id] = data

    def validate_user(self, data):    # PreferenceRule fires (keyword "validate")
        assert "email" in data
```

The engine produces four mappings:

1. `UserService` -> HIDDEN_STATE (confidence 0.75, from MutatingSubsystemRule)
2. `get_user` -> OBSERVATION (confidence 0.85, from ObservationRule keyword match)
3. `update_user` -> ACTION (confidence 0.80, from ActionRule keyword match)
4. `validate_user` -> CONSTRAINT (confidence 0.85, from PreferenceRule keyword match)

If `ContainmentRule` also fires on `UserService` (it has methods), the majority-vote classification at confidence 0.75 is resolved against the per-method rules which carry higher confidence. The per-method mappings win.

## The seven semantic roles

### HIDDEN_STATE

Internal mutable state that is not directly observable from outside. Private fields, caches, buffers, accumulators. In the [GNN output](gnn.md), these become `StateSpaceBlock` variables. In the [Markov blanket](markov_blanket.md), these are internal nodes.

### OBSERVATION

Read-only access points that expose hidden state. Getter methods, query functions, logging handlers. These become observation modalities in the GNN and feed the A (likelihood) matrix.

### ACTION

Functions that change hidden state. Setters, mutators, event publishers, request handlers. These become action variables in the GNN and define the B (transition) matrix slices.

### POLICY

Control logic that selects which action to execute. Controllers, routers, schedulers, retry strategies. These map to the policy layer in Active Inference -- the mechanism that minimizes expected free energy.

### CONSTRAINT

Validators and tests that define what the system considers correct. Assertions, schema validators, type checkers. These populate the C (preference) matrix in the GNN.

### CONTEXT

Configuration, feature flags, and global state that parameterize the system. These populate the D (prior) matrix in the GNN -- the initial beliefs before any observations.

### DATA_FLOW

Functions that read from one source and write to a different target. Transformation pipelines, ETL functions, adapters. These appear in the Connections section of the GNN.

## Confidence tiers

Every mapping carries a `ConfidenceTier` label:

- **STATIC_ONLY** -- based purely on static analysis (all current rules)
- **STATIC_PLUS_RUNTIME** -- static + dynamic trace evidence (e.g., EventBusRule)
- **RUNTIME_ONLY** -- dynamic evidence only (future)
- **HUMAN_REVIEWED** -- manually approved (future)

The confidence score (0.65 to 0.90) determines conflict resolution priority. `ConfigRule` at 0.90 is the highest confidence in the entire family -- explicit configuration is ground truth. `SingletonAccessRule` at 0.65 is the lowest -- "read by many modules" is a weak signal.

## Further reading

- [What is a GNN?](gnn.md) -- how role assignments become GNN sections
- [Active Inference from a programmer's perspective](active_inference.md) -- the theory behind the seven roles
- [Program graphs in COGANT](program_graph.md) -- the graph structure that rules analyze
- [Markov blankets in codebases](markov_blanket.md) -- the complementary partitioning approach
