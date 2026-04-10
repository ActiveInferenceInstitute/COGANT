from dataclasses import dataclass, field
from typing import Any

from rich.console import Console as Console

from cogant.schemas.core import Node as Node
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.translate.engine import RuleExplanation as RuleExplanation

class NodeNotFoundError(LookupError): ...

@dataclass
class ExplainResult:
    node_name: str
    node_id: str
    node_kind: str
    assigned_role: str | None
    rules_fired: list[RuleExplanation]
    rules_considered: list[RuleExplanation]
    blanket_role: str
    target: str = ...
    mapping_label: str | None = ...
    mapping_description: str | None = ...
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]: ...

def resolve_node(graph: ProgramGraph, query: str) -> Node: ...
def explain_node(repo_path: str, node_query: str) -> ExplainResult: ...
def format_text(result: ExplainResult, console: Console | None = None) -> None: ...
def format_json(result: ExplainResult) -> str: ...
