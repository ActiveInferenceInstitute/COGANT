# Active Inference Mapping (R&D)

This page mirrors the internal R&D document `_rnd/ACTIVE_INFERENCE_MAPPING.md` — the long-form justification for how COGANT maps software constructs to Active Inference roles, plus the 2026-04-09 validation data and the surprising findings that informed the current rule priorities.

The curated public version lives in [Theory — Active Inference mapping](../theory/active_inference.md). This page is kept for research transparency and to record the open questions the team is still working through.

## Overview

The mapping pipeline is intentionally *structural*: every role is assigned by inspecting the program graph (`NodeKind`, `EdgeKind`, name keywords, degree statistics). No language-specific heuristics beyond Python keyword scanning are required, which is what lets the same engine later cover Rust, TypeScript, and Lean targets.

## The four fundamental roles

Active Inference partitions an agent into four disjoint sets:

```
    internal (mu)  <---  sensory (s)  <---  external (eta)
                   --->  active  (a)  --->
```

### Hidden State (mu) — internal states

- **Mutable class attributes** — instance variables written by methods (e.g. `Calculator.display`, `Calculator.accumulator`, `Calculator.history`, `RetryableEventHandler.failed_events`).
- **Classes with WRITES edges** — caught by `MutatingSubsystemRule` in `py/cogant/translate/rules/structural.py`, which emits `HIDDEN_STATE` whenever a class has at least one incoming or outgoing `WRITES`/`MUTATES` edge.
- **State machines** — attributes + transition methods.
- **Caches, accumulators, buffers** — internal scratch space.

Rule: `MutatingSubsystemRule` → `MappingKind.HIDDEN_STATE`.

### Observation (s) — sensory states

- **Pure getter functions** — keywords `get | read | fetch | query | display | show | status | info | list`, or any function / method with `READS` edges and zero `WRITES`.
- **Logging handlers and monitors** — consume events but never mutate shared state.
- **Read-only modules** — entire modules whose only outbound edges are `READS`.
- **Event subscribers that don't modify state**.

Rules: `ObservationRule` (`semantic.py`) and `ReadOnlyInputRule` (`structural.py`) → `MappingKind.OBSERVATION`.

### Action (a) — active states

- **Setter / mutator methods** — keywords `set | update | create | delete | send | push | execute | run | process | handle | dispatch`, usually accompanied by `WRITES` edges.
- **Event publishers** — `EventBus.publish`, `dispatch`, etc.
- **Request handlers** — `handle_request`, `process_request`, `process_response`.

Rule: `ActionRule` (`semantic.py`) → `MappingKind.ACTION`.

### Policy (pi) — control under uncertainty

- **Handler / Controller / Manager / Router / Dispatcher / Scheduler classes** — anything matching the canonical control-plane vocabulary.
- **Retry, backoff, circuit-breaker, fallback, timeout patterns** — `RetryPatternRule`.
- **Functions with high out-degree** — orchestrators recognised by `OrchestratorRule` in `behavioral.py`.
- **Strategy / policy pattern implementors** — via inheritance (`InheritanceRule`).

Rules: `PolicyRule` (`semantic.py`), `RetryPatternRule` (`resilience.py`), and `InheritanceRule` (`structural.py`) → `MappingKind.POLICY`.

### Secondary roles

- `CONSTRAINT` — `assert_*`, `test_*`, `validate_*`, `Validator` / `Checker` classes (`PreferenceRule`, `TestAssertionRule`).
- `CONTEXT` — configuration, feature flags, singleton / global state (`ConfigRule`, `FeatureFlagRule`, `ContextRule`, `SingletonAccessRule`).
- `DATA_FLOW` — reader-writer pipelines whose read sources differ from their write targets (`DataPipelineRule`).
- `ERROR_HANDLING` — functions with `CATCHES` / `THROWS` edges (`ErrorBoundaryRule`).
- `CIRCUIT_BREAKER` — `GUARDS` edge + retry / fallback keywords (`CircuitBreakerRule`).
- `ORCHESTRATION` — high-fan-out controllers (`OrchestratorRule`).

## Markov blanket partitioning

`MarkovBlanketExtractor` (`py/cogant/markov/extractor.py`) offers five seed-selection strategies. The default `auto` strategy picks the module with the best cohesion / coupling ratio:

```
score(module) = internal_edges / (internal_edges + boundary_edges + 1)
```

