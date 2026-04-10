from _typeshed import Incomplete
from cogant.viz.cytoscape_view import build_cytoscape_html as build_cytoscape_html
from pathlib import Path
from typing import Any

logger: Incomplete

class HTMLSiteRenderer:
    bundle: Incomplete
    output_dir: Path
    def __init__(self, bundle: dict[str, Any]) -> None: ...
    def render(self, output_dir: str) -> Path: ...
