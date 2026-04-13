# AGENTS.md — Rules module

COGANT's translation rules map program-graph patterns to Active Inference
roles. This module explains how the rule engine is structured, how it
resolves conflicts, how to author new rules, how to test them, and how to
debug rules that fail to fire.

## Purpose and ownership

Rules are the most customized extension point of COGANT: almost every
non-trivial adopter ends up writing or tuning a rule. The documentation
here has to stay accurate because third-party rule authors depend on it
for correctness. Owned by whoever is editing `py/cogant/translate/rules/`
or the rule engine core.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC and recommended reading order | When a file is added, removed, or renamed |
| `AGENTS.md` | This file — maintenance rules | When ownership or the update-with-code policy changes |
| `overview.md` | What a translation rule is and how the engine evaluates it | When the rule data model changes |
| `core_rules_summary.md` | The shipped baseline rule set | Whenever the baseline set gains, loses, or changes a rule |
| `configuration_and_precedence.md` | Rule loading, ordering, and precedence | When the loading or precedence policy changes |
| `rule_application.md` | How a rule is matched against a node and applied | When the matcher or application logic changes |
| `custom_rules.md` | Authoring your own translation rules | When the custom-rule API changes |
| `language_specific_variants.md` | Per-language overrides | When the override mechanism or per-language defaults change |
| `heuristic_rules.md` | Soft / heuristic rules and when to use them | When heuristic rule semantics change |
| `conflict_resolution.md` | What happens when two rules disagree | When the conflict resolution algorithm changes |
| `rule_set_management.md` | Versioning and distributing rule sets | When packaging or versioning conventions change |
| `performance.md` | Profiling and optimizing rule evaluation | When performance guidance changes or new profiling hooks land |
| `testing_rules.md` | Unit-testing custom rules | When the testing helpers or fixtures change |
| `debugging.md` | Diagnosing rules that fail to fire or fire incorrectly | When new debugging hooks or flags are added |
| `see_also.md` | Cross-links to related modules | When link targets move |

## Adding a new doc

1. Decide whether the new content is about authoring (`custom_rules.md`
   family), operation (`performance.md` / `debugging.md` family), or
   integration (`configuration_and_precedence.md` /
   `rule_set_management.md` family), and place it alongside its siblings.
2. Use a short, lower-case, underscore-separated slug.
3. Open with an example rule — the most effective documentation in this
   module is a compact, readable example followed by a short narration of
   what the engine does with it.
4. Add a row to the `## Contents` table in `README.md`.
5. If the new doc references a rule class or matcher API, link to the
   matching page in `../api/` instead of inlining signatures.

## Known gotchas

- `overview.md`, `rule_application.md`, and `custom_rules.md` all touch
  the same data model from different angles. When the data model changes,
  grep all three and update them in a single PR.
- `../cookbook/19_extend_rules.md` and `../cookbook/custom_translation_rules.md`
  are cookbook companions to `custom_rules.md`. Keep the cookbook focused on
  the "how" and `custom_rules.md` focused on the "what and why".
- The rule engine has performance-sensitive code paths. Any example in
  `performance.md` that cites timings must be reproducible with the
  command printed next to the number.
