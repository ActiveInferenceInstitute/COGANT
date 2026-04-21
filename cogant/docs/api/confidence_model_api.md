## Confidence Model API

Mappings produced by the translation engine carry a `confidence` score in `[0.0, 1.0]` and a `tier` label that summarizes the evidence backing the score. Tiers are determined by combining the numeric threshold with the kinds of evidence available for the underlying nodes.

### Confidence Tiers

| Tier | Threshold | Evidence Required |
| --- | --- | --- |
| `HUMAN_REVIEWED` | `>= 0.9` | Human review decision (accept / edit via `ReviewAPI`) |
| `STATIC_PLUS_RUNTIME` | `>= 0.65` | Both static analysis and dynamic (coverage or trace) evidence |
| `STATIC_ONLY` | `>= 0.5` | Static analysis evidence only |
| `RUNTIME_ONLY` | `>= 0.4` | Dynamic evidence only (coverage or trace, no static match) |

### Tier Determination

A mapping's tier is the highest tier whose threshold is satisfied *and* whose evidence requirement is met. Mappings whose score falls below `0.4` or whose evidence does not match any tier are flagged for review and excluded from the curated bundle by default. Human-reviewed mappings always promote to `HUMAN_REVIEWED` regardless of the underlying numeric score, so accepting a mapping via `ReviewAPI.accept_mapping()` pins it at the highest tier.
