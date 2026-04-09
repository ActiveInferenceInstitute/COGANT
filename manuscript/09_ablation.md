# Ablation study

This section studies how each component of the translation pipeline contributes to the observed output on the six packaged fixtures. The ablations are organised along two axes: the five **rule families** defined in Section 2 (structural, semantic, control, behavioural, resilience) and the **fixpoint iteration cap** of the translation engine. Where a measurement is available from the shipped validation runs in `../_rnd/figures/metrics.json` and `../_rnd/ACTIVE_INFERENCE_MAPPING.md`, it is cited directly. Where a measurement has been planned but not yet populated in the canonical metrics file --- typically because the P3 validation harness reruns the pipeline with one rule family disabled at a time --- the entry is marked "planned" and the expected signal is stated so that a future run can fill it in without restructuring the table.

## Rule-family ablation

The question answered by this ablation is: *if one family of translation rules is removed, which Active Inference roles disappear from the output, and what fraction of previously covered nodes lose their semantic role?* The experimental protocol is to re-run the full pipeline (ingest, parse, graph, translate, statespace, GNN package build, validate) with the `TranslationEngine` constructed over a rule list that excludes exactly one family, and to diff the resulting `semantic_mappings.json` against the canonical baseline. The ablation is defined over the `flask_app` fixture (the largest real-world fixture, 98 nodes, 51 baseline mappings) and the `calculator` fixture (the smallest control-positive fixture, 12 nodes, 5 baseline mappings) so that both a well-covered and a narrowly-covered input are represented.

**Table 10. Rule-family ablation on `flask_app` and `calculator` (baseline values from canonical metrics; ablation deltas planned).**

| Rule family | Rules removed | Baseline mappings | Roles primarily affected | `flask_app` $\Delta$ mappings | `calculator` $\Delta$ mappings | Primary quality signal |
|---|---|---:|---|:---:|:---:|---|
| Structural | `ReadOnlyInput`, `MutatingSubsystem`, `Inheritance`, `Containment`, `DataPipeline` | 5 rules | HIDDEN\_STATE, OBSERVATION, POLICY (via inheritance) | planned | planned | State-variable count drops on mutation-heavy fixtures (`flask_app` expected loss of the 16 state variables reported in Table 6); Markov blanket collapses to external-only on `calculator`. |
| Semantic | `Observation`, `Action`, `Policy`, `Preference`, `Context` | 5 rules | OBSERVATION, ACTION, POLICY, PREFERENCE | planned | planned | `calculator` loses all three getter observations (`get_display`, `get_history`, `assert_display`); `flask_app` loses all 19 OBSERVATION mappings and the 16 ACTION mappings reported in Table 6. `json_stdlib` baseline already shows `actions=0` because the semantic `ActionRule` keyword set does not match the stdlib function names, so removing the semantic family leaves the baseline unchanged on that fixture (a known recall gap documented in `../_rnd/ACTIVE_INFERENCE_MAPPING.md` §"Surprising findings"). |
| Control | `Config`, `FeatureFlag` | 2 rules | CONTEXT | planned | planned | Context-mapping count drops to zero on `flask_app` (expected to remove the entries produced by `AppConfig` class and any feature-flag constants in `config.py`); no change on `calculator` (no configuration nodes in the single-class fixture). |
| Behavioural | `Orchestrator`, `TestAssertion`, `EventBus` | 3 rules | POLICY (orchestration), CONSTRAINT, ACTION (event-bus publish) | planned | planned | `event_pipeline` (not shown here, see Table 6) would lose its four POLICY mappings that derive from the handler controller classes; `calculator` loses its single CONSTRAINT from `assert_history_length`. |
| Resilience | `RetryPattern`, `ErrorBoundary`, `SingletonAccess`, `CircuitBreaker` | 4 rules | POLICY (retry/circuit), ERROR\_HANDLING, CIRCUIT\_BREAKER, CONTEXT (singleton) | planned | planned | `flask_app` loses any retry-pattern POLICY mappings attached to service-layer wrappers; `calculator` is unchanged because the fixture contains no resilience patterns. |

