from pathlib import Path

from _typeshed import Incomplete

from cogant.schema import SchemaVersion as SchemaVersion
from cogant.schema import detect_version as detect_version
from cogant.schema import migrate_gnn as migrate_gnn

console: Incomplete
migrate_app: Incomplete

def migrate(path: Path = ..., dry_run: bool = ..., target: str = ...) -> None: ...
