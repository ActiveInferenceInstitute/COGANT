from _typeshed import Incomplete as Incomplete

from cogant.schemas.graph import ProgramGraph as ProgramGraph

logger: Incomplete

class GraphMLExporter:
    graph: Incomplete
    def __init__(self, program_graph: ProgramGraph) -> None: ...
    def export(self) -> str: ...
