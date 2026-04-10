from _typeshed import Incomplete
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel
from dataclasses import dataclass

logger: Incomplete

@dataclass
class ProvenanceGap:
    element_id: str
    element_type: str
    message: str
    severity: str

class ProvenanceChecker:
    provenance_records: Incomplete
    gaps: list[ProvenanceGap]
    def __init__(self, provenance_records: dict[str, list[object]] | None = None) -> None: ...
    def check_graph_provenance(self, graph: ProgramGraph) -> list[ProvenanceGap]: ...
    def check_state_space_provenance(self, state_space: StateSpaceModel) -> list[ProvenanceGap]: ...
    def get_gaps(self) -> list[ProvenanceGap]: ...
    def get_coverage_percentage(self, total_elements: int) -> float: ...
    def merge_records(self, other_records: dict[str, list[object]]) -> None: ...
    def add_record(self, element_id: str, record: object) -> None: ...
