# Active Inference mapping

This page records the theoretical justification for how COGANT maps software constructs to Active Inference roles and composes those roles into a Markov blanket and A/B/C/D generative-model matrices. The canonical source is [`../evaluation/ACTIVE_INFERENCE_MAPPING.md`](https://github.com/cogant-contributors/cogant/blob/main/docs/evaluation/ACTIVE_INFERENCE_MAPPING.md); the rule implementations live in `py/cogant/translate/rules/`.

The mapping pipeline is intentionally **structural**: every role is assigned by inspecting `NodeKind`, `EdgeKind`, name keywords, and degree statistics in the program graph. No language-specific heuristics beyond keyword scanning are required, which is what lets the same engine generalize from Python to Rust, TypeScript, and Lean.

## The four fundamental roles

Active Inference partitions an agent into four disjoint sets:

```text
    internal (mu)  <---  sensory (s)  <---  external (eta)
                   --->  active  (a)  --->
```

COGANT maps software constructs to these roles as follows.

### Hidden State (mu) — internal states

Code patterns that become `HIDDEN_STATE`:

- **Mutable class attributes** — instance variables written by methods (e.g. `Calculator.display`, `Calculator.accumulator`, `Calculator.history`, `RetryableEventHandler.failed_events`).
- **Classes with WRITES edges** — caught by `MutatingSubsystemRule` in `translate/rules/structural.py`, which emits `HIDDEN_STATE` whenever a class has at least one incoming or outgoing `WRITES` / `MUTATES` edge.
- **State machines** — attributes plus transition methods.
- **Caches, accumulators, buffers** — internal scratch space.

Rule: `MutatingSubsystemRule` → `MappingKind.HIDDEN_STATE`.

### Observation (s) — sensory states

Code patterns that become `OBSERVATION`:

- **Pure getters** — keywords `get | read | fetch | query | display | show | status | info | list`, or any function with `READS` edges and zero `WRITES`.
- **Logging handlers and monitors** — consume events but never mutate shared state.
- **Read-only modules** — entire modules whose only outbound edges are `READS`; picked up by `ReadOnlyInputRule`.
- **Event subscribers that don't modify state**.

Rules: `ObservationRule` and `ReadOnlyInputRule` → `MappingKind.OBSERVATION`.

### Action (a) — active states

Code patterns that become `ACTION`:

- **Setter / mutator methods** — keywords `set | update | create | delete | send | push | execute | run | process | handle | dispatch`, usually accompanied by `WRITES` edges.
- **Event publishers** — `EventBus.publish`, `dispatch`, etc.
- **Request handlers** — `handle_request`, `process_request`, `process_response`.

Rule: `ActionRule` → `MappingKind.ACTION`.

### Policy (pi) — control under uncertainty

Code patterns that become `POLICY`:

- **Handler / Controller / Manager / Router / Dispatcher / Scheduler classes** — anything matching the canonical control-plane vocabulary.
- **Retry, backoff, circuit-breaker, fallback, timeout patterns** — picked up by `RetryPatternRule`.
- **High-fan-out functions** — orchestrators recognized by `OrchestratorRule` in `behavioral.py`.
- **Strategy / policy pattern implementors** — via inheritance (`InheritanceRule`).

Rules: `PolicyRule`, `RetryPatternRule`, and `InheritanceRule` (when bases look like handlers/controllers) → `MappingKind.POLICY`.

### Secondary roles

Not part of the canonical Markov blanket but useful for GNN bundles and downstream analysis:

- `CONSTRAINT` — `assert_*`, `test_*`, `validate_*`, `Validator` / `Checker` classes (`PreferenceRule`, `TestAssertionRule`).
- `CONTEXT` — configuration, feature flags, singleton / global state (`ConfigRule`, `FeatureFlagRule`, `ContextRule`, `SingletonAccessRule`).
- `DATA_FLOW` — reader-writer pipelines whose read sources differ from their write targets (`DataPipelineRule`).
- `ERROR_HANDLING` — functions with `CATCHES` / `THROWS` edges (`ErrorBoundaryRule`).
- `CIRCUIT_BREAKER` — `GUARDS` edge plus retry / fallback keywords (`CircuitBreakerRule`).
- `ORCHESTRATION` — high-fan-out controllers (`OrchestratorRule`).

## Markov blanket partitioning

`MarkovBlanketExtractor` (`py/cogant/markov/extractor.py`) offers five seed-selection strategies. The default `auto` strategy picks the module with the best cohesion / coupling ratio:

```text
score(module) = internal_edges / (internal_edges + boundary_edges + 1)
```

Once a seed set `S` is chosen, `partition_by_seeds` (`py/cogant/markov/blanket.py`) walks the undirected projection of the program graph:

1. A node `n` in `S` with no neighbor outside `S` is **internal** (mu).
2. A node `n` in `S` with external neighbors is **sensory** (only incoming edges) or **active** (any outgoing edge; bidirectional defaults to active).
3. A node `n` outside `S` is **external** (eta). Nodes adjacent to `S` are tagged with `neighbour` metadata.

The partition is complete, mutually exclusive, and deterministic for a given graph and seed set.

## A / B / C / D matrix derivation

| Matrix | Shape | Source edges | Semantics |
| --- | --- | --- | --- |
| **A** (likelihood) | `[n_obs x n_states]` | `READS`, `OBSERVES` | `P(observation \| hidden_state)` |
| **B** (transition) | `[n_states x n_states x n_actions]` | `WRITES`, `MUTATES`, `CALLS` | `P(next_state \| current_state, action)` |
| **C** (preference) | `[n_obs]` | `CONSTRAINT` confidence scores | `log P(preferred observations)` |
| **D** (prior) | `[n_states]` | `CONFIGURATION` nodes + domain defaults | `P(initial hidden state)` |

`StateSpaceCompiler` (`py/cogant/statespace/compiler.py`) consumes the rule output, projects it onto the hidden-state set, and hands the result to the GNN matrix builder.

## Known limitations

1. **A matrix sparsity** — heuristic `0.9 / 0.1` diagonal vs off-diagonal fill; no learned parameters yet.
2. **B matrix identity fallback** — when an `ACTION` has no `WRITES` edge, B is identity-filled along the current state.
3. **Uniform C** — when no `CONSTRAINT` mappings exist the preference vector is uniform.
4. **Uniform D** — when no `CONFIGURATION` nodes or type domains are found the prior is uniform.
5. **Keyword sensitivity** — English keyword lists in the rule classes bias recognition toward well-named idiomatic Python. Obfuscated or non-English identifiers fall back to purely structural evidence (edge degree, containment, inheritance).
6. **Conflict resolution is priority + confidence, not semantic** — when two rules overlap, the engine keeps the higher-priority mapping or the higher-confidence one as a tiebreaker. Semantic merging ("this class is both policy and hidden state") is not yet performed.

## Validation snapshot

Semantic mapping counts from the control-positive fixtures (2026-04-09 run):

| Fixture | Total | Hidden | Observation | Action | Policy | Constraint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `calculator` | 6 | 1 | 3 | 1 | 0 | 1 |
| `event_pipeline` | 20 | 1 | 9 | 6 | 4 | 0 |
| `flask_mini` | 19 | 3 | 2 | 8 | 6 | 0 |

Markov blanket partitioning (auto strategy):

| Fixture | Nodes | Internal (mu) | Sensory (s) | Active (a) | External (eta) | Internal ratio | Boundary ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `calculator` | 12 | 10 | 1 | 0 | 1 | 0.833 | 0.083 |
| `event_pipeline` | 23 | 3 | 1 | 1 | 18 | 0.130 | 0.087 |
| `flask_mini` | 26 | 4 | 1 | 2 | 19 | 0.154 | 0.115 |

`tests/unit/test_ai_role_validation.py` ships 16 passing qualitative tests covering the individual rules and an end-to-end calculator check.

## Further reading

- [GNN format](gnn_format.md) — the bracket-notation export that consumes these matrices.
- [Active Inference mapping (R&D source)](../rnd/active_inference_mapping.md) — the full R&D document including surprising findings and follow-ups.
- [Calibration](../rnd/calibration.md) — confidence calibration notes.
