from pathlib import Path

from _typeshed import Incomplete as Incomplete

from cogant.schemas.graph import ProgramGraph as ProgramGraph

logger: Incomplete

class ParquetExporter:
    graph: Incomplete
    def __init__(self, program_graph: ProgramGraph) -> None: ...
    def export(self, output_dir: Path) -> list[str]: ...
