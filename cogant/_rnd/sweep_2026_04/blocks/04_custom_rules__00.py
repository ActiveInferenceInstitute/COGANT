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
