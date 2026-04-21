"""Test demonstrating the tutorial 04 example against the real ObservationRule.

This test is the concrete, runnable version of the code block in
``docs/tutorials/04_custom_rules.md`` step 4. Keeping it in sync with the
tutorial ensures the documented read-only-accessor pattern actually fires
on a minimal handcrafted graph.
"""

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.translate.rules.semantic import ObservationRule


def _read_only_method_graph() -> ProgramGraph:
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="test://tutorial04"))
    cls = Node(id="n:Cache", kind=NodeKind.CLASS, name="Cache", qualified_name="Cache")
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
    # get_value matches the keyword branch ("get") AND the structural
    # branch (reads > 0, writes == 0) — this is exactly the pattern
    # the tutorial's "ReadOnlyCacheRule" was trying to express.
    assert any(m["node_id"] == "n:get_value" for m in matches)

    match = next(m for m in matches if m["node_id"] == "n:get_value")
    mapping = rule.apply(graph, match)
    assert mapping is not None
    assert mapping.kind.name == "OBSERVATION"
