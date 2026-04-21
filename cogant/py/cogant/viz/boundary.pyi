from __future__ import annotations

from typing import Any

from cogant.schemas.graph import ProgramGraph as ProgramGraph

class BoundaryMapper:
    def __init__(self) -> None: ...
    def map_module_boundaries(self, graph: ProgramGraph) -> str: ...
    def map_type_boundaries(self, graph: ProgramGraph) -> str: ...
    def generate_boundary_report(self, graph: ProgramGraph) -> dict[str, Any]: ...
    def markov_blanket_collapsed_mermaid(
        self,
        graph: ProgramGraph,
        blanket: Any = None,
        *,
        strategy: str = "auto",
        **extract_kwargs: Any,
    ) -> str: ...
    def markov_blanket_detailed_mermaid(
        self,
        graph: ProgramGraph,
        blanket: Any = None,
        *,
        strategy: str = "auto",
        max_per_role: int = 12,
        **extract_kwargs: Any,
    ) -> str: ...
