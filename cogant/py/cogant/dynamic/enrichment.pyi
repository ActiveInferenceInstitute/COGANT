from typing import Any

from _typeshed import Incomplete

from cogant.dynamic.coverage import CoverageIngester as CoverageIngester
from cogant.dynamic.traces import TraceIngester as TraceIngester
from cogant.schemas.core import Edge as Edge
from cogant.schemas.core import EdgeKind as EdgeKind
from cogant.schemas.core import NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph

logger: Incomplete

def enrich_graph(graph: ProgramGraph, coverage_path: str | None = None, trace_path: str | None = None) -> dict[str, Any]: ...
