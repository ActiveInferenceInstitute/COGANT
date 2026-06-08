# Recipe: Custom Translation Rules

**Goal:** Write, register, test, and ship a new `TranslationRule` so the
fixpoint engine emits your role assignment alongside the 22 built-in rules.

> This is the short, copy-pasteable recipe. For the rationale, the
> precedence rules, and a fully-explained example (the read-only-cache
> rule) see [Tutorial 4: Writing a custom translation rule](../tutorials/04_custom_rules.md).

## When to write a rule vs. configure an existing one

- **Configure existing** — if you only need to retune confidence tiers or
  keyword patterns, prefer the configuration knobs documented in the
  [translate API page](../api/translate.md). Don't fork.
- **New rule** — if you need a new graph pattern that none of the
  five families (structural / semantic / behavioral / control / resilience)
  matches, write a `TranslationRule` subclass.

## Step 1 — pick a family and a priority

Rules live in `py/cogant/translate/rules/{family}.py`. Lower priority numbers
fire later — the conflict-resolution pass uses priority + confidence to break
ties. Pick a slot that does not collide with the built-ins (see
`py/cogant/translate/rules/__init__.py` for the registered priorities).

## Step 2 — subclass `TranslationRule`

```python
from cogant.schemas.core import NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import SemanticMapping, MappingKind, ConfidenceTier
from cogant.graph.queries import GraphQuery
from cogant.translate.engine import TranslationRule, RuleExplanation


class MyRule(TranslationRule):
    name = "MyRule"
    priority = 55  # see step 1

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> bool:
        # Cheap pre-filter — return False fast.
        return any(n.kind is NodeKind.CLASS for n in graph.nodes)

    def apply(self, graph: ProgramGraph, query: GraphQuery) -> list[SemanticMapping]:
        mappings: list[SemanticMapping] = []
        # … emit SemanticMapping(kind=MappingKind.OBSERVATION, …) …
        return mappings

    def explain(self, mapping: SemanticMapping) -> RuleExplanation:
        return RuleExplanation(
            rule_name=self.name,
            evidence=[...],
            confidence_reason="...",
        )
```

## Step 3 — register

Add the class to the family's `__all__` list and to the rule registry in
`py/cogant/translate/rules/__init__.py`. The engine auto-discovers
registered rules at startup.

## Step 4 — test (no mocks)

Drop a real fixture into `tests/fixtures/` (or under `examples/zoo/` if it's
useful as a public example) and write a real-data assertion:

```python
from pathlib import Path
from cogant import Session

def test_my_rule_fires_on_fixture():
    session = Session.from_target(Path("tests/fixtures/my_rule_target"))
    session.extract_static()
    session.build_graph()
    session.translate_to_gnn()
    mappings = session.semantic_mappings()
    assert any(m.rule_name == "MyRule" for m in mappings)
```

## Step 5 — ship

If the rule is project-internal: commit it under `py/cogant/translate/rules/`.
If you want to ship it as a third-party package, expose it via the plugin
entry point documented in [`plugin_api.md`](../api/plugin_api.md).

## See also

- [Tutorial 4: Writing a custom translation rule](../tutorials/04_custom_rules.md) — full read-only-cache walkthrough.
- [`docs/api/translate.md`](../api/translate.md) — every public symbol your rule will touch.
- [Recipe 19: Adding a custom translation rule](19_extend_rules.md) — the numbered custom-rule recipe.
- [Recipe 3: Explain a single node](03_explain_node.md) — using `RuleExplanation` from the CLI.
