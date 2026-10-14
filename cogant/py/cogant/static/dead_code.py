"""Dead code detection: identify unused imports, functions, and unreachable code."""

import ast
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Statements after one of these, in the same block, can never execute.
_TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)


def _is_dunder(name: str) -> bool:
    """Return True for ``__name__``-style names the runtime looks up implicitly."""
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


def _unreachable_blocks(tree: ast.AST) -> Iterator[tuple[str, ast.stmt, int, str]]:
    """Yield ``(scope, first_dead_stmt, dead_count, terminator)`` per dead block.

    A block is the tail of a statement list (``body``/``orelse``/
    ``finalbody`` of any node, including except handlers and match cases)
    that follows a ``return``, ``raise``, ``break`` or ``continue``.
    """

    def walk(node: ast.AST, scope: str) -> Iterator[tuple[str, ast.stmt, int, str]]:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            scope = f"function:{node.name}"
        elif isinstance(node, ast.ClassDef):
            scope = f"class:{node.name}"
        for field_name in ("body", "orelse", "finalbody"):
            stmts = getattr(node, field_name, None)
            if not isinstance(stmts, list):
                continue
            for index, stmt in enumerate(stmts[:-1]):
                if isinstance(stmt, _TERMINATORS):
                    terminator = type(stmt).__name__.lower()
                    yield scope, stmts[index + 1], len(stmts) - index - 1, terminator
                    break
        for child in ast.iter_child_nodes(node):
            yield from walk(child, scope)

    yield from walk(tree, "module")


