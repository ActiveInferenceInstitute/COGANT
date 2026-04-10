from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _typeshed import Incomplete

from cogant.static.parser import PythonASTParser as PythonASTParser

logger: Incomplete

@dataclass
class ImportEdge:
    id: str
    source_file: Path
    module_name: str
    is_relative: bool
    is_stdlib: bool
    is_third_party: bool
    is_local: bool
    resolved_file: Path | None = ...
    resolved_module: str | None = ...
    line_num: int = ...
    imported_names: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

class ImportAnalyzer:
    repo_root: Incomplete
    parser: Incomplete
    def __init__(self, repo_root: Path | None = None) -> None: ...
    def analyze_file(self, file_path: Path) -> list[ImportEdge]: ...
    def analyze_source(self, source: str, file_path: Path) -> list[ImportEdge]: ...
