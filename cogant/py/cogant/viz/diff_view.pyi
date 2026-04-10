from typing import Any

from _typeshed import Incomplete as Incomplete

logger: Incomplete

class DiffVisualizer:
    bundle1: Incomplete
    bundle2: Incomplete
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    changed: list[dict[str, Any]]
    def __init__(self, bundle1: dict[str, Any], bundle2: dict[str, Any]) -> None: ...
    def render_html(self, output_path: str) -> str: ...
    def render_json(self) -> str: ...
