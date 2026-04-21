## Testing Rules

### Unit Test Template

```python
# doctest: +SKIP  # example requires runtime context or external resources
import pytest
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import ProgramGraph, GraphMetadata
from cogant.graph.queries import GraphQuery
from rules.my_rules import MyCustomRule

def _make_graph_with_node(name: str) -> ProgramGraph:
    """Helper to build a minimal ProgramGraph with one function node."""
    node = Node(id=f"fn_{name}", name=name, kind=NodeKind.FUNCTION)
    return ProgramGraph(nodes=[node], edges=[], metadata=GraphMetadata())

def test_my_custom_rule_matches():
    rule = MyCustomRule()
    graph = _make_graph_with_node("magic_function")
    query = GraphQuery(graph)
    matches = rule.matches(graph, query)
    assert len(matches) == 1

def test_my_custom_rule_apply():
    rule = MyCustomRule()
    graph = _make_graph_with_node("magic_function")
    query = GraphQuery(graph)
    matches = rule.matches(graph, query)
    mapping = rule.apply(matches[0], graph, query)
    assert mapping.target_concept == "special_function"

def test_my_custom_rule_no_match():
    rule = MyCustomRule()
    graph = _make_graph_with_node("normal_function")
    query = GraphQuery(graph)
    matches = rule.matches(graph, query)
    assert len(matches) == 0
```
