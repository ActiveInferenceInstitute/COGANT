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
