"""Python AST parsing for extracting code structure."""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FunctionDef:
    """Function definition from AST."""

    name: str
    """Function name."""

    line_start: int
    """Starting line number."""

    line_end: int
    """Ending line number."""

    decorators: List[str] = field(default_factory=list)
    """List of decorator names."""

    args: List[str] = field(default_factory=list)
    """Parameter names."""

    return_annotation: Optional[str] = None
    """Return type annotation if present."""

    docstring: Optional[str] = None
    """Function docstring."""

    parent: Optional[str] = None
    """Parent class name if method."""

    is_async: bool = False
    """Whether function is async."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class ClassDef:
    """Class definition from AST."""

    name: str
    """Class name."""

    line_start: int
    """Starting line number."""

    line_end: int
    """Ending line number."""

    bases: List[str] = field(default_factory=list)
    """Base class names."""

    decorators: List[str] = field(default_factory=list)
    """List of decorator names."""

    docstring: Optional[str] = None
    """Class docstring."""

    methods: List[FunctionDef] = field(default_factory=list)
    """Methods defined in class."""

    attributes: List[str] = field(default_factory=list)
    """Class attributes."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class ImportDef:
    """Import statement from AST."""

    module_name: str
    """Module being imported."""

    is_relative: bool
    """Whether import is relative."""

    names: List[str] = field(default_factory=list)
    """Specific names imported (for 'from X import Y')."""

    line_num: int = 0
    """Line number of import."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class AssignmentDef:
    """Variable assignment from AST."""

    target_name: str
    """Variable name being assigned."""

    line_num: int
    """Line number of assignment."""

    annotation: Optional[str] = None
    """Type annotation if present."""

    value: Optional[str] = None
    """String representation of assigned value."""

    parent_scope: Optional[str] = None
    """Scope containing assignment (module or function)."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class PythonModule:
    """Complete parsed Python module."""

    file_path: Path
    """Source file path."""

    docstring: Optional[str] = None
    """Module docstring."""

    functions: List[FunctionDef] = field(default_factory=list)
    """Module-level functions."""

    classes: List[ClassDef] = field(default_factory=list)
    """Module-level classes."""

    imports: List[ImportDef] = field(default_factory=list)
    """Import statements."""

    assignments: List[AssignmentDef] = field(default_factory=list)
    """Module-level assignments."""

    errors: List[str] = field(default_factory=list)
    """Parse errors encountered."""


