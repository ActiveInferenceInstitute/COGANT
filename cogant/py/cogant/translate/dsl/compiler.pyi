from dataclasses import dataclass

from cogant.schemas.core import EdgeKind as EdgeKind
from cogant.schemas.core import Node as Node
from cogant.schemas.core import NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.translate.dsl.schema import DSLCondition as DSLCondition
from cogant.translate.dsl.schema import DSLRuleSet as DSLRuleSet

@dataclass
class CompiledRule:
    name: str
    role: str
    confidence: float
    description: str | None
    def match(self, node: Node, graph: ProgramGraph) -> float: ...

def compile_ruleset(ruleset: DSLRuleSet) -> list[CompiledRule]: ...
