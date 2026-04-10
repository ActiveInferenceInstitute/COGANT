# Recipe 19: Adding a Custom Translation Rule

**Goal:** Extend COGANT's translation engine with a new rule.
**Time:** ~15 minutes.

## Prerequisites

- COGANT source code checked out
- Familiarity with the translation rule interface

## Steps

### 1. Understand the rule interface

Translation rules live in `cogant/py/cogant/translate/rules/`. Each
rule is a Python class that inspects a program-graph node and decides
whether to assign it a semantic role.

A rule must implement:

```python
class MyCustomRule:
    """One-line description shown in `cogant explain` output."""

    name: str = "my_custom_rule"
    priority: int = 50  # Lower fires first

    def evaluate(self, node, graph) -> RuleResult:
        """Return a RuleResult with role, confidence, and reason."""
        ...
```

### 2. Create the rule file

```bash
cat > cogant/py/cogant/translate/rules/my_custom_rule.py << 'EOF'
"""Custom rule: detect event-emitter classes as active states."""

from cogant.translate.rules.base import TranslationRule, RuleResult


class EventEmitterRule(TranslationRule):
    """Assign 'active state' (a) role to event-emitter classes."""

    name = "event_emitter"
    priority = 45  # Fire before generic class rules

    def evaluate(self, node, graph):
        # Check if the node is a class that emits events
        if node.kind != "class":
            return RuleResult.no_match()

        method_names = {m.name for m in node.methods}
        emitter_signals = {"emit", "dispatch", "publish", "notify"}

        if method_names & emitter_signals:
            return RuleResult(
                role="a",
                confidence=0.85,
                reason=f"Class has emitter methods: {method_names & emitter_signals}",
            )

        return RuleResult.no_match()
EOF
```

### 3. Register the rule

Add the rule to the plugin configuration in your pipeline config:

```yaml
pipeline:
  plugins:
    translate:
      extra_rules:
        - cogant.translate.rules.my_custom_rule.EventEmitterRule
```

### 4. Test the rule

```bash
cogant translate ./my-project \
  --config cogant-config.yaml \
  --output ./output-custom-rules \
  --no-dynamic
```

### 5. Verify with explain

```bash
cogant explain ./my-project MyEventEmitter --format json
```

Check that `event_emitter` appears in the `rules_fired` list.

### 6. Compare with and without the custom rule

```bash
cogant translate ./my-project --output ./output-default --no-dynamic
cogant diff ./output-default ./output-custom-rules
```

## Expected output

The `cogant explain` output shows the custom rule as FIRED with the
assigned role and confidence score.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Rule not firing | Check `priority` is low enough to fire before competing rules |
| Import error | Ensure the module path in `extra_rules` matches the file location |
| Confidence too low to appear | Lower the `confidence_threshold` in the pipeline config |
| Rule fires on wrong nodes | Add more specific guards in `evaluate` (check `node.kind`, method names, etc.) |
