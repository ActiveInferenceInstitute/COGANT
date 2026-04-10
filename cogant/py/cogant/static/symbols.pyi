from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _typeshed import Incomplete

from cogant.static.parser import PythonASTParser as PythonASTParser
from cogant.static.parser import PythonModule as PythonModule

logger: Incomplete

@dataclass
class SymbolInfo:
    id: str
    name: str
    qualified_name: str
    kind: str
    file_path: Path
    line_start: int
    line_end: int
    scope: str
    parent_id: str | None = ...
    doc: str | None = ...
    decorators: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class SymbolTable:
    file_path: Path
    symbols: list[SymbolInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

class SymbolExtractor:
    repo_root: Incomplete
    parser: Incomplete
    def __init__(self, repo_root: Path | None = None) -> None: ...
    def extract_from_file(self, file_path: Path) -> SymbolTable: ...
    def extract_from_source(self, source: str, file_path: Path) -> SymbolTable: ...
