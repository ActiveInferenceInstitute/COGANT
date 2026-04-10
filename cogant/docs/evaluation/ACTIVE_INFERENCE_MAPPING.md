# Active Inference Mapping Theory

## Overview

This document records the theoretical justification for how COGANT maps
software constructs to Active Inference (AI) roles and how those mappings
are composed into a Markov blanket and the A/B/C/D generative-model
matrices. It complements the qualitative validation tests in
``tests/unit/test_ai_role_validation.py`` (repository path) and the rule implementations
under ``py/cogant/translate/rules/``.

The mapping pipeline is intentionally *structural*: every role is
assigned by inspecting the program graph (`NodeKind`, `EdgeKind`,
name keywords, degree statistics). No language-specific heuristics
beyond Python keyword scanning are required, which is what lets the
same engine later cover Rust, TypeScript, and Lean targets.

## The Four Fundamental Roles

Active Inference partitions an agent into four disjoint sets:

```
    internal (mu)  <---  sensory (s)  <---  external (eta)
                   --->  active  (a)  --->
```

COGANT maps software constructs to these roles as follows:

### Hidden State (mu) - internal states

Code patterns that become HIDDEN_STATE:

- **Mutable class attributes** - instance variables written by methods
  (e.g. `Calculator.display`, `Calculator.accumulator`,
  `Calculator.history`, `RetryableEventHandler.failed_events`).
- **Classes with WRITES edges** - caught by `MutatingSubsystemRule`
  (`py/cogant/translate/rules/structural.py`), which emits
  `HIDDEN_STATE` whenever a class has at least one incoming or outgoing
  `WRITES`/`MUTATES` edge.
- **State machines** - attributes + transition methods.
- **Caches, accumulators, buffers** - internal scratch space.

Rule: `MutatingSubsystemRule` -> `MappingKind.HIDDEN_STATE`.

### Observation (s) - sensory states

Code patterns that become OBSERVATION:

- **Pure getter functions** - keywords
  `get | read | fetch | query | display | show | status | info | list`
  or any function/method with `READS` edges and zero `WRITES`.
- **Logging handlers and monitors** - they consume events but never
  mutate shared state.
- **Read-only modules** - entire modules whose only outbound edges are
  `READS`; these are picked up by `ReadOnlyInputRule`.
- **Event subscribers that don't modify state**.

Rules:
- `ObservationRule` (`semantic.py`) -> `MappingKind.OBSERVATION`.
- `ReadOnlyInputRule` (`structural.py`) -> `MappingKind.OBSERVATION`.

### Action (a) - active states

Code patterns that become ACTION:

- **Setter/mutator methods** - keywords
  `set | update | create | delete | send | push | execute | run |
  process | handle | dispatch`, usually accompanied by `WRITES`
  edges.
- **Event publishers** - `EventBus.publish`, `dispatch`, etc.
- **Request handlers** - `handle_request`, `process_request`,
  `process_response`.

Rule: `ActionRule` (`semantic.py`) -> `MappingKind.ACTION`.

### Policy (pi) - control under uncertainty

Code patterns that become POLICY:

- **Handler / Controller / Manager / Router / Dispatcher / Scheduler
  classes** - anything matching the canonical control-plane
  vocabulary.
- **Retry, backoff, circuit-breaker, fallback, timeout patterns** -
  picked up by `RetryPatternRule`.
- **Functions with high out-degree** - orchestrators recognised by
  `OrchestratorRule` in `behavioral.py`.
- **Strategy / policy pattern implementors** (via inheritance -
  `InheritanceRule`).

Rules:
- `PolicyRule` (`semantic.py`) -> `MappingKind.POLICY`.
- `RetryPatternRule` (`resilience.py`) -> `MappingKind.POLICY`.
- `InheritanceRule` (`structural.py`) -> `MappingKind.POLICY` when
  bases look like handlers/controllers.

### Secondary roles

These roles are not part of the canonical Markov blanket but are useful
for GNN bundles and downstream analysis:

- `CONSTRAINT` - `assert_*`, `test_*`, `validate_*`, `Validator` /
  `Checker` classes (`PreferenceRule`, `TestAssertionRule`).
