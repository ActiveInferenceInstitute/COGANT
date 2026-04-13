from typing import Any

from cogant.schemas.graph import ProgramGraph as ProgramGraph

def enrich_graph(graph: ProgramGraph, coverage_path: str | None = None, trace_path: str | None = None) -> dict[str, Any]: ...
