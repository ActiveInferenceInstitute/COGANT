from collections.abc import Iterable, Sequence
from typing import Any

from cogant.markov.blanket import MarkovBlanket as MarkovBlanket
from cogant.schemas.core import NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph

SeedStrategy: Any

class MarkovBlanketExtractor:
    graph: Any
    prefer_boundary: Any
    def __init__(self, graph: ProgramGraph, *, prefer_boundary: int = 1) -> None: ...
    def extract(
        self,
        *,
        strategy: SeedStrategy = "auto",
        seeds: Iterable[str] | None = None,
        module_names: Sequence[str] | None = None,
        kinds: Sequence[NodeKind] | None = None,
        mapping_kinds: Sequence[str] | None = None,
        semantic_mappings: dict[str, Any] | None = None,
    ) -> MarkovBlanket: ...
