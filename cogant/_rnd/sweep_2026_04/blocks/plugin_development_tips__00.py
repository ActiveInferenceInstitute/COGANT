import pytest
from my_plugin import MyTranslationRule
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import ProgramGraph, GraphMetadata
from cogant.graph.queries import GraphQuery

def test_my_rule():
    rule = MyTranslationRule()
    
    node = Node(id="fn_special", name="special_function", kind=NodeKind.FUNCTION)
    graph = ProgramGraph(nodes=[node], edges=[], metadata=GraphMetadata())
    query = GraphQuery(graph)
    
    matches = rule.matches(graph, query)
    assert len(matches) == 1
    mapping = rule.apply(matches[0], graph, query)
    assert mapping.target_concept == "special_function"
