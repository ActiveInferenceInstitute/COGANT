from typing import Any

from _typeshed import Incomplete as Incomplete

logger: Incomplete

class SemanticVisualizer:
    states: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    policies: list[dict[str, Any]]
    transitions: list[dict[str, Any]]
    def __init__(self) -> None: ...
    def from_state_space(self, state_space: dict[str, Any]) -> SemanticVisualizer: ...
    def render_html(self, output_path: str) -> str: ...
    def render_json(self) -> str: ...
