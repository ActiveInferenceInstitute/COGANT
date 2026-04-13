from __future__ import annotations

from typing import Any

class DiffVisualizer:
    bundle1: Any
    bundle2: Any
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    changed: list[dict[str, Any]]
    def __init__(self, bundle1: dict[str, Any], bundle2: dict[str, Any]) -> None: ...
    def render_html(self, output_path: str) -> str: ...
    def render_json(self) -> str: ...
