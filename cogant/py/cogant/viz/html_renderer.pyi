from pathlib import Path
from typing import Any

from _typeshed import Incomplete as Incomplete

logger: Incomplete

class HTMLSiteRenderer:
    bundle: Incomplete
    output_dir: Path
    def __init__(self, bundle: dict[str, Any]) -> None: ...
    def render(self, output_dir: str) -> Path: ...
