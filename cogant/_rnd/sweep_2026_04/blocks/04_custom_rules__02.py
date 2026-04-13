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
