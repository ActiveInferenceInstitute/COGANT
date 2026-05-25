# Tutorial 4: Writing a custom translation rule

> **What this page is:** A hands-on tutorial for authoring, registering, and testing your own `TranslationRule` against the COGANT fixpoint engine.
>
> **Prerequisites:** [How COGANT assigns roles](../concepts/role_assignment.md) and Tutorials [1](01_quickstart.md)–[2](02_small_repo_walkthrough.md). Comfortable writing pytest tests.
>
> **Reading time:** ~25 minutes
>
> **Next steps:** [Tutorial 7: Authoring a language plugin](07_plugin_authoring.md) · [Plugin API reference](../api/plugin_api.md) · [Translation rules reference](../reference/translation_rules.md)

> **Goal.** Write and register a new `TranslationRule` that assigns an Active Inference role based on graph evidence. Ship it with tests.

> **Theory background:** A "translation rule" is the unit of work that turns program-graph
> evidence into an Active Inference role assignment. Before writing one, read:
>
> - [Translation rules reference](../reference/translation_rules.md) — the data model and
>   precedence semantics the engine enforces.
> - [Rules overview](../rules/overview.md) — the five rule families COGANT ships and where each
>   one fits.
> - [Custom rules guide](../rules/custom_rules.md) — registration, configuration, and packaging
>   conventions for third-party rules.

Translation rules are the pluggable units of COGANT's fixpoint engine. Each rule inspects the
program graph and, if its pattern matches, produces one or more `SemanticMapping`s. COGANT ships
with 22 rules across five families; this tutorial walks through how one of them
(`ObservationRule`) is structured so you can author a 20th in the same shape.

## 1. Pick the pattern

Suppose we want a rule that flags **read-only accessors** — functions/methods that `READ` but
never `WRITE` state — as `OBSERVATION` nodes. This is exactly the pattern that the shipped
`ObservationRule` already handles, via two triggers:

1. A lexical match on one of `OBSERVATION_KEYWORDS` (`get`, `read`, `fetch`, ...).
2. A structural fallback: `reads > 0 AND writes == 0`.

We'll walk through the real `ObservationRule` code as the teaching example. To write your own
rule, copy the same shape into a new class and change the patterns.

## 2. Inherit from `TranslationRule`

Rules live in `py/cogant/translate/rules/`. Pick a family file (`semantic.py`, `structural.py`,
`behavioral.py`, `control.py`, `resilience.py`) or create a new one. Here is the real
`ObservationRule` from `py/cogant/translate/rules/semantic.py`, condensed to show the shape:

```python
# py/cogant/translate/rules/semantic.py

from typing import Any

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.translate.engine import TranslationRule

OBSERVATION_KEYWORDS = [
    "get", "read", "fetch", "query", "display", "show", "status", "info", "list",
]


class ObservationRule(TranslationRule):
    """Maps getter/query functions and read-only methods to OBSERVATION.

    Fires when either:
      1. The node name contains an observation keyword, OR
      2. The node has READS edges and no WRITES edges (structural fallback).
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)
        for node in functions + methods:
            name_lower = node.name.lower()
            keyword_match = any(kw in name_lower for kw in OBSERVATION_KEYWORDS)

            out_edges = graph.get_edges_from(node.id)
            reads = sum(1 for e in out_edges if e.kind == EdgeKind.READS)
            writes = sum(1 for e in out_edges if e.kind == EdgeKind.WRITES)

            if keyword_match or (reads > 0 and writes == 0):
                matches.append({
                    "node_id": node.id,
                    "read_count": reads,
                    "write_count": writes,
                    "keyword_match": keyword_match,
                })
        return matches

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
        node_id = match["node_id"]
        node = graph.get_node(node_id)
        if not node:
            return None
        confidence = 0.85 if match["keyword_match"] else 0.7
        return SemanticMapping(
            id=f"obs_{node_id}",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Observation",
            confidence_score=confidence,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=confidence,
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,
        )

    @property
    def name(self) -> str:
        return "observation"

    @property
    def mapping_kind(self) -> MappingKind:
        return MappingKind.OBSERVATION
```

Three required methods (plus two `@property`s for rule metadata):

- `matches(graph, query)` — return a list of match dicts. Each dict becomes one mapping.
- `apply(graph, match)` — convert a match into a `SemanticMapping` instance (or `None`).
- `explain(node, graph, query)` — emit a `RuleExplanation` for the `cogant explain` CLI.
  Non-firing cases must return `fired=False` with a human-readable `reason`. See the full
  `ObservationRule.explain` in `semantic.py` for a complete implementation.

