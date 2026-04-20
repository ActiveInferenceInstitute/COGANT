from cogant.translate.engine import TranslationRule
from cogant.schemas.semantic import SemanticMapping, MappingKind, ConfidenceTier
from cogant.schemas.core import NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.graph.queries import GraphQuery

class TestFunctionRule(TranslationRule):
    """Identifies test functions by naming convention."""
    
    def matches(self, graph: ProgramGraph, query: GraphQuery):
        matches = []
        for node in graph.get_nodes_by_kind(NodeKind.FUNCTION):
            if node.name.startswith("test_") or node.name.startswith("Test"):
                matches.append({"node_id": node.id, "name": node.name})
        return matches
    
    def apply(self, match, graph: ProgramGraph, query: GraphQuery):
        tier = ConfidenceTier.HIGH if match["name"].startswith("test_") else ConfidenceTier.MEDIUM
        return SemanticMapping(
            source_id=match["node_id"],
            target_concept="test_code",
            kind=MappingKind.STRUCTURAL,
            confidence=tier,
            provenance=None,
        )
