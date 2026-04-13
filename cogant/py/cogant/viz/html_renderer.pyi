from __future__ import annotations

from pathlib import Path
from typing import Any

class HTMLSiteRenderer:
    bundle: Any
    output_dir: Path
    def __init__(self, bundle: dict[str, Any]) -> None: ...
    def render(self, output_dir: str) -> Path: ...
