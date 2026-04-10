from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _typeshed import Incomplete as Incomplete

logger: Incomplete

@dataclass
class TypeInfo:
    symbol_id: str
    symbol_name: str
    symbol_kind: str
    inferred_type: str | None = ...
    annotation: str | None = ...
    is_mutable: bool = ...
    confidence: float = ...
    metadata: dict[str, Any] = field(default_factory=dict)

class TypeInferencer:
    repo_root: Incomplete
    parser: Incomplete
    symbol_extractor: Incomplete
    def __init__(self, repo_root: Path | None = None) -> None: ...
    def infer_types_from_file(self, file_path: Path) -> list[TypeInfo]: ...
    def infer_types_from_source(self, source: str, file_path: Path) -> list[TypeInfo]: ...
