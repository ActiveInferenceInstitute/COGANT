from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from _typeshed import Incomplete as Incomplete

logger: Incomplete
AI_ROLE_COLORS: dict[str, str]
DEFAULT_NODE_COLOR: str
MIN_NODE_SIZE: int
MAX_NODE_SIZE: int
CYTOSCAPE_CDN: str

def build_cytoscape_graph_data(graph: Mapping[str, Any], mappings: Iterable[Any] | None = None) -> dict[str, list[dict[str, Any]]]: ...
def build_cytoscape_html(graph: Mapping[str, Any], mappings: Iterable[Any] | None = None) -> str: ...
def render_cytoscape_html(graph: Mapping[str, Any], output_path: str | Path, mappings: Iterable[Any] | None = None) -> Path: ...