- `CONTEXT` - configuration, feature flags, singleton/global state
  (`ConfigRule`, `FeatureFlagRule`, `ContextRule`,
  `SingletonAccessRule`).
- `DATA_FLOW` - reader-writer pipelines whose read sources differ
  from their write targets (`DataPipelineRule`).
- `ERROR_HANDLING` - functions with `CATCHES` / `THROWS` edges
  (`ErrorBoundaryRule`).
- `CIRCUIT_BREAKER` - `GUARDS` edge + retry/fallback keywords
  (`CircuitBreakerRule`).
- `ORCHESTRATION` - high-fan-out controllers (`OrchestratorRule`).

## Markov Blanket Partitioning

COGANT's `MarkovBlanketExtractor`
(`py/cogant/markov/extractor.py`) offers five seed-selection
strategies. The default `auto` strategy picks the module with the best
cohesion / coupling ratio:

```
score(module) = internal_edges / (internal_edges + boundary_edges + 1)
```

Once a seed set `S` is chosen, the pure-function partitioner
`partition_by_seeds` (`py/cogant/markov/blanket.py`) walks the
undirected projection of the program graph:

1. A node `n` in `S` with no neighbour outside `S` is **internal** (mu).
2. A node `n` in `S` with external neighbours is **sensory** (only
   incoming edges) or **active** (any outgoing edge, bidirectional
   defaults to active).
3. A node `n` outside `S` is **external** (eta). Nodes adjacent to `S`
   are tagged with `neighbour` metadata.

The partition is complete, mutually exclusive, and deterministic for a
given graph and seed set.

## A / B / C / D Matrix Derivation

| Matrix | Shape | Source edges | Semantics |
| --- | --- | --- | --- |
| A (likelihood) | `[n_obs x n_states]` | `READS`, `OBSERVES` | `P(observation | hidden_state)` |
| B (transition) | `[n_states x n_states x n_actions]` | `WRITES`, `MUTATES`, `CALLS` | `P(next_state | current_state, action)` |
| C (preference) | `[n_obs]` | `CONSTRAINT` confidence scores | `log P(preferred observations)` |
| D (prior) | `[n_states]` | `CONFIGURATION` nodes + domain defaults | `P(initial hidden state)` |

`StateSpaceCompiler` (`py/cogant/statespace/compiler.py`)
consumes the rule output, projects it onto the hidden-state set, and
hands the result to the GNN matrix builder.

## Known Limitations

1. **A matrix sparsity**: heuristic `0.9 / 0.1` diagonal vs off-diagonal
   fill - no learned parameters yet.
2. **B matrix identity fallback**: when an `ACTION` has no `WRITES`
   edge, B is identity-filled along the current state.
3. **Uniform C**: when no `CONSTRAINT` mappings exist the preference
   vector is uniform.
4. **Uniform D**: when no `CONFIGURATION` nodes or type domains are
   found the prior is uniform.
5. **Keyword sensitivity**: English keyword lists in the rule classes
   bias recognition toward well-named idiomatic Python. Obfuscated or
   non-English identifiers fall back to purely structural evidence
   (edge degree, containment, inheritance).
6. **Conflict resolution is priority+confidence, not semantic**: when
   two rules overlap, the engine keeps the higher-priority mapping or
   the higher-confidence one as a tiebreaker. Semantic merging (e.g.
   "this class is both policy and hidden state") is not yet performed.

## Validation Results (2026-04-09)

### Semantic mapping counts per control-positive fixture

| Fixture | Total mappings | Hidden state | Observation | Action | Policy | Constraint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `calculator` | 6 | 1 | 3 | 1 | 0 | 1 |
| `event_pipeline` | 20 | 1 | 9 | 6 | 4 | 0 |
| `flask_mini` | 19 | 3 | 2 | 8 | 6 | 0 |

The calculator fixture shows the expected hidden-state / observation /
action / constraint split: the `Calculator` class becomes hidden state,
`get_display` / `get_history` / `assert_display` become observations,
`_execute_operation` becomes an action, and `assert_history_length`
becomes a constraint (preference).

The event-pipeline fixture concentrates policy on
`EventHandler`, `LoggingEventHandler`, `RetryableEventHandler`, and
`FilteringEventHandler` - all recognised via the
`handler`/`controller`/`manager` keyword set. Observations include
`get_logs`, `get_failed_events`, `get_event_history`, and the `publish`
/ `subscribe` methods of the bus.