class PythonASTParser:
    """Parse Python source files and extract AST information."""

    def parse_file(self, file_path: Path) -> PythonModule:
        """Parse a Python source file.

        Args:
            file_path: Path to Python file.

        Returns:
            PythonModule with extracted AST information.
        """
        module = PythonModule(file_path=file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception as e:
            module.errors.append(f"Failed to read file: {e}")
            return module

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            module.errors.append(f"Syntax error: {e}")
            return module
        except Exception as e:
            module.errors.append(f"Parse error: {e}")
            return module

        # Extract module docstring
        if (
            isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            module.docstring = tree.body[0].value.value

        # Visit all nodes
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) or isinstance(
                node, ast.AsyncFunctionDef
            ):
                func = self._extract_function(node)
                if func:
                    module.functions.append(func)
            elif isinstance(node, ast.ClassDef):
                cls = self._extract_class(node)
                if cls:
                    module.classes.append(cls)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports = self._extract_imports(node)
                module.imports.extend(imports)
            elif isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign):
                assign = self._extract_assignment(node)
                if assign:
                    module.assignments.append(assign)

        return module

    def parse_string(self, source: str, file_path: Optional[Path] = None) -> PythonModule:
        """Parse Python source from string.

        Args:
            source: Python source code as string.
            file_path: Optional file path for reference.

        Returns:
            PythonModule with extracted AST information.
        """
        if file_path is None:
            file_path = Path("<string>")

        module = PythonModule(file_path=file_path)

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            module.errors.append(f"Syntax error: {e}")
            return module
        except Exception as e:
            module.errors.append(f"Parse error: {e}")
            return module

        # Extract module docstring
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            module.docstring = tree.body[0].value.value

        # Visit all nodes
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) or isinstance(
                node, ast.AsyncFunctionDef
            ):
                func = self._extract_function(node)
                if func:
                    module.functions.append(func)
            elif isinstance(node, ast.ClassDef):
                cls = self._extract_class(node)
                if cls:
                    module.classes.append(cls)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports = self._extract_imports(node)
                module.imports.extend(imports)
            elif isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign):
                assign = self._extract_assignment(node)
                if assign:
                    module.assignments.append(assign)

        return module

    def _extract_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> Optional[FunctionDef]:
        """Extract function definition from AST node.

        Args:
            node: AST FunctionDef or AsyncFunctionDef node.

        Returns:
            FunctionDef or None if extraction failed.
        """
        try:
            # Extract decorators
            decorators = [
                self._ast_to_str(dec) for dec in node.decorator_list
            ]

            # Extract argument names
            args = []
            for arg in node.args.args:
                args.append(arg.arg)

            # Extract return annotation
            return_annotation = None
            if node.returns:
                return_annotation = self._ast_to_str(node.returns)

            # Extract docstring
            docstring = None
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring = node.body[0].value.value

            return FunctionDef(
                name=node.name,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                decorators=decorators,
                args=args,
                return_annotation=return_annotation,
                docstring=docstring,
                is_async=isinstance(node, ast.AsyncFunctionDef),
            )

        except Exception as e:
            logger.debug(f"Failed to extract function {getattr(node, 'name', '?')}: {e}")
            return None

    def _extract_class(self, node: ast.ClassDef) -> Optional[ClassDef]:
        """Extract class definition from AST node.

        Args:
            node: AST ClassDef node.

        Returns:
            ClassDef or None if extraction failed.
        """
        try:
            # Extract base class names
            bases = [self._ast_to_str(base) for base in node.bases]

            # Extract decorators
            decorators = [
                self._ast_to_str(dec) for dec in node.decorator_list
            ]

            # Extract docstring
            docstring = None
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring = node.body[0].value.value

            # Extract methods
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(
                    item, ast.AsyncFunctionDef
                ):
                    method = self._extract_function(item)
                    if method:
                        method.parent = node.name
                        methods.append(method)

            # Extract class attributes
            attributes = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    attributes.append(item.target.id)

            return ClassDef(
                name=node.name,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                bases=bases,
                decorators=decorators,
                docstring=docstring,
                methods=methods,
                attributes=attributes,
            )

        except Exception as e:
            logger.debug(f"Failed to extract class {getattr(node, 'name', '?')}: {e}")
            return None

    def _extract_imports(self, node: ast.Import | ast.ImportFrom) -> List[ImportDef]:
        """Extract import statements from AST node.

        Args:
            node: AST Import or ImportFrom node.

        Returns:
            List of ImportDef.
        """
        imports = []

        try:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportDef(
                            module_name=alias.name,
                            is_relative=False,
                            line_num=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                is_relative = node.level > 0

                for alias in node.names:
                    imports.append(
                        ImportDef(
                            module_name=module_name,
                            is_relative=is_relative,
                            names=[alias.name],
                            line_num=node.lineno,
                        )
                    )

        except Exception as e:
            logger.debug(f"Failed to extract imports: {e}")

        return imports

    def _extract_assignment(
        self, node: ast.Assign | ast.AnnAssign
    ) -> Optional[AssignmentDef]:
        """Extract assignment from AST node.

        Args:
            node: AST Assign or AnnAssign node.

        Returns:
            AssignmentDef or None if extraction failed.
        """
        try:
            if isinstance(node, ast.Assign):
                # Handle multiple targets (e.g., a = b = c)
                if node.targets and isinstance(node.targets[0], ast.Name):
                    target_name = node.targets[0].id
                    value_str = self._ast_to_str(node.value) if node.value else None

                    return AssignmentDef(
                        target_name=target_name,
                        line_num=node.lineno,
                        value=value_str,
                    )

            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    annotation_str = (
                        self._ast_to_str(node.annotation)
                        if node.annotation
                        else None
                    )
                    value_str = self._ast_to_str(node.value) if node.value else None

                    return AssignmentDef(
                        target_name=node.target.id,
                        line_num=node.lineno,
                        annotation=annotation_str,
                        value=value_str,
                    )

        except Exception as e:
            logger.debug(f"Failed to extract assignment: {e}")

        return None

    @staticmethod
    def _ast_to_str(node: ast.AST) -> str:
        """Convert AST node to string representation.

        Args:
            node: AST node.

        Returns:
            String representation of node.
        """
        try:
            return ast.unparse(node)
        except Exception:
            # Fallback for nodes that can't be unparsed
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Constant):
                return repr(node.value)
            elif isinstance(node, ast.Attribute):
                return f"{PythonASTParser._ast_to_str(node.value)}.{node.attr}"
            else:
                return type(node).__name__
