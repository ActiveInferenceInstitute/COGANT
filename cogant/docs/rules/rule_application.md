## Rule Application

### Match & Apply

1. For each node in graph:
2. Find all matching rules (rules where `matches(node)` = true)
3. Sort by confidence (highest first)
4. Apply transformations
5. Update node with target role

### Confidence Adjustment

Base confidence modified by context:

```
final_confidence = base_confidence
                 + 0.1 (if explicit type annotation)
                 + 0.1 (if docstring/comment present)
                 + 0.05 (if consistent naming)
                 - 0.2 (if weak heuristic only)
                 - 0.15 (if type mismatch)
```

Result clamped to [0.0, 1.0].
