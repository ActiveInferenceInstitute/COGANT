"""Complexity metrics: cyclomatic and cognitive complexity analysis."""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ComplexityEntry:
    """Complexity metrics for a single symbol."""

    name: str
    """Symbol name."""

    qualified_name: str
    """Fully qualified symbol name."""

    kind: str
    """Symbol kind (function, method, class)."""

    file_path: Path
    """Source file path."""

    line_start: int
    """Starting line number."""

    line_end: int
    """Ending line number."""

    cyclomatic_complexity: int
    """Cyclomatic complexity (decision point count)."""

    cognitive_complexity: int
    """Cognitive complexity (nesting depth + decision points)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class ComplexityReport:
    """Aggregated complexity metrics for a module."""

    file_path: Path
    """Source file path."""

    entries: list[ComplexityEntry] = field(default_factory=list)
    """Per-symbol complexity entries."""

    average_cyclomatic: float = 0.0
    """Average cyclomatic complexity across all functions."""

    average_cognitive: float = 0.0
    """Average cognitive complexity across all functions."""

    max_cyclomatic: int = 0
    """Maximum cyclomatic complexity in module."""

    max_cognitive: int = 0
    """Maximum cognitive complexity in module."""

    errors: list[str] = field(default_factory=list)
    """Errors encountered during analysis."""

    def get_hotspots(self, threshold: int = 10) -> list[ComplexityEntry]:
        """Get functions exceeding complexity threshold.

        Args:
            threshold: Cyclomatic complexity threshold.

        Returns:
            Sorted list of ComplexityEntry above threshold.
        """
        hotspots = [e for e in self.entries if e.cyclomatic_complexity >= threshold]
        return sorted(hotspots, key=lambda e: e.cyclomatic_complexity, reverse=True)


class ComplexityVisitor(ast.NodeVisitor):
    """Visit AST nodes to compute complexity metrics."""

    def __init__(self) -> None:
        """Initialize complexity visitor."""
        self.entries: list[ComplexityEntry] = []
        self.current_scope: str = "module"
        self.current_file: Path = Path("<unknown>")
        self.current_class: str | None = None
        self._nesting_depth: int = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._visit_function_like(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self._visit_function_like(node)

    def _visit_function_like(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Process a function or method node.

        Args:
            node: Function or async function node.
        """
        qualified_name = node.name
        if self.current_class:
            qualified_name = f"{self.current_class}.{node.name}"

        cc = self._compute_cyclomatic_complexity(node.body)
        cog = self._compute_cognitive_complexity(node.body, base_depth=1)

        entry = ComplexityEntry(
            name=node.name,
            qualified_name=qualified_name,
            kind="method" if self.current_class else "function",
            file_path=self.current_file,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            cyclomatic_complexity=cc,
            cognitive_complexity=cog,
        )
        self.entries.append(entry)

        # Visit nested functions
        old_scope = self.current_scope
        old_class = self.current_class
        self.current_scope = node.name
        for stmt in node.body:
            self.visit(stmt)
        self.current_scope = old_scope
        self.current_class = old_class

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def _compute_cyclomatic_complexity(self, body: list[ast.stmt]) -> int:
        """Compute cyclomatic complexity for a code block.

        Counts decision points: if, elif, for, while, except, and/or operators, ternary.

        Args:
            body: List of AST statements.

        Returns:
            Cyclomatic complexity score (minimum 1).
        """
        complexity = 1
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            # try adds one decision unit (paired with except handlers)
            if isinstance(node, ast.Try):
                complexity += 1
            # if/elif adds complexity
            elif isinstance(node, ast.If):
                complexity += 1
            # for/while adds complexity
            elif isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
                complexity += 1
            # except handlers add complexity
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            # boolean operators (and, or) add complexity
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            # ternary (IfExp) adds complexity
            elif isinstance(node, ast.IfExp):
                complexity += 1
        return complexity

    def _compute_cognitive_complexity(self, body: list[ast.stmt], base_depth: int = 0) -> int:
        """Compute cognitive complexity for a code block.

        Penalizes nesting depth and decision points.

        Args:
            body: List of AST statements.
            base_depth: Base nesting depth.

        Returns:
            Cognitive complexity score.
        """
        complexity = 0
        for stmt in body:
            complexity += self._cognitive_score_node(stmt, base_depth)
        return complexity

    def _cognitive_score_node(self, node: ast.stmt, depth: int) -> int:
        """Score cognitive complexity of a single node.

        Args:
            node: AST node.
            depth: Current nesting depth.

        Returns:
            Cognitive score for this node.
        """
        score = 0

        # Depth penalty
        depth_penalty = max(0, depth - 1)

        if isinstance(node, ast.If):
            score += 1 + depth_penalty
            # Recursively score the body and orelse
            for stmt in node.body:
                score += self._cognitive_score_node(stmt, depth + 1)
            for stmt in node.orelse:
                score += self._cognitive_score_node(stmt, depth + 1)
        elif isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            score += 1 + depth_penalty
            for stmt in node.body:
                score += self._cognitive_score_node(stmt, depth + 1)
            for stmt in node.orelse:
                score += self._cognitive_score_node(stmt, depth + 1)
        elif isinstance(node, ast.Try):
            score += 1 + depth_penalty
            for stmt in node.body:
                score += self._cognitive_score_node(stmt, depth + 1)
            for handler in node.handlers:
                score += 1 + depth_penalty
                for stmt in handler.body:
                    score += self._cognitive_score_node(stmt, depth + 1)
            for stmt in node.orelse:
                score += self._cognitive_score_node(stmt, depth + 1)
            for stmt in node.finalbody:
                score += self._cognitive_score_node(stmt, depth + 1)
        elif isinstance(node, ast.With):
            score += depth_penalty
            for stmt in node.body:
                score += self._cognitive_score_node(stmt, depth + 1)
        else:
            # Other statements may contain nested control flow
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.stmt):
                    score += self._cognitive_score_node(child, depth)

        return score


class ComplexityAnalyzer:
    """Compute cyclomatic and cognitive complexity metrics."""

    def __init__(self) -> None:
        """Initialize complexity analyzer."""
        pass

    def analyze(self, source: str, file_path: Path) -> ComplexityReport:
        """Analyze complexity of Python source code.

        Args:
            source: Python source code.
            file_path: Path for reference.

        Returns:
            ComplexityReport with metrics.
        """
        report = ComplexityReport(file_path=file_path)

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            report.errors.append(f"Syntax error: {e}")
            return report

        visitor = ComplexityVisitor()
        visitor.current_file = file_path
        visitor.visit(tree)
        report.entries = visitor.entries

        # Compute aggregates
        if report.entries:
            cc_values = [e.cyclomatic_complexity for e in report.entries]
            cog_values = [e.cognitive_complexity for e in report.entries]
            report.average_cyclomatic = sum(cc_values) / len(cc_values)
            report.average_cognitive = sum(cog_values) / len(cog_values)
            report.max_cyclomatic = max(cc_values)
            report.max_cognitive = max(cog_values)

        return report

    def analyze_file(self, file_path: Path) -> ComplexityReport:
        """Analyze complexity of a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            ComplexityReport with metrics.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            report = ComplexityReport(file_path=file_path)
            report.errors.append(f"Failed to read file: {e}")
            return report

        return self.analyze(source, file_path)
