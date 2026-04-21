"""Code metrics: lines of code, Halstead metrics, and coverage statistics."""

import ast
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CodeMetrics:
    """Basic code metrics."""

    lines_of_code: int
    """Total lines of code (excluding blank and comments)."""

    logical_lines: int
    """Logical lines of code (statements)."""

    comment_lines: int
    """Lines containing comments."""

    blank_lines: int
    """Blank lines."""

    docstring_coverage: float
    """Percentage of public symbols with docstrings [0.0, 1.0]."""

    public_symbols: int
    """Count of public symbols."""

    documented_symbols: int
    """Count of documented public symbols."""


@dataclass
class HalsteadMetrics:
    """Halstead complexity metrics."""

    unique_operators: int
    """n1: count of unique operators."""

    unique_operands: int
    """n2: count of unique operands."""

    total_operators: int
    """N1: total count of operators."""

    total_operands: int
    """N2: total count of operands."""

    vocabulary: int
    """n = n1 + n2: vocabulary size."""

    length: int
    """N = N1 + N2: program length."""

    volume: float
    """V = N * log2(n): program volume."""

    difficulty: float
    """D = (n1/2) * (N2/n2): difficulty."""

    effort: float
    """E = D * V: effort to implement."""

    @classmethod
    def compute(cls, source: str) -> "HalsteadMetrics":
        """Compute Halstead metrics from source code.

        Args:
            source: Python source code.

        Returns:
            HalsteadMetrics instance.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return cls(
                unique_operators=0,
                unique_operands=0,
                total_operators=0,
                total_operands=0,
                vocabulary=0,
                length=0,
                volume=0.0,
                difficulty=0.0,
                effort=0.0,
            )

        visitor = HalsteadVisitor()
        visitor.visit(tree)
        return visitor.get_metrics()


class HalsteadVisitor(ast.NodeVisitor):
    """Visit AST to collect Halstead metrics."""

    def __init__(self) -> None:
        """Initialize Halstead visitor."""
        self.operators: list[str] = []
        self.operands: list[str] = []

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Visit binary operation."""
        op_name = node.op.__class__.__name__
        self.operators.append(op_name)
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        """Visit unary operation."""
        op_name = node.op.__class__.__name__
        self.operators.append(op_name)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Visit boolean operation."""
        op_name = node.op.__class__.__name__
        self.operators.append(op_name)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Visit comparison."""
        for op in node.ops:
            op_name = op.__class__.__name__
            self.operators.append(op_name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment."""
        self.operators.append("Assign")
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Visit augmented assignment."""
        self.operators.append("AugAssign")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        self.operators.append("Call")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name reference."""
        self.operands.append(node.id)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Visit constant."""
        if node.value is not None:
            self.operands.append(str(node.value))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Visit attribute access."""
        self.operators.append(".")
        self.operands.append(node.attr)
        self.generic_visit(node)

    def get_metrics(self) -> HalsteadMetrics:
        """Compute and return Halstead metrics.

        Returns:
            HalsteadMetrics instance.
        """
        import math

        n1 = len(set(self.operators))
        n2 = len(set(self.operands))
        N1 = len(self.operators)
        N2 = len(self.operands)

        vocabulary = n1 + n2
        length = N1 + N2

        if vocabulary > 0:
            volume = length * math.log2(vocabulary)
        else:
            volume = 0.0

        if n2 > 0:
            difficulty = (n1 / 2.0) * (N2 / n2)
        else:
            difficulty = 0.0

        effort = difficulty * volume

        return HalsteadMetrics(
            unique_operators=n1,
            unique_operands=n2,
            total_operators=N1,
            total_operands=N2,
            vocabulary=vocabulary,
            length=length,
            volume=volume,
            difficulty=difficulty,
            effort=effort,
        )


class MetricsAnalyzer:
    """Analyze code metrics: lines, coverage, Halstead."""

    def __init__(self) -> None:
        """Initialize metrics analyzer."""
        pass

    def compute(self, source: str) -> CodeMetrics:
        """Compute basic code metrics from source.

        Args:
            source: Python source code.

        Returns:
            CodeMetrics instance.
        """
        if source == "":
            return CodeMetrics(
                lines_of_code=0,
                logical_lines=0,
                comment_lines=0,
                blank_lines=0,
                docstring_coverage=0.0,
                public_symbols=0,
                documented_symbols=0,
            )

        lines = source.splitlines()

        blank_count = 0
        comment_count = 0
        code_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_count += 1
            elif stripped.startswith("#"):
                comment_count += 1
            else:
                code_lines.append(line)

        loc = len(code_lines)

        # Parse to count logical lines and docstrings
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return CodeMetrics(
                lines_of_code=loc,
                logical_lines=0,
                comment_lines=comment_count,
                blank_lines=blank_count,
                docstring_coverage=0.0,
                public_symbols=0,
                documented_symbols=0,
            )

        # Count logical lines via ast statements
        logical_count = len([n for n in ast.walk(tree) if isinstance(n, ast.stmt)])

        # Count public symbols and their docstrings
        visitor = DocstringVisitor()
        visitor.visit(tree)

        public_count = visitor.public_symbols
        documented_count = visitor.documented_symbols

        docstring_coverage = documented_count / public_count if public_count > 0 else 0.0

        return CodeMetrics(
            lines_of_code=loc,
            logical_lines=logical_count,
            comment_lines=comment_count,
            blank_lines=blank_count,
            docstring_coverage=docstring_coverage,
            public_symbols=public_count,
            documented_symbols=documented_count,
        )

    def halstead(self, source: str) -> HalsteadMetrics:
        """Compute Halstead metrics from source.

        Args:
            source: Python source code.

        Returns:
            HalsteadMetrics instance.
        """
        return HalsteadMetrics.compute(source)

    def analyze_file(self, file_path: Path) -> tuple[CodeMetrics, HalsteadMetrics]:
        """Analyze a Python file for all metrics.

        Args:
            file_path: Path to Python file.

        Returns:
            Tuple of (CodeMetrics, HalsteadMetrics).
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            logger.debug(f"Failed to read {file_path}: {e}")
            return (
                CodeMetrics(
                    lines_of_code=0,
                    logical_lines=0,
                    comment_lines=0,
                    blank_lines=0,
                    docstring_coverage=0.0,
                    public_symbols=0,
                    documented_symbols=0,
                ),
                HalsteadMetrics(
                    unique_operators=0,
                    unique_operands=0,
                    total_operators=0,
                    total_operands=0,
                    vocabulary=0,
                    length=0,
                    volume=0.0,
                    difficulty=0.0,
                    effort=0.0,
                ),
            )

        code_metrics = self.compute(source)
        halstead_metrics = self.halstead(source)
        return code_metrics, halstead_metrics


class DocstringVisitor(ast.NodeVisitor):
    """Visit AST to count public symbols and their docstrings."""

    def __init__(self) -> None:
        """Initialize docstring visitor."""
        self.public_symbols = 0
        self.documented_symbols = 0
        self.current_class: str | None = None
        self._class_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        # Count only module-level callables; methods are not separate "symbols" here.
        if self._class_depth == 0 and not node.name.startswith("_"):
            self.public_symbols += 1
            if ast.get_docstring(node) is not None:
                self.documented_symbols += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        if self._class_depth == 0 and not node.name.startswith("_"):
            self.public_symbols += 1
            if ast.get_docstring(node) is not None:
                self.documented_symbols += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        if not node.name.startswith("_"):
            self.public_symbols += 1
            if ast.get_docstring(node) is not None:
                self.documented_symbols += 1
        self._class_depth += 1
        self.generic_visit(node)
        self._class_depth -= 1