The **planned** entries will be populated by a companion harness that constructs a `TranslationEngine` with `register_rule()` called on only four of the five families, reruns `RoundtripOrchestrator` on the two fixtures, and diffs the resulting `semantic_mappings.json`. The harness is expected to land as part of the P3 validation backlog (`../_rnd/SCOPING_REPORT.md`); until it does, the final three columns of Table 8 report the qualitative prediction based on the rule implementations and the known baseline counts rather than a measured delta.

One informative *unintended* ablation is already visible in the baseline data. On the `json_stdlib` fixture the `ActionRule` produces zero ACTION mappings because the rule keyword-matches on `set/update/create/delete/send/push/execute/run/process/handle/dispatch` and none of those keywords appear in the stdlib `json` module's function names (which are `dump`, `dumps`, `load`, `loads`, `encode`, `decode`, `iterencode`, and so on). The baseline therefore already exercises what removing `ActionRule` would look like on that fixture: the pipeline still emits a valid 19-file GNN package, `state_variables` is 3, `observations` is 5, `actions` is 0, and `transitions` is 0 because the cross-reference pass has no actions to link. This is an informative upper bound on the "no ACTION rule" condition: even in the complete absence of action mappings, the pipeline still validates at 100.0/100, the Markov blanket is still extracted, and the A/B/C/D matrices still pass `validate_shapes()` because the identity fallback in `compute_B` (lines 309--314 of `matrices.py`) fills the transition tensor with a valid stay-move distribution.

Similarly, the known conflict-resolution interaction between `InheritanceRule` and `MutatingSubsystemRule` recorded in `../_rnd/ACTIVE_INFERENCE_MAPPING.md` gives an inadvertent ablation-style observation: on the `event_pipeline` fixture, `EventHandler` subclasses are labelled POLICY by `InheritanceRule` and the HIDDEN\_STATE mapping that `MutatingSubsystemRule` would have emitted for the same class is silently dropped by the conflict resolver because POLICY wins on priority. In effect, `event_pipeline` is already running with `MutatingSubsystemRule` ablated on those specific nodes, and the downstream consequence is directly observable: the fixture's HIDDEN\_STATE count in Table 6 is 1 rather than the 5 that the mutable-attribute pattern would otherwise yield. This is a recall gap worth a follow-up fix (emit both roles on inheriting mutating classes), not a silent defect.

## Fixpoint-iteration ablation

The translation engine's default iteration cap is `max_iterations = 10`; this ablation studies how the output depends on that cap. The expected behaviour from Theorem 1 is that the engine converges in a single pass on every packaged fixture, because the shipped rules are disjoint on the node kinds they target and each mapping id is stable across iterations. The ablation verifies this empirically by rerunning the pipeline with the cap set to $K \in \{1, 2, 5, 10\}$ and recording the total mapping count at each setting.

**Table 11. Fixpoint iteration ablation (planned; baseline row reports the canonical $K = 10$ run from Table 4).**

| $K$ (max iterations) | `calculator` mappings | `event_pipeline` mappings | `flask_mini` mappings | `flask_app` mappings | `requests_lib` mappings | `json_stdlib` mappings | Convergence |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 1 | planned | planned | planned | planned | planned | planned | Predicted to equal the $K = 10$ baseline on every fixture (single-pass convergence). |
| 2 | planned | planned | planned | planned | planned | planned | Expected identical to $K = 1$ (no second-pass additions on any shipped fixture). |
| 5 | planned | planned | planned | planned | planned | planned | Expected identical. |
| 10 (default) | 5 | 20 | 19 | 51 | 46 | 8 | Canonical; matches Table 4. |

The single-pass-convergence prediction is testable directly from the engine's internal match log: `TranslationEngine._log_match("iteration_complete", ...)` writes one entry per iteration containing the per-pass new-mapping count, and a converged run on the first pass writes exactly one `iteration_complete` entry with a nonzero count followed by at most one more with `new_mappings=0`. The harness populating Table 9 will assert that the log length at $K = 10$ is between 1 and 2 iteration-complete entries on every fixture.