## 3. Register the rule

Rules are registered via `TranslationEngine.register_rule()`. COGANT's bootstrap code in
`py/cogant/translate/__init__.py` wires the default 22; add your new rule there. As an
example, here is how the shipped `ObservationRule` is wired:

```python
# doctest: +SKIP  # example requires runtime context or external resources
# py/cogant/translate/__init__.py

from cogant.translate.rules.semantic import (
    ObservationRule,
    ActionRule,
    PolicyRule,
    PreferenceRule,
    ContextRule,
    # MyNewRule,  # <-- your new rule would go here
)


def register_default_rules(engine: "TranslationEngine") -> None:
    engine.register_rule(ObservationRule())
    engine.register_rule(ActionRule())
    engine.register_rule(PolicyRule())
    engine.register_rule(PreferenceRule())
    engine.register_rule(ContextRule())
    # engine.register_rule(MyNewRule())  # <-- and register it
    # ... other families ...
```

## 4. Write the test first

COGANT is test-driven: every rule ships with at least one positive and one negative case. Below
is a minimal test pattern demonstrated against the real `ObservationRule` — this test actually
runs as part of the tutorial fixture suite, so you can copy the shape verbatim for your own
rule.

```python
# tests/unit/test_observation_rule_tutorial.py

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.translate.rules.semantic import ObservationRule


def _read_only_method_graph() -> ProgramGraph:
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="test://tutorial04"))
    cls = Node(
        id="n:Cache", kind=NodeKind.CLASS, name="Cache", qualified_name="Cache"
    )
    method = Node(
        id="n:get_value",
        kind=NodeKind.METHOD,
        name="get_value",
        qualified_name="Cache.get_value",
    )
    attr = Node(
        id="n:store",
        kind=NodeKind.VARIABLE,
        name="store",
        qualified_name="Cache.store",
    )
    graph.add_node(cls)
    graph.add_node(method)
    graph.add_node(attr)
    graph.add_edge(
        Edge(
            id="e:get_value->store",
            source_id=method.id,
            target_id=attr.id,
            kind=EdgeKind.READS,
        )
    )
    return graph


def test_observation_rule_fires_on_read_only_getter() -> None:
    graph = _read_only_method_graph()
    query = GraphQuery(graph)
    rule = ObservationRule()
    matches = rule.matches(graph, query)
    # get_value matches the keyword branch ("get") and/or the
    # structural branch (reads > 0, writes == 0)
    assert any(m["node_id"] == "n:get_value" for m in matches)

    match = next(m for m in matches if m["node_id"] == "n:get_value")
    mapping = rule.apply(graph, match)
    assert mapping is not None
    assert mapping.kind.name == "OBSERVATION"
```

Run the new test:

```bash
uv run pytest tests/unit/test_observation_rule_tutorial.py -v
```

## 5. Run against a real fixture

Once the test is green, run the full pipeline on a fixture that contains a read-only accessor
(e.g. a class with `get_*` methods that only read state) and confirm the mapping shows up:

```bash
uv run cogant translate examples/control_positive/my_cache_fixture \
    --output output/my_cache_fixture
uv run python -c "
import json
data = json.load(open('output/my_cache_fixture/bundle.json'))
for m in data['stages']['translate']['mappings']:
    if m['rule_id'] == 'observation':
        print(m)
"
```

## Gotchas

- **Priority ordering.** Conflicts are resolved by priority, then confidence. Pick a priority
  that reflects the rule's evidence strength. A structural, keyword-free pattern (like this
  one) should sit below keyword-based rules so the keyword signal wins the tie.
- **Determinism.** `matches` must return results in a deterministic order (iterate over
  `graph.nodes.values()`, which preserves insertion order in Python 3.7+).
- **Confidence provenance.** Record which evidence contributed to the score. The confidence
  tier is set by `ConfidenceModel` later in the pipeline; your job is to pick a base value
  that reflects how much you trust the pattern.
- **No side effects in `matches`.** The fixpoint engine calls `matches` repeatedly. It must be
  idempotent and must not mutate the graph.

## Next

- [Tutorial 5: reading GNN matrices](05_gnn_interpretation.md) — see how rule output flows
  into A / B / C / D.
- [`py/cogant/translate/rules/README.md`](https://github.com/docxology/cogant/blob/main/cogant/py/cogant/translate/rules/README.md) — the
  rule-family reference.
