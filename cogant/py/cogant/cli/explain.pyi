from cogant.api.bundle import ArtifactKey as ArtifactKey, Bundle as Bundle
from cogant.api.pipeline import PipelineConfig as PipelineConfig, PipelineRunner as PipelineRunner
from cogant.graph.queries import GraphQuery as GraphQuery
from cogant.markov import MarkovBlanketExtractor as MarkovBlanketExtractor
from cogant.markov.blanket import BlanketRole as BlanketRole
from cogant.schemas.core import Node as Node
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import SemanticMapping as SemanticMapping
from cogant.translate.engine import RuleExplanation as RuleExplanation, TranslationEngine as TranslationEngine
from dataclasses import dataclass, field
from rich.console import Console
from typing import Any

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
