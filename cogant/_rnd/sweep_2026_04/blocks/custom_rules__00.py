from cogant.translate.engine import TranslationRule
from cogant.schemas.semantic import SemanticMapping, MappingKind, ConfidenceTier
from cogant.schemas.core import NodeKind
from cogant.graph.queries import GraphQuery
from cogant.schemas.graph import ProgramGraph

class MyCustomRule(TranslationRule):
    def matches(self, graph: ProgramGraph, query: GraphQuery):
        """Return list of match dicts for nodes matching this rule."""
        matches = []
        for node in graph.get_nodes_by_kind(NodeKind.FUNCTION):
            if "magic_" in node.name:
                matches.append({"node_id": node.id, "name": node.name})
        return matches

    def apply(self, match, graph: ProgramGraph, query: GraphQuery):
        """Apply rule and return SemanticMapping."""
        return SemanticMapping(
            source_id=match["node_id"],
            target_concept="special_function",
            kind=MappingKind.STRUCTURAL,
            confidence=ConfidenceTier.HIGH,
            provenance=None,
        )
