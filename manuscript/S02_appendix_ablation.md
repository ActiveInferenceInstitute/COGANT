# Appendix B — Full Ablation Table {#sec:S02-appendix-ablation}

This appendix complements the rule-family ablation reported in @sec:09-ablation of
the main text (which uses `flask_app` and `calculator` as ablation targets)
by measuring the same analysis on `zoo/01_simple_state` — the
smallest non-trivial fixture in the evaluation set and the one used to
demonstrate the runnable active-inference cycle summarized in @sec:10-conclusion. Because
zoo/01 has a single hidden-state factor, a single observation modality, two
actions, and no POLICY/CONTEXT/CONSTRAINT nodes in the origin, the ablations
isolate each rule family's contribution to the minimal POMDP skeleton.

> **Status of this appendix (measured).** The rows below are now emitted by
> [`tools/regenerate_ablation.py`](../tools/regenerate_ablation.py), which
> includes `zoo/01_simple_state` in the live ablation harness and writes a
> per-`MappingKind` decomposition into `METRICS.yaml`. The table is no longer
> hand-reconstructed from rule assignments. The deltas still retain the engine's
> conflict-resolution semantics: when a node can be won by another retained
> family, removing one family may change the role mix without changing the net
> mapping count.

### B.1 Rule-family ablation on zoo/01\_simple\_state

**Baseline (all 5 families enabled).** The live harness records
**{{ABLATION_ZOO01_BASELINE}}** mappings for zoo/01:
**{{ABLATION_ZOO01_BASELINE_HIDDEN_STATE}}** HIDDEN\_STATE,
**{{ABLATION_ZOO01_BASELINE_OBSERVATION}}** OBSERVATION, and
**{{ABLATION_ZOO01_BASELINE_ACTION}}** ACTION mappings.

| Rule family removed | Net mapping Δ | Per-`MappingKind` signal | Interpretation |
|---------------------|--------------:|--------------------------|----------------|
| Structural | {{ABLATION_ZOO01_STRUCTURAL_DELTA}} | HIDDEN\_STATE Δ {{ABLATION_ZOO01_STRUCTURAL_HIDDEN_STATE_DELTA}}; POLICY Δ {{ABLATION_ZOO01_STRUCTURAL_POLICY_DELTA}} | The hidden-state producer is structural, but the conflict resolver re-covers the net count through a retained POLICY role, so the total delta is zero while the role mix changes. |
| Semantic | {{ABLATION_ZOO01_SEMANTIC_DELTA}} | OBSERVATION Δ {{ABLATION_ZOO01_SEMANTIC_OBSERVATION_DELTA}}; ACTION Δ {{ABLATION_ZOO01_SEMANTIC_ACTION_DELTA}} | The semantic family is the measured source of the observable/action half of the minimal POMDP skeleton. |
| Control | {{ABLATION_ZOO01_CONTROL_DELTA}} | No measured per-kind loss | No config/feature/parameter role survives conflict resolution on this fixture. |
| Behavioural | {{ABLATION_ZOO01_BEHAVIORAL_DELTA}} | No measured per-kind loss | No event-bus, assertion, orchestrator, or state-machine role is load-bearing in zoo/01. |
| Resilience | {{ABLATION_ZOO01_RESILIENCE_DELTA}} | No measured per-kind loss | The fixture contains no retry, boundary, singleton, circuit-breaker, or rate-limiter pattern. |

: Measured rule-family ablation on `zoo/01_simple_state`, including per-`MappingKind` deltas emitted by `tools/regenerate_ablation.py`. {#tbl:zoo01-rule-family-ablation}

**Interpretation.** On the minimal-POMDP fixture:

1. **Structural rules are load-bearing for HIDDEN\_STATE but not for net
   mapping count.** Removing the structural family drops the measured
   HIDDEN\_STATE contribution by {{ABLATION_ZOO01_STRUCTURAL_HIDDEN_STATE_DELTA}},
   while a retained role re-covers the total count. This is exactly why
   per-`MappingKind` decomposition matters: net totals alone would hide the
   role-mix change.

2. **Semantic rules provide the observation/action half of the POMDP.**
   The semantic-family ablation removes {{ABLATION_ZOO01_SEMANTIC_DELTA}}
   mappings in total: {{ABLATION_ZOO01_SEMANTIC_OBSERVATION_DELTA}}
   OBSERVATION and {{ABLATION_ZOO01_SEMANTIC_ACTION_DELTA}} ACTION mappings.

3. **Control, behavioural, and resilience families are inactive on zoo/01.**
   Their measured deltas are all zero, matching the absence of config,
   assertion/event, and resilience idioms in the fixture.

4. **Matrix fallbacks are fully active on the minimal fixture.** The same
   measured run records {{ABLATION_ZOO01_A_COLS_UNIFORM}} /
   {{ABLATION_ZOO01_A_COLS_TOTAL}} uniform A state-columns,
   {{ABLATION_ZOO01_B_ACTIONS_IDENTITY}} /
   {{ABLATION_ZOO01_B_ACTIONS_TOTAL}} identity B actions, and
   {{ABLATION_ZOO01_C_ENTRIES_ZERO}} /
   {{ABLATION_ZOO01_C_ENTRIES_TOTAL}} zero C entries. This confirms that
   the minimal POMDP is a structural smoke case, not an informative-matrix
   exemplar (cf. @sec:09-ablation, @tbl:matrix-fallback-ablation).

### B.2 Cross-reference with main-text rule-family ablation

The five rule families in the ablation above correspond to the five families
in @sec:09-ablation / @tbl:rule-family-ablation as follows:

| Supplement family  | Main-text family                    | Primary main-text rule(s)                                        |
|--------------------|-------------------------------------|------------------------------------------------------------------|
| StateSpaceRule     | Structural                          | `MutatingSubsystemRule`, `ReadOnlyInputRule`                     |
| ObservationRule    | Semantic                            | `ObservationRule`, `PolicyRule`, `ContextRule`                    |
| ActionRule         | Semantic                            | `ActionRule`, `OrchestratorRule`                                  |
| ConstraintRule     | Semantic + Behavioural              | `PreferenceRule`, `TestAssertionRule`                             |
| FallbackRule       | Matrix-fallback (@tbl:matrix-fallback-ablation) | `compute_A`, `compute_B`, `compute_C`, `compute_D` fallback paths |

The ablation in @sec:09-ablation is fixture-level (`flask_app`, `calculator`) and
reports mapping-count deltas; the ablation in @sec:S02-appendix-ablation is role-level
(HS, OBS, ACT, CNST, fallback) and reports `s_role` deltas on the
minimum-complexity fixture that still round-trips perfectly. The two
ablations are complementary: together they bracket the failure surface from
"largest real-world fixture" down to "smallest runnable POMDP".
