from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class DeadCodeEntry:
    symbol_name: str
    file_path: Path
    line_num: int
    kind: str
    scope: str = "module"
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class DeadCodeReport:
    file_path: Path
    entries: list[DeadCodeEntry] = field(default_factory=list)
    unused_imports: int = 0
    unused_functions: int = 0
    unused_variables: int = 0
    unreachable_statements: int = 0
    errors: list[str] = field(default_factory=list)
    def get_certain_entries(self) -> list[DeadCodeEntry]: ...

class DeadCodeDetector(ast.NodeVisitor):
    file_path: Path
    entries: list[DeadCodeEntry]
    defined_names: dict[str, int]
    used_names: set[str]
    imported_names: dict[str, int]
    function_defs: dict[str, int]
    class_defs: dict[str, int]
    variable_defs: dict[str, int]
    current_scope: str
    current_function: str | None
    current_class: str | None
    def __init__(self, file_path: Path) -> None: ...
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None: ...
    def visit_Import(self, node: ast.Import) -> None: ...
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None: ...
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None: ...
    def visit_ClassDef(self, node: ast.ClassDef) -> None: ...
    def visit_Assign(self, node: ast.Assign) -> None: ...
    def visit_Name(self, node: ast.Name) -> None: ...
    def visit_Return(self, node: ast.Return) -> None: ...
    def visit_Raise(self, node: ast.Raise) -> None: ...
    def visit_Break(self, node: ast.Break) -> None: ...
    def visit_Continue(self, node: ast.Continue) -> None: ...

class DeadCodeAnalyzer:
    def __init__(self) -> None: ...
    def analyze(self, source: str, file_path: Path) -> DeadCodeReport: ...
    def analyze_file(self, file_path: Path) -> DeadCodeReport: ...