@dataclass
class DeadCodeEntry:
    """Information about a dead code instance."""

    symbol_name: str
    """Name of unused/unreachable symbol."""

    file_path: Path
    """Source file path."""

    line_num: int
    """Line number where symbol is defined."""

    kind: str
    """Kind: UNUSED_IMPORT, UNUSED_FUNCTION, UNUSED_VARIABLE, UNREACHABLE."""

    scope: str = "module"
    """Scope context (module, class_name, function_name)."""

    confidence: float = 1.0
    """Confidence score [0.0, 1.0]. 1.0 = certain, < 1.0 = heuristic."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class DeadCodeReport:
    """Aggregated dead code findings."""

    file_path: Path
    """Source file path."""

    entries: list[DeadCodeEntry] = field(default_factory=list)
    """Dead code entries."""

    unused_imports: int = 0
    """Count of unused imports."""

    unused_functions: int = 0
    """Count of unused functions."""

    unused_variables: int = 0
    """Count of unused variables."""

    unreachable_statements: int = 0
    """Count of unreachable statements (summed over UNREACHABLE entries)."""

    errors: list[str] = field(default_factory=list)
    """Errors encountered during analysis."""

    def get_certain_entries(self) -> list[DeadCodeEntry]:
        """Get entries with high confidence (>= 0.9).

        Returns:
            List of high-confidence dead code entries.
        """
        return [e for e in self.entries if e.confidence >= 0.9]


class DeadCodeDetector(ast.NodeVisitor):
    """Detect dead code: unused imports, functions, variables, and unreachable statements."""

    def __init__(self, file_path: Path) -> None:
        """Initialize dead code detector.

        Args:
            file_path: Path to file being analyzed.
        """
        self.file_path = file_path
        self.entries: list[DeadCodeEntry] = []

        # Track names defined and used
        self.defined_names: dict[str, int] = {}  # name -> line number
        self.used_names: set[str] = set()
        # Attribute names read anywhere (``self._helper()``, ``obj._cache``).
        self.used_attributes: set[str] = set()
        self.imported_names: dict[str, int] = {}  # imported_name -> line number
        self.function_defs: dict[str, int] = {}  # function_name -> line number
        self.class_defs: dict[str, int] = {}  # class_name -> line number
        self.variable_defs: dict[str, int] = {}  # variable_name -> line number

        self.current_scope: str = "module"
        self.current_function: str | None = None
        self.current_class: str | None = None
        self._in_unreachable_block: bool = False

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit import from statement.

        ``from __future__`` imports are compiler directives and ``*`` binds
        no single name, so neither is tracked as a possibly unused import.
        """
        if node.module != "__future__":
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname if alias.asname else alias.name
                self.imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement.

        ``import a.b`` binds the top-level name ``a`` (``import a.b as c``
        binds ``c``), so that bound name is what later code must use.
        """
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".", 1)[0]
            self.imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self.function_defs[node.name] = node.lineno
        old_func = self.current_function
        old_scope = self.current_scope
        self.current_function = node.name
        self.current_scope = f"function:{node.name}"
        self.generic_visit(node)
        self.current_function = old_func
        self.current_scope = old_scope

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self.function_defs[node.name] = node.lineno
        old_func = self.current_function
        old_scope = self.current_scope
        self.current_function = node.name
        self.current_scope = f"function:{node.name}"
        self.generic_visit(node)
        self.current_function = old_func
        self.current_scope = old_scope

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        self.class_defs[node.name] = node.lineno
        old_class = self.current_class
        old_scope = self.current_scope
        self.current_class = node.name
        self.current_scope = f"class:{node.name}"
        self.generic_visit(node)
        self.current_class = old_class
        self.current_scope = old_scope

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment."""
        # Record defined variables
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variable_defs[target.id] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name reference."""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Record attribute reads so ``self._helper()`` counts as a use of ``_helper``."""
        if isinstance(node.ctx, ast.Load):
            self.used_attributes.add(node.attr)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Visit return statement (unreachable tails are found by the analyzer)."""
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """Visit raise statement (unreachable tails are found by the analyzer)."""
        self.generic_visit(node)

    def visit_Break(self, node: ast.Break) -> None:
        """Visit break statement."""
        self.generic_visit(node)

    def visit_Continue(self, node: ast.Continue) -> None:
        """Visit continue statement."""
        self.generic_visit(node)


class DeadCodeAnalyzer:
    """Analyze Python source for dead code."""

    def __init__(self) -> None:
        """Initialize dead code analyzer."""
        pass

    def analyze(self, source: str, file_path: Path) -> DeadCodeReport:
        """Analyze source code for dead code.

        Args:
            source: Python source code.
            file_path: Path for reference.

        Returns:
            DeadCodeReport with findings.
        """
        report = DeadCodeReport(file_path=file_path)

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            report.errors.append(f"Syntax error: {e}")
            return report

        detector = DeadCodeDetector(file_path)
        detector.visit(tree)

        # Detect unused imports
        for name, line_num in detector.imported_names.items():
            if name not in detector.used_names and not name.startswith("_"):
                entry = DeadCodeEntry(
                    symbol_name=name,
                    file_path=file_path,
                    line_num=line_num,
                    kind="UNUSED_IMPORT",
                    confidence=0.95,  # High confidence for imports
                )
                report.entries.append(entry)
                report.unused_imports += 1

        # Names read directly or through an attribute (``self._x``).
        referenced = detector.used_names | detector.used_attributes

        # Detect unused private functions (dunders are invoked by the runtime)
        for name, line_num in detector.function_defs.items():
            if name.startswith("_") and not _is_dunder(name) and name not in referenced:
                entry = DeadCodeEntry(
                    symbol_name=name,
                    file_path=file_path,
                    line_num=line_num,
                    kind="UNUSED_FUNCTION",
                    confidence=0.8,  # Lower confidence; may be called dynamically
                )
                report.entries.append(entry)
                report.unused_functions += 1

        # Detect unused private variables (``__all__`` & co. are read implicitly)
        for name, line_num in detector.variable_defs.items():
            if name.startswith("_") and not _is_dunder(name) and name not in referenced:
                entry = DeadCodeEntry(
                    symbol_name=name,
                    file_path=file_path,
                    line_num=line_num,
                    kind="UNUSED_VARIABLE",
                    confidence=0.7,  # Lower confidence; may be used elsewhere
                )
                report.entries.append(entry)
                report.unused_variables += 1

        # Detect statements that follow return/raise/break/continue
        blocks = sorted(_unreachable_blocks(tree), key=lambda block: block[1].lineno)
        for scope, stmt, dead_count, terminator in blocks:
            try:
                text = ast.unparse(stmt).splitlines()[0][:80]
            except Exception:
                text = type(stmt).__name__
            report.entries.append(
                DeadCodeEntry(
                    symbol_name=text,
                    file_path=file_path,
                    line_num=stmt.lineno,
                    kind="UNREACHABLE",
                    scope=scope,
                    confidence=1.0,  # Control flow cannot reach these statements
                    metadata={"after": terminator, "statements": dead_count},
                )
            )
            report.unreachable_statements += dead_count

        return report

    def analyze_file(self, file_path: Path) -> DeadCodeReport:
        """Analyze a Python file for dead code.

        Args:
            file_path: Path to Python file.

        Returns:
            DeadCodeReport with findings.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            report = DeadCodeReport(file_path=file_path)
            report.errors.append(f"Failed to read file: {e}")
            return report

        return self.analyze(source, file_path)
