from cogant.schemas.core import EdgeKind as EdgeKind, Node as Node, NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.translate.dsl.schema import DSLCondition as DSLCondition, DSLRuleSet as DSLRuleSet
from dataclasses import dataclass

@dataclass
class CompiledRule:
    name: str
    role: str
    confidence: float
    description: str | None
    def match(self, node: Node, graph: ProgramGraph) -> float: ...

def compile_ruleset(ruleset: DSLRuleSet) -> list[CompiledRule]: ...