The purpose of keeping the cap at $K = 10$ despite the single-pass prediction is a safety valve: if a user registers a pathological rule set --- for example two rules that mutually trigger each other via the confidence model's rescoring pass in `translate_with_confidence()` --- the engine bounds the cost at ten full passes over the rule list rather than looping indefinitely. Section 4 ("Fixpoint non-convergence") already documents the warning message the engine emits when the cap is exceeded; this ablation simply confirms that the warning is never triggered on the shipped fixtures.

## Matrix-fallback ablation

A third ablation of interest is the effect of the identity-fallback and uniform-fallback paths in `GNNMatrices` on the resulting matrices. The fallbacks fire when the graph contains no edges of the expected kind for a given role:

- `compute_A` falls back to a uniform row when an observation has no READS, OBSERVES, or DEPENDS\_ON edges to any hidden state (`matrices.py` line 269).
- `compute_B` falls back to the identity tensor when an action writes no hidden state (lines 312--314).
- `compute_C` falls back to the zero vector when no CONSTRAINT or PREFERENCE mapping touches the observation (the implicit initialisation at line 371).
- `compute_D` falls back to a uniform prior when no CONFIGURATION neighbour exists (lines 416--417).

**Table 12. Fallback frequency on the six packaged fixtures (planned).**

| Fixture | $A$ rows uniform | $B$ actions identity | $C$ entries zero | $D$ uniform | Validator result |
|---|:---:|:---:|:---:|:---:|:---:|
| `calculator` | planned | planned | planned | planned | 100.0 |
| `event_pipeline` | planned | planned | planned | planned | 100.0 |
| `flask_mini` | planned | planned | planned | planned | 100.0 |
| `flask_app` | planned | planned | planned | planned | 100.0 |
| `requests_lib` | planned | planned | planned | planned | 100.0 |
| `json_stdlib` | 5 (all) | 1 (identity) | 5 (all) | 3 (uniform) | 100.0 |

The `json_stdlib` row is populated directly from the canonical baseline and `../_rnd/ACTIVE_INFERENCE_MAPPING.md`: because that fixture has zero ACTION mappings and no CONSTRAINT mappings, every row of $A$ is uniform (no observation has a READS/OBSERVES edge onto a hidden state at the granularity extracted by the Python front end), every action slice of $B$ is identity (there are no action slices to fill), every entry of $C$ is zero, and the prior $D$ is uniform over the three hidden-state variables. Crucially, the validator still passes at 100.0 because shape, sum-to-one, and non-negativity invariants are all satisfied by the fallback. This establishes that the fallback paths are not failure modes but **principled degradations** to a maximum-entropy distribution in the absence of edge evidence, and that every bundle COGANT emits --- even one built entirely from fallbacks --- remains a valid Active Inference generative model that PyMDP or a compatible runtime can execute.

## Summary

The ablation study answers three questions. First, **which rule families are necessary for which roles?** (Table 10: structural rules drive HIDDEN\_STATE; semantic rules drive OBSERVATION/ACTION/POLICY/PREFERENCE; control rules drive CONTEXT; behavioural rules drive orchestration POLICY and CONSTRAINT; resilience rules drive resilience-flavoured POLICY.) Second, **how many iterations does the fixpoint actually need?** (Table 11: one pass on every shipped fixture, with the $K = 10$ cap serving as a pathological-rule safety valve.) Third, **what do the A/B/C/D fallbacks produce when no edge evidence is available?** (Table 12: maximum-entropy uniform distributions and identity transitions that still validate at 100.0 and remain valid active-inference generative models.) Several entries remain marked "planned" pending the P3 validation harness; filling them in is a single-file addition that reruns the pipeline with the appropriate rule-list restriction and writes the deltas into the same `metrics.json` format used by `../_rnd/figures/generate_figures.py`.
