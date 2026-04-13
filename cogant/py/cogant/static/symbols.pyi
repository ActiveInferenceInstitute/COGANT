from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    def get_public_api(self) -> list[SymbolInfo]: ...
    def get_entry_points(self) -> list[SymbolInfo]: ...
    def to_json(self) -> str: ...

class SymbolExtractor:
    repo_root: Path | None
    parser: Any
    def __init__(self, repo_root: Path | None = None) -> None: ...
    def extract_from_file(self, file_path: Path) -> SymbolTable: ...
    def extract_from_source(self, source: str, file_path: Path) -> SymbolTable: ...
