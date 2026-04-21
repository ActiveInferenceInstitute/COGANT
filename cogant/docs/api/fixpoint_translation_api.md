## Fixpoint Translation API

The `TranslationEngine` drives rule-based translation from a `ProgramGraph` to GNN mappings using a fixpoint iteration loop. Rules are re-applied until no new mappings are produced (convergence) or `max_iterations` is reached, which allows later rules to observe mappings produced by earlier rules.

### Basic Usage

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant.translate.engine import TranslationEngine

engine = TranslationEngine(max_iterations=10)
engine.register_rule(my_rule)

# Run fixpoint iteration
mappings = engine.translate(graph)
```

Each registered rule inspects the current graph and any mappings produced by prior iterations, then emits its own mappings. The loop terminates as soon as a full pass produces zero new mappings.

### Translation with Confidence Rescoring

```python
# Apply confidence rescoring after translation converges
mappings = engine.translate_with_confidence(graph)
```

`translate_with_confidence()` runs the same fixpoint loop, then recomputes each mapping's confidence score by combining static and dynamic evidence attached to the underlying graph nodes (see the Confidence Model API below).

### Coverage Report

```python
report = engine.get_coverage_report(graph)
print(f"{report['coverage_percent']:.1f}% of nodes mapped")
# report also includes: mapped_nodes, unmapped_nodes, total_nodes
```

### Conflict Resolution

When multiple rules emit overlapping mappings for the same source fragment, the engine retains the mapping with the highest confidence score and discards the others. This ensures the final mapping set is consistent: every source fragment maps to at most one target, chosen by evidence strength rather than rule registration order.
