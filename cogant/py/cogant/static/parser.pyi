from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class FunctionDef:
    name: str
    line_start: int
    line_end: int
    decorators: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    return_annotation: str | None = ...
    docstring: str | None = ...
    parent: str | None = ...
    is_async: bool = ...
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ClassDef:
    name: str
    line_start: int
    line_end: int
    bases: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = ...
    methods: list[FunctionDef] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ImportDef:
    module_name: str
    is_relative: bool
    names: list[str] = field(default_factory=list)
    line_num: int = ...
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class AssignmentDef:
    target_name: str
    line_num: int
    annotation: str | None = ...
    value: str | None = ...
    parent_scope: str | None = ...
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class PythonModule:
    file_path: Path
    docstring: str | None = ...
    functions: list[FunctionDef] = field(default_factory=list)
    classes: list[ClassDef] = field(default_factory=list)
    imports: list[ImportDef] = field(default_factory=list)
    assignments: list[AssignmentDef] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

class PythonASTParser:
    def parse_file(self, file_path: Path) -> PythonModule: ...
    def parse_string(self, source: str, file_path: Path | None = None) -> PythonModule: ...
