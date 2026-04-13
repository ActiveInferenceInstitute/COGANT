from __future__ import annotations

from pathlib import Path

from cogant.schemas.graph import ProgramGraph as ProgramGraph

class ParquetExporter:
    graph: ProgramGraph
    def __init__(self, program_graph: ProgramGraph) -> None: ...
    def export(self, output_dir: Path) -> list[str]: ...
