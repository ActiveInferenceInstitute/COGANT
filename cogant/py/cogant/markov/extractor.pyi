from _typeshed import Incomplete
from cogant.markov.blanket import MarkovBlanket as MarkovBlanket, partition_by_seeds as partition_by_seeds
from cogant.schemas.core import EdgeKind as EdgeKind, NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from collections.abc import Iterable, Sequence
from typing import Any

logger: Incomplete
SeedStrategy: Incomplete

class MarkovBlanketExtractor:
    graph: Incomplete
    prefer_boundary: Incomplete
    def __init__(self, graph: ProgramGraph, *, prefer_boundary: int = 1) -> None: ...
    def extract(self, *, strategy: SeedStrategy = 'auto', seeds: Iterable[str] | None = None, module_names: Sequence[str] | None = None, kinds: Sequence[NodeKind] | None = None, mapping_kinds: Sequence[str] | None = None, semantic_mappings: dict[str, Any] | None = None) -> MarkovBlanket: ...
