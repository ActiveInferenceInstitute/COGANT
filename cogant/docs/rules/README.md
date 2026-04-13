# Translation Rules

> COGANT's rule engine maps program-graph patterns to Active Inference roles. This section explains how rules are structured, how they are resolved when they conflict, how to author your own, and how to debug a rule that is not firing as expected.

## Contents

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | What a translation rule is and how the engine evaluates it | Beginner |
| [Configuration and Precedence](configuration_and_precedence.md) | Rule loading, ordering, and precedence policy | Intermediate |
| [Core Rules Summary](core_rules_summary.md) | The shipped baseline rule set | Beginner |
| [Rule Application](rule_application.md) | How a rule is matched against a node and applied | Intermediate |
| [Custom Rules](custom_rules.md) | Authoring your own translation rules | Intermediate |
| [Language-Specific Variants](language_specific_variants.md) | Per-language rule overrides | Intermediate |
| [Heuristic Rules](heuristic_rules.md) | Soft / heuristic rules and when to use them | Advanced |
| [Conflict Resolution](conflict_resolution.md) | What happens when two rules disagree | Advanced |
| [Rule Set Management](rule_set_management.md) | Versioning and distributing rule sets | Intermediate |
| [Performance](performance.md) | Profiling and optimizing rule evaluation | Advanced |
| [Testing Rules](testing_rules.md) | Unit-testing custom rules | Intermediate |
| [Debugging](debugging.md) | Diagnosing rules that fail to fire or fire incorrectly | Intermediate |
| [See Also](see_also.md) | Cross-links to related documentation | Beginner |

## Recommended Reading Order

1. [Overview](overview.md) — understand the rule data model.
2. [Core Rules Summary](core_rules_summary.md) — see what ships out of the box.
3. [Rule Application](rule_application.md) — learn the matcher's behavior.
4. [Custom Rules](custom_rules.md) — write your first rule.
5. [Testing Rules](testing_rules.md) — lock the new rule's behavior in.
6. [Configuration and Precedence](configuration_and_precedence.md) and [Conflict Resolution](conflict_resolution.md) — fit it into a real rule set.
7. [Language-Specific Variants](language_specific_variants.md), [Heuristic Rules](heuristic_rules.md) — handle edge cases.
8. [Performance](performance.md) and [Debugging](debugging.md) — operational concerns once your rule set grows.

## Related modules

- [../concepts/role_assignment.md](../concepts/role_assignment.md) — conceptual background for what rules do.
- [../plugins/README.md](../plugins/README.md) — shipping rule packs as plugins.
- [../reference/README.md](../reference/README.md) — canonical rule schema.
- [../cookbook/README.md](../cookbook/README.md) — short recipes for common rule-authoring tasks.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
