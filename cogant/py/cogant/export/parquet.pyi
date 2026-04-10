from _typeshed import Incomplete
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from pathlib import Path

logger: Incomplete

class ParquetExporter:
    graph: Incomplete
    def __init__(self, program_graph: ProgramGraph) -> None: ...
    def export(self, output_dir: Path) -> list[str]: ...
