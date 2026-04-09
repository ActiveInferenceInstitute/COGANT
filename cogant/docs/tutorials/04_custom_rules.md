# Tutorial 4: Writing a custom translation rule

> **Goal.** Write and register a new `TranslationRule` that assigns an Active Inference role based on graph evidence. Ship it with tests.

Translation rules are the pluggable units of COGANT's fixpoint engine. Each rule inspects the
program graph and, if its pattern matches, produces one or more `SemanticMapping`s. COGANT ships
with 19 rules across five families; this tutorial walks through writing a 20th.

## 1. Pick the pattern

Suppose we want to flag **cache-like classes** — classes that only `READ` and never `WRITE` to
their own attributes — as `OBSERVATION` nodes with a distinctive provenance tag. This pattern
is not currently covered by `ObservationRule` (which operates on method nodes, not classes).

## 2. Inherit from `TranslationRule`

Rules live in `py/cogant/translate/rules/`. Pick a family file (`semantic.py`, `structural.py`,
`behavioral.py`, `control.py`, `resilience.py`) or create a new one.

```python
# py/cogant/translate/rules/semantic.py  (or a new file)

from typing import Any, Dict, List

from cogant.schemas.core import NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import SemanticMapping, MappingKind, ConfidenceTier
from cogant.graph.queries import GraphQuery
from cogant.translate.engine import TranslationRule, RuleExplanation


class ReadOnlyCacheRule(TranslationRule):
    """Tag classes whose methods only READ attributes as OBSERVATION nodes.

    The rule fires when:

    1. Node kind is CLASS.
    2. The class has at least one method with READS edges to class attrs.
    3. The class has zero WRITES edges from any of its methods.

    Rationale: caches and read-through views expose hidden state to the
    rest of the program without mutating it, which is exactly the
    OBSERVATION role in the Active Inference mapping.
    """

    name = "ReadOnlyCacheRule"
    priority = 55  # lower than PolicyRule (80) and MutatingSubsystemRule (80)

    def matches(
        self, graph: ProgramGraph, query: GraphQuery
    ) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        for node in graph.nodes.values():
            if node.kind != NodeKind.CLASS:
                continue

            methods = query.contained_nodes(node.id, kind=NodeKind.METHOD)
            if not methods:
                continue

            reads_count = 0
            writes_count = 0
            for method in methods:
                reads_count += len(
                    query.outgoing_edges(method.id, kind=EdgeKind.READS)
                )
                writes_count += len(
                    query.outgoing_edges(method.id, kind=EdgeKind.WRITES)
                )

            if writes_count == 0 and reads_count >= 1:
                matches.append({
                    "class_id": node.id,
                    "reads": reads_count,
                })
        return matches

    def apply(
        self, graph: ProgramGraph, match: Dict[str, Any]
    ) -> SemanticMapping:
        return SemanticMapping(
            id=f"rocache:{match['class_id']}",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[match["class_id"]],
            confidence=0.72,
            confidence_tier=ConfidenceTier.MEDIUM,
            rule_id=self.name,
            provenance="ReadOnlyCacheRule",
            metadata={"reads": match["reads"], "writes": 0},
        )

    def explain(
        self, graph: ProgramGraph, query: GraphQuery, node_id: str
    ) -> RuleExplanation:
        node = graph.nodes.get(node_id)
        if node is None or node.kind != NodeKind.CLASS:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"node {node_id!r} is not a CLASS",
            )
        # ... collect evidence the same way as matches() and return
        # a populated RuleExplanation.
        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=True,
            reason="class has reads but no writes",
            evidence=[f"READS={...}", f"WRITES=0"],
            mapping_kind=MappingKind.OBSERVATION.value,
        )
```

Three required methods:

- `matches(graph, query)` — return a list of match dicts. Each dict becomes one mapping.
- `apply(graph, match)` — convert a match into a `SemanticMapping` instance.
- `explain(graph, query, node_id)` — emit a `RuleExplanation` for the rule-explainer CLI
  surface. Non-firing cases must return `fired=False` with a human-readable `reason`.

## 3. Register the rule

Rules are registered via `TranslationEngine.register_rule()`. COGANT's bootstrap code in
`py/cogant/translate/__init__.py` wires the default 19; add yours there:

```python
# py/cogant/translate/__init__.py

from cogant.translate.rules.semantic import (
    ObservationRule,
    ActionRule,
    PolicyRule,
    PreferenceRule,
    ContextRule,
    ReadOnlyCacheRule,  # <-- add the import
)


def register_default_rules(engine: "TranslationEngine") -> None:
    engine.register_rule(ObservationRule())
    engine.register_rule(ActionRule())
    engine.register_rule(PolicyRule())
    engine.register_rule(PreferenceRule())
    engine.register_rule(ContextRule())
    engine.register_rule(ReadOnlyCacheRule())  # <-- and register it
    # ... other families ...
```

## 4. Write the test first

COGANT is test-driven: every rule ships with at least one positive and one negative case. A
minimal test pattern (pattern borrowed from `tests/unit/test_ai_role_validation.py`):

```python
# tests/unit/test_read_only_cache_rule.py

from cogant.schemas.core import Node, NodeKind, Edge, EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.graph.queries import GraphQuery
from cogant.translate.rules.semantic import ReadOnlyCacheRule


def _cache_graph() -> ProgramGraph:
    graph = ProgramGraph()
    cls = Node(id="n:CacheClass", kind=NodeKind.CLASS, name="Cache")
    method = Node(id="n:get", kind=NodeKind.METHOD, name="get")
    attr = Node(id="n:store", kind=NodeKind.VARIABLE, name="store")
    graph.add_node(cls)
    graph.add_node(method)
    graph.add_node(attr)
    graph.add_edge(Edge(source_id=cls.id, target_id=method.id,
                         kind=EdgeKind.CONTAINS))
    graph.add_edge(Edge(source_id=method.id, target_id=attr.id,
                         kind=EdgeKind.READS))
    return graph


def test_rule_fires_on_read_only_cache() -> None:
    graph = _cache_graph()
    query = GraphQuery(graph)
    rule = ReadOnlyCacheRule()
    matches = rule.matches(graph, query)
    assert len(matches) == 1
    assert matches[0]["class_id"] == "n:CacheClass"

    mapping = rule.apply(graph, matches[0])
    assert mapping.kind.name == "OBSERVATION"
    assert mapping.confidence == 0.72


def test_rule_ignores_class_with_writes() -> None:
    graph = _cache_graph()
    method = next(n for n in graph.nodes.values() if n.name == "get")
    attr = next(n for n in graph.nodes.values() if n.name == "store")
    graph.add_edge(Edge(source_id=method.id, target_id=attr.id,
                         kind=EdgeKind.WRITES))
    matches = ReadOnlyCacheRule().matches(graph, GraphQuery(graph))
    assert matches == []
```

Run the new test:

```bash
uv run pytest tests/unit/test_read_only_cache_rule.py -v
```

## 5. Run against a real fixture

Once the test is green, run the full pipeline on a fixture that contains a cache class (or add
one to `examples/control_positive/`) and confirm the new mapping shows up:

```bash
uv run cogant translate examples/control_positive/my_cache_fixture \
    --output output/my_cache_fixture
uv run python -c "
import json
data = json.load(open('output/my_cache_fixture/bundle.json'))
for m in data['stages']['translate']['mappings']:
    if m['rule_id'] == 'ReadOnlyCacheRule':
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
- [`py/cogant/translate/rules/README.md`](../../py/cogant/translate/rules/README.md) — the
  rule-family reference.
