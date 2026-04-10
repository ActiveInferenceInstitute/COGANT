import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _typeshed import Incomplete

from cogant.static.parser import PythonASTParser as PythonASTParser
from cogant.static.symbols import SymbolExtractor as SymbolExtractor

logger: Incomplete

@dataclass
class DataFlowEdge:
    id: str
    source_symbol: str
    target_symbol: str
    edge_type: str
    file_path: Path
    line_num: int
    context: str = ...
    metadata: dict[str, Any] = field(default_factory=dict)

class DataFlowAnalyzer:
    repo_root: Incomplete
    parser: Incomplete
    symbol_extractor: Incomplete
    def __init__(self, repo_root: Path | None = None) -> None: ...
    def analyze_file(self, file_path: Path) -> list[DataFlowEdge]: ...
    def analyze_source(self, source: str, file_path: Path) -> list[DataFlowEdge]: ...

class DataFlowVisitor(ast.NodeVisitor):
    file_path: Incomplete
    context: Incomplete
    symbol_extractor: Incomplete
    flows: list[DataFlowEdge]
    def __init__(self, file_path: Path, context: str, body: list[ast.stmt], symbol_extractor: Any | None = None) -> None: ...
    def visit_Assign(self, node: ast.Assign) -> None: ...
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None: ...
    def visit_AugAssign(self, node: ast.AugAssign) -> None: ...
    def visit_Return(self, node: ast.Return) -> None: ...
    def visit_Call(self, node: ast.Call) -> None: ...
    def visit_Name(self, node: ast.Name) -> None: ...
    def visit_Attribute(self, node: ast.Attribute) -> None: ...
