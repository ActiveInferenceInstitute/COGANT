from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class CallEdge:
    id: str
    source_file: Path
    caller_id: str
    caller_name: str
    callee_name: str
    callee_id: str | None = ...
    line_num: int = ...
    is_method_call: bool = ...
    receiver: str | None = ...
    args: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

class CallGraphBuilder:
    repo_root: Any
    parser: Any
    symbol_extractor: Any
    def __init__(self, repo_root: Path | None = None) -> None: ...
    def extract_calls_from_file(self, file_path: Path) -> list[CallEdge]: ...
    def extract_calls_from_source(self, source: str, file_path: Path) -> list[CallEdge]: ...

class CallExtractorVisitor(ast.NodeVisitor):
    file_path: Any
    function_name: Any
    scope: Any
    symbol_table: Any
    calls: list[CallEdge]
    def __init__(
        self, file_path: Path, function_name: str, scope: str, symbol_table: Any
    ) -> None: ...
    def visit_Call(self, node: ast.Call) -> None: ...