The flask-mini fixture classifies `Middleware`, `LoggingMiddleware`,
`AuthMiddleware`, `Route`, `route`, and `match_route` as policy, and
promotes `Request`, `Response`, `Application` to hidden state because
they hold mutated attributes.

### Markov blanket partitioning (auto strategy)

| Fixture | Total nodes | Internal (mu) | Sensory (s) | Active (a) | External (eta) | Internal ratio | Boundary ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `calculator` | 12 | 10 | 1 | 0 | 1 | 0.833 | 0.083 |
| `event_pipeline` | 23 | 3 | 1 | 1 | 18 | 0.130 | 0.087 |
| `flask_mini` | 26 | 4 | 1 | 2 | 19 | 0.154 | 0.115 |

Calculator: the auto strategy seeds on the `calculator` module, pulling
ten methods inside as internal. The `Calculator` class itself becomes
the single sensory boundary node (it reads from outside its container
when the module contains-edge points at it), and the enclosing
`calculator` module is the only external neighbour - a clean minimal
blanket for a single-class fixture.

Event pipeline and flask_mini show the typical "core + boundary" split:
most nodes are external because the seed module only contains the
classes it owns, while a handful of boundary methods couple the
internal classes to the surrounding module.

### Qualitative validation test coverage

`tests/unit/test_ai_role_validation.py` contains 16 passing tests
covering:

- `ObservationRule` (pure getter, read-only function without keyword).
- `ActionRule` (setter with WRITES, process_* keyword without WRITES).
- `PolicyRule` (handler class).
- `ReadOnlyInputRule` (module with only READS edges).
- `MutatingSubsystemRule` (class with incoming WRITES).
- `RetryPatternRule` (retry_* function name).
- `PreferenceRule` (assert_* method).
- End-to-end calculator pipeline produces multiple role kinds,
  observation labels for `get_display` / `get_history`, at least one
  constraint from `assert_*`, a complete Markov blanket partition, and
  mutually-exclusive role sets.
- Parametrised cross-fixture check that `event_pipeline` and
  `flask_mini` produce both `POLICY` and `ACTION` mappings.

### Surprising findings

1. **The on-disk `semantic_mappings.json` emitted by
   `orchestrate_roundtrip.py` is lossy**: every mapping is written with
   `semantic_role: "unknown"` because the serialization helper does not
   read `SemanticMapping.kind`. The in-memory objects returned from
   `_apply_translation_rules` carry the correct kinds; only the JSON
   export is degraded. The validation tests therefore exercise the
   in-memory pipeline directly and bypass the broken exporter.
2. **Calculator never emits an `ACTION` mapping** even though
   `input_digit`, `input_operation`, and `equals` clearly mutate state.
   The reason is that `ActionRule` keyword-matches on
   `set/update/create/delete/send/push/execute/run/process/handle/dispatch`
   and none of those keywords appear in those method names. Only the
   private helper `_execute_operation` matches via `execute`. This is a
   real recall gap in `ActionRule` that should be addressed by
   adding an edge-based fallback: any method with 2+ `WRITES` edges
   targeting `self.*` attributes should become an action regardless of
   name.
3. **Class-level `POLICY` vs `HIDDEN_STATE` overlaps**: `MutatingSubsystemRule`
   sets `TranslationRule.priority` to `1` and `InheritanceRule` uses the
   default `0`, so the hidden-state mapping wins `(priority,
   confidence_score)` ordering in `TranslationEngine._resolve_conflicts`
   unless rescoring changes the tuple order. Older notes recorded the
   pre-priority-tuning case where `POLICY` could dominate; re-check
   fixture tables after changing either rule's score bands.
4. **Calculator's Markov blanket uses the *module* as the external
   node** even though the module `contains` the class. This is a
   byproduct of the auto-seed scoring: the `calculator` module's
   cohesion score is below the class cluster's score, so the class and
   its methods are chosen as the system of interest and the module
   becomes environment. It is a correct application of the scoring
   function but counter-intuitive - normally one would call the module
   "the system" and the class "inside". Worth documenting in the
   blanket extractor README.
