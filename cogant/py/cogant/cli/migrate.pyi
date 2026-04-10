from _typeshed import Incomplete
from cogant.schema import SchemaVersion as SchemaVersion, detect_version as detect_version, migrate_gnn as migrate_gnn
from pathlib import Path

console: Incomplete
migrate_app: Incomplete

def migrate(path: Path = ..., dry_run: bool = ..., target: str = ...) -> None: ...
