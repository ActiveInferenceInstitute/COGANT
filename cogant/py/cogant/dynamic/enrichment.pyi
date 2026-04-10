from _typeshed import Incomplete
from cogant.dynamic.coverage import CoverageIngester as CoverageIngester
from cogant.dynamic.traces import TraceIngester as TraceIngester
from cogant.schemas.core import Edge as Edge, EdgeKind as EdgeKind, NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from typing import Any

logger: Incomplete

def enrich_graph(graph: ProgramGraph, coverage_path: str | None = None, trace_path: str | None = None) -> dict[str, Any]: ...
