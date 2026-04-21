"""Call graph extraction: find function/method calls and build call relationships."""

import ast
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cogant.static.parser import PythonASTParser
from cogant.static.symbols import SymbolExtractor

logger = logging.getLogger(__name__)


@dataclass
class CallEdge:
    """A function/method call relationship."""

    id: str
    """Unique edge identifier."""

    source_file: Path
    """File containing the call."""

    caller_id: str
    """Symbol ID of the calling function."""

    caller_name: str
    """Name of calling function/method."""

    callee_name: str
    """Name of called function/method."""

    callee_id: str | None = None
    """Symbol ID of called function (if resolved)."""

    line_num: int = 0
    """Line number of call."""

    is_method_call: bool = False
    """Whether this is a method call."""

    receiver: str | None = None
    """Object/module the method is called on."""

    args: list[str] = field(default_factory=list)
    """Argument values as strings."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


class CallGraphBuilder:
    """Extract function and method calls from Python source."""

    def __init__(self, repo_root: Path | None = None):
        """Initialize call graph builder.

        Args:
            repo_root: Root path of repository.
        """
        self.repo_root = Path(repo_root or "/")
        self.parser = PythonASTParser()
        self.symbol_extractor = SymbolExtractor(repo_root)

    def extract_calls_from_file(self, file_path: Path) -> list[CallEdge]:
        """Extract all function/method calls from a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            List of CallEdge for all calls found.
        """
        module = self.parser.parse_file(file_path)
        symbol_table = self.symbol_extractor.extract_from_file(file_path)

        calls = []
        for func in module.functions:
            call_visitor = CallExtractorVisitor(file_path, func.name, "module", symbol_table)
            # Parse again to visit AST
            try:
                with open(file_path) as f:
                    tree = ast.parse(f.read())
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == func.name:
                        call_visitor.visit(node)
                        calls.extend(call_visitor.calls)
            except Exception as e:
                logger.debug(f"Failed to extract calls from {func.name}: {e}")

        for cls in module.classes:
            for method in cls.methods:
                call_visitor = CallExtractorVisitor(file_path, method.name, cls.name, symbol_table)
                try:
                    with open(file_path) as f:
                        tree = ast.parse(f.read())
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef) and node.name == cls.name:
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef) and item.name == method.name:
                                    call_visitor.visit(item)
                                    calls.extend(call_visitor.calls)
                except Exception as e:
                    logger.debug(f"Failed to extract calls from {cls.name}.{method.name}: {e}")

        return calls

    def extract_calls_from_source(self, source: str, file_path: Path) -> list[CallEdge]:
        """Extract function/method calls from Python source code.

        Args:
            source: Python source code.
            file_path: Path for reference.

        Returns:
            List of CallEdge for all calls found.
        """
        module = self.parser.parse_string(source, file_path)
        symbol_table = self.symbol_extractor.extract_from_source(source, file_path)

        calls = []
        try:
            tree = ast.parse(source)
            for func in module.functions:
                call_visitor = CallExtractorVisitor(file_path, func.name, "module", symbol_table)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == func.name:
                        call_visitor.visit(node)
                        calls.extend(call_visitor.calls)

            for cls in module.classes:
                for method in cls.methods:
                    call_visitor = CallExtractorVisitor(
                        file_path, method.name, cls.name, symbol_table
                    )
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef) and node.name == cls.name:
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef) and item.name == method.name:
                                    call_visitor.visit(item)
                                    calls.extend(call_visitor.calls)
        except Exception as e:
            logger.debug(f"Failed to extract calls from source: {e}")

        return calls


class CallExtractorVisitor(ast.NodeVisitor):
    """AST visitor to extract function/method calls."""

    def __init__(
        self,
        file_path: Path,
        function_name: str,
        scope: str,
        symbol_table: Any,
    ):
        """Initialize call extractor visitor.

        Args:
            file_path: Source file path.
            function_name: Name of the function being analyzed.
            scope: Scope context (module or class name).
            symbol_table: SymbolTable for callee resolution.
        """
        self.file_path = file_path
        self.function_name = function_name
        self.scope = scope
        self.symbol_table = symbol_table
        self.calls: list[CallEdge] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call node.

        Args:
            node: AST Call node.
        """
        call_edge = self._extract_call(node)
        if call_edge:
            self.calls.append(call_edge)

        self.generic_visit(node)

    def _extract_call(self, node: ast.Call) -> CallEdge | None:
        """Extract call information from AST Call node.

        Args:
            node: AST Call node.

        Returns:
            CallEdge or None if extraction failed.
        """
        try:
            callee_name = None
            receiver = None
            is_method_call = False

            # Handle different call types
            if isinstance(node.func, ast.Name):
                # Simple function call: foo()
                callee_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                # Method call: obj.method()
                is_method_call = True
                callee_name = node.func.attr
                receiver = self._ast_to_str(node.func.value)
            else:
                # Complex call expression
                callee_name = self._ast_to_str(node.func)

            if not callee_name:
                return None

            # Extract arguments
            args = [self._ast_to_str(arg) for arg in node.args]

            # Try to resolve callee ID
            callee_id = None
            for sym in self.symbol_table.symbols:
                if sym.name == callee_name:
                    callee_id = sym.id
                    break

            # Create caller ID
            caller_id = self._generate_caller_id(self.function_name, self.scope)

            return CallEdge(
                id=self._generate_call_id(
                    self.file_path, self.function_name, callee_name, node.lineno
                ),
                source_file=self.file_path,
                caller_id=caller_id,
                caller_name=self.function_name,
                callee_name=callee_name,
                callee_id=callee_id,
                line_num=node.lineno,
                is_method_call=is_method_call,
                receiver=receiver,
                args=args,
            )

        except Exception as e:
            logger.debug(f"Failed to extract call: {e}")
            return None

    @staticmethod
    def _ast_to_str(node: ast.AST) -> str:
        """Convert AST node to string.

        Args:
            node: AST node.

        Returns:
            String representation.
        """
        try:
            return ast.unparse(node)
        except Exception:
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Constant):
                return repr(node.value)
            elif isinstance(node, ast.Attribute):
                return f"{CallExtractorVisitor._ast_to_str(node.value)}.{node.attr}"
            else:
                return type(node).__name__

    @staticmethod
    def _generate_caller_id(function_name: str, scope: str) -> str:
        """Generate caller symbol ID.

        Args:
            function_name: Function name.
            scope: Scope context.

        Returns:
            Caller ID.
        """
        content = f"{scope}#{function_name}"
        hash_obj = hashlib.sha256(content.encode())
        return hash_obj.hexdigest()[:16]

    @staticmethod
    def _generate_call_id(file_path: Path, caller: str, callee: str, line_num: int) -> str:
        """Generate call edge ID.

        Args:
            file_path: Source file path.
            caller: Caller function name.
            callee: Callee function name.
            line_num: Line number of call.

        Returns:
            Call edge ID.
        """
        content = f"{file_path}:{caller}→{callee}:{line_num}"
        hash_obj = hashlib.sha256(content.encode())
        return hash_obj.hexdigest()[:16]
