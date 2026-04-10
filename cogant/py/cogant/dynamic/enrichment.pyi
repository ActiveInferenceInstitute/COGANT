from typing import Any

from _typeshed import Incomplete as Incomplete

from cogant.schemas.graph import ProgramGraph as ProgramGraph

logger: Incomplete

def enrich_graph(graph: ProgramGraph, coverage_path: str | None = None, trace_path: str | None = None) -> dict[str, Any]: ...
