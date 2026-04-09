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
