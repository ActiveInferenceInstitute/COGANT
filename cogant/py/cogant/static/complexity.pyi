from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class ComplexityEntry:
    name: str
    qualified_name: str
    kind: str
    file_path: Path
    line_start: int
    line_end: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ComplexityReport:
    file_path: Path
    entries: list[ComplexityEntry] = field(default_factory=list)
    average_cyclomatic: float = 0.0
    average_cognitive: float = 0.0
    max_cyclomatic: int = 0
    max_cognitive: int = 0
    errors: list[str] = field(default_factory=list)
    def get_hotspots(self, threshold: int = 10) -> list[ComplexityEntry]: ...

class ComplexityVisitor(ast.NodeVisitor):
    entries: list[ComplexityEntry]
    current_scope: str
    current_file: Path
    current_class: str | None
    def __init__(self) -> None: ...
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None: ...
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None: ...
    def visit_ClassDef(self, node: ast.ClassDef) -> None: ...

class ComplexityAnalyzer:
    def __init__(self) -> None: ...
    def analyze(self, source: str, file_path: Path) -> ComplexityReport: ...
    def analyze_file(self, file_path: Path) -> ComplexityReport: ...