Once a seed set `S` is chosen, the pure-function partitioner `partition_by_seeds` (`py/cogant/markov/blanket.py`) walks the undirected projection of the program graph:

1. A node `n` in `S` with no neighbour outside `S` is **internal** (mu).
2. A node `n` in `S` with external neighbours is **sensory** (only incoming edges) or **active** (any outgoing edge, bidirectional defaults to active).
3. A node `n` outside `S` is **external** (eta). Nodes adjacent to `S` are tagged with `neighbour` metadata.

## A / B / C / D matrix derivation

| Matrix | Shape | Source edges | Semantics |
| --- | --- | --- | --- |
| A (likelihood) | `[n_obs x n_states]` | `READS`, `OBSERVES` | `P(observation \| hidden_state)` |
| B (transition) | `[n_states x n_states x n_actions]` | `WRITES`, `MUTATES`, `CALLS` | `P(next_state \| current_state, action)` |
| C (preference) | `[n_obs]` | `CONSTRAINT` confidence scores | `log P(preferred observations)` |
| D (prior) | `[n_states]` | `CONFIGURATION` nodes + domain defaults | `P(initial hidden state)` |

## Known limitations

1. **A matrix sparsity** — heuristic `0.9 / 0.1` diagonal vs off-diagonal fill; no learned parameters yet.
2. **B matrix identity fallback** — when an `ACTION` has no `WRITES` edge, B is identity-filled along the current state.
3. **Uniform C** — when no `CONSTRAINT` mappings exist the preference vector is uniform.
4. **Uniform D** — when no `CONFIGURATION` nodes or type domains are found the prior is uniform.
5. **Keyword sensitivity** — English keyword lists bias recognition toward idiomatic Python.
6. **Conflict resolution is priority + confidence, not semantic**.

## Validation Results (2026-04-09)

### Semantic mapping counts per control-positive fixture

| Fixture | Total | Hidden state | Observation | Action | Policy | Constraint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `calculator` | 6 | 1 | 3 | 1 | 0 | 1 |
| `event_pipeline` | 20 | 1 | 9 | 6 | 4 | 0 |
| `flask_mini` | 19 | 3 | 2 | 8 | 6 | 0 |

### Markov blanket partitioning (auto strategy)

| Fixture | Total | Internal (mu) | Sensory (s) | Active (a) | External (eta) | Internal ratio | Boundary ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `calculator` | 12 | 10 | 1 | 0 | 1 | 0.833 | 0.083 |
| `event_pipeline` | 23 | 3 | 1 | 1 | 18 | 0.130 | 0.087 |
| `flask_mini` | 26 | 4 | 1 | 2 | 19 | 0.154 | 0.115 |

## Surprising findings

1. **The on-disk `semantic_mappings.json` emitted by `orchestrate_roundtrip.py` is lossy** — every mapping is written with `semantic_role: "unknown"` because the serialization helper does not read `SemanticMapping.kind`. The in-memory objects returned from `_apply_translation_rules` carry the correct kinds; only the JSON export is degraded. The validation tests therefore exercise the in-memory pipeline directly and bypass the broken exporter.
2. **Calculator never emits an `ACTION` mapping** even though `input_digit`, `input_operation`, and `equals` clearly mutate state — because `ActionRule` keyword-matches on `set/update/create/delete/send/push/execute/run/process/handle/dispatch` and none of those keywords appear in those method names. Only the private helper `_execute_operation` matches via `execute`. This is a real recall gap that should be addressed by adding an edge-based fallback: any method with 2+ `WRITES` edges targeting `self.*` attributes should become an action regardless of name.
3. **Conflict resolution silently drops `HIDDEN_STATE` mappings when `InheritanceRule` fires** — if a class inherits from a handler base it is relabelled `POLICY`, which then wins the overlap resolution against the `HIDDEN_STATE` emitted by `MutatingSubsystemRule`. This is why `EventHandler` subclasses never appear as hidden state in the event-pipeline fixture despite having `failed_events` lists. Worth a follow-up to emit both roles where it is semantically accurate.
4. **Calculator's Markov blanket uses the *module* as the external node** even though the module `contains` the class — a byproduct of the auto-seed scoring: the `calculator` module's cohesion score is below the class cluster's score, so the class and its methods are chosen as the system of interest and the module becomes environment. It is a correct application of the scoring function but counter-intuitive.
