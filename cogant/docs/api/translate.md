# `cogant.translate`

The `cogant.translate` package is the semantic-mapping engine: it takes the typed program graph produced by `cogant.graph`, applies a priority-ordered rule set, runs a bounded fixpoint loop, and emits a set of `SemanticMapping` records annotated with `MappingKind` (HIDDEN_STATE / OBSERVATION / ACTION / POLICY / CONSTRAINT / ...) and a confidence score.

## Package

::: cogant.translate

## Engine

The core orchestration: `TranslationEngine.run()` drives the fixpoint loop and the conflict-resolution pass; every rule exposes an `.explain()` method that returns a `RuleExplanation` (used by `cogant explain`).

::: cogant.translate.engine

## Confidence

Confidence scoring keeps rule decisions epistemic about the pipeline, not about code quality.

::: cogant.translate.confidence

## Review

Human-in-the-loop API for curating uncovered or low-confidence mappings.

::: cogant.translate.review

## Rules

Rule classes are split by theme and priority:

### Structural rules

::: cogant.translate.rules.structural

### Semantic rules

::: cogant.translate.rules.semantic

### Behavioral rules

::: cogant.translate.rules.behavioral

### Control-flow rules

::: cogant.translate.rules.control

### Resilience rules

::: cogant.translate.rules.resilience

## Examples

`TranslationEngine`, the confidence scorer, the review API, and every rule family above are exercised by:

- **Zoo:** [`examples/zoo/01_simple_state/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/01_simple_state) — exercises `MutatingSubsystemRule` (structural; HIDDEN_STATE).
- **Zoo:** [`examples/zoo/02_observer/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/02_observer) — exercises `ObservationRule` (semantic).
- **Zoo:** [`examples/zoo/03_actor/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/03_actor) — exercises `ActionRule` (semantic).
- **Zoo:** [`examples/zoo/09_policy/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/09_policy) — exercises `PolicyRule` (semantic).
- **Zoo:** [`examples/zoo/10_constraint/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/10_constraint) — exercises `PreferenceRule` / constraint family.
- **Zoo:** [`examples/zoo/12_full_pomdp/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/12_full_pomdp) — fixpoint loop + conflict resolution under all five families simultaneously.
- **Cookbook:** [Recipe 3: Explain a single node](../cookbook/03_explain_node.md) — `RuleExplanation` from the `.explain()` API.
- **Cookbook:** [Recipe 19: Adding a custom translation rule](../cookbook/19_extend_rules.md) — registering a new `TranslationRule` against the engine.
- **Cookbook:** [Recipe: Custom translation rules](../cookbook/custom_translation_rules.md) — packaging-and-tests workflow for shipping rules.
- **Tutorial:** [Tutorial 4: Writing a custom translation rule](../tutorials/04_custom_rules.md) — full narrative on rule authorship and registration.
