from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from cogant.schemas.graph import ProgramGraph as ProgramGraph

class BlanketRole(StrEnum):
    INTERNAL = 'internal'
    SENSORY = 'sensory'
    ACTIVE = 'active'
    EXTERNAL = 'external'

@dataclass
class MarkovBlanket:
    roles: dict[str, BlanketRole]
    seeds: set[str]
    internal_ids: set[str] = field(default_factory=set)
    sensory_ids: set[str] = field(default_factory=set)
    active_ids: set[str] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    rationale: dict[str, str] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    @property
    def boundary_ids(self) -> set[str]: ...
    def role_of(self, node_id: str) -> BlanketRole: ...
    def ids_by_role(self, role: BlanketRole) -> set[str]: ...

def partition_by_seeds(graph: ProgramGraph, seeds: Iterable[str], *, adjacency: Mapping[str, tuple[set[str], set[str]]] | None = None) -> MarkovBlanket: ...
def serialize_blanket(blanket: MarkovBlanket, graph: ProgramGraph, *, include_rationale: bool = True, max_nodes_per_role: int | None = None) -> dict[str, Any]: ...
