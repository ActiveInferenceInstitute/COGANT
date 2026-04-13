from typing import Any

from pathlib import Path

console: Any
migrate_app: Any

def migrate(path: Path = ..., dry_run: bool = ..., target: str = ...) -> None: ...
