from dataclasses import dataclass, field
from typing import Any

from cogant.markov.blanket import BlanketRole as BlanketRole
from cogant.markov.blanket import MarkovBlanket as MarkovBlanket
from cogant.schemas.core import EdgeKind as EdgeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph

@dataclass
class BlanketNetwork:
    role_counts: dict[str, int]
    role_members: dict[str, list[str]]
    aggregate_edges: dict[tuple[str, str], int]
    edge_kind_breakdown: dict[tuple[str, str], dict[str, int]]
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]: ...
    def to_mermaid(self) -> str: ...

def build_blanket_network(graph: ProgramGraph, blanket: MarkovBlanket) -> BlanketNetwork: ...
