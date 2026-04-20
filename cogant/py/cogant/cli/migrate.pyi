from pathlib import Path
from typing import Any

console: Any
migrate_app: Any

def migrate(path: Path = ..., dry_run: bool = ..., target: str = ...) -> None: ...
