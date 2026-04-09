"""Symbol extraction: build symbol table with qualified names, types, and scopes."""

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogant.static.parser import (
    ClassDef,
    FunctionDef,
    PythonASTParser,
    PythonModule,
)

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Information about a code symbol."""

    id: str
    """Unique stable identifier."""

    name: str
    """Short name (e.g., 'foo')."""

    qualified_name: str
    """Fully qualified name (e.g., 'module.Class.method')."""

    kind: str
    """Symbol kind (function, class, method, variable)."""

    file_path: Path
    """Source file path."""

    line_start: int
    """Starting line number."""

    line_end: int
    """Ending line number."""

    scope: str
    """Scope context (module, class_name, function_name)."""

    parent_id: Optional[str] = None
    """ID of parent symbol if nested."""

    doc: Optional[str] = None
    """Docstring if available."""

    decorators: List[str] = field(default_factory=list)
    """List of decorators."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Language-specific metadata."""


@dataclass
class SymbolTable:
    """Collection of extracted symbols."""

    file_path: Path
    """Source file path."""

    symbols: List[SymbolInfo] = field(default_factory=list)
    """Extracted symbols."""

    errors: List[str] = field(default_factory=list)
    """Errors encountered during extraction."""


class SymbolExtractor:
    """Extract symbols from parsed Python modules."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize symbol extractor.

        Args:
            repo_root: Optional repository root for qualified name generation.
        """
        self.repo_root = Path(repo_root or "/")
        self.parser = PythonASTParser()

    def extract_from_file(self, file_path: Path) -> SymbolTable:
        """Extract symbols from a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            SymbolTable with extracted symbols.
        """
        # Parse file
        module = self.parser.parse_file(file_path)

        # Extract symbols
        return self._extract_from_module(module)

    def extract_from_source(
        self, source: str, file_path: Path
    ) -> SymbolTable:
        """Extract symbols from Python source code.

        Args:
            source: Python source code.
            file_path: Path for reference and qualified names.

        Returns:
            SymbolTable with extracted symbols.
        """
        # Parse source
        module = self.parser.parse_string(source, file_path)

        # Extract symbols
        return self._extract_from_module(module)

    def _extract_from_module(self, module: PythonModule) -> SymbolTable:
        """Extract symbols from parsed module.

        Args:
            module: Parsed Python module.

        Returns:
            SymbolTable with extracted symbols.
        """
        table = SymbolTable(file_path=module.file_path, errors=module.errors)

        # Get module qualified name
        module_qname = self._get_module_qname(module.file_path)

        # Extract module-level functions
        for func in module.functions:
            symbol = SymbolInfo(
                id=self._generate_symbol_id(module.file_path, func.name),
                name=func.name,
                qualified_name=f"{module_qname}.{func.name}",
                kind="function",
                file_path=module.file_path,
                line_start=func.line_start,
                line_end=func.line_end,
                scope="module",
                doc=func.docstring,
                decorators=func.decorators,
                metadata={
                    "is_async": func.is_async,
                    "parameters": func.args,
                    "return_annotation": func.return_annotation,
                },
            )
            table.symbols.append(symbol)

        # Extract classes and their methods
        for cls in module.classes:
            class_id = self._generate_symbol_id(module.file_path, cls.name)
            class_symbol = SymbolInfo(
                id=class_id,
                name=cls.name,
                qualified_name=f"{module_qname}.{cls.name}",
                kind="class",
                file_path=module.file_path,
                line_start=cls.line_start,
                line_end=cls.line_end,
                scope="module",
                doc=cls.docstring,
                decorators=cls.decorators,
                metadata={
                    "bases": cls.bases,
                    "attributes": cls.attributes,
                },
            )
            table.symbols.append(class_symbol)

            # Extract methods
            for method in cls.methods:
                method_id = self._generate_symbol_id(
                    module.file_path, f"{cls.name}.{method.name}"
                )
                method_symbol = SymbolInfo(
                    id=method_id,
                    name=method.name,
                    qualified_name=f"{module_qname}.{cls.name}.{method.name}",
                    kind="method",
                    file_path=module.file_path,
                    line_start=method.line_start,
                    line_end=method.line_end,
                    scope=cls.name,
                    parent_id=class_id,
                    doc=method.docstring,
                    decorators=method.decorators,
                    metadata={
                        "is_async": method.is_async,
                        "parameters": method.args,
                        "return_annotation": method.return_annotation,
                    },
                )
                table.symbols.append(method_symbol)

        # Extract module-level variables
        for assign in module.assignments:
            symbol = SymbolInfo(
                id=self._generate_symbol_id(
                    module.file_path, assign.target_name
                ),
                name=assign.target_name,
                qualified_name=f"{module_qname}.{assign.target_name}",
                kind="variable",
                file_path=module.file_path,
                line_start=assign.line_num,
                line_end=assign.line_num,
                scope="module",
                metadata={
                    "annotation": assign.annotation,
                    "value": assign.value,
                },
            )
            table.symbols.append(symbol)

        return table

    def _get_module_qname(self, file_path: Path) -> str:
        """Generate qualified name for a module.

        Args:
            file_path: Path to Python file.

        Returns:
            Qualified module name.
        """
        try:
            relative = file_path.relative_to(self.repo_root)
        except ValueError:
            # If file is not relative to repo root, use file name
            relative = file_path

        # Convert path to module name
        parts = list(relative.parts[:-1])  # Exclude filename
        parts.append(relative.stem)  # Add module name (without .py)

        # Filter out common prefixes
        parts = [p for p in parts if p not in {"src", "lib", "cogant"}]

        return ".".join(parts) if parts else relative.stem

    @staticmethod
    def _generate_symbol_id(file_path: Path, symbol_name: str) -> str:
        """Generate stable symbol ID.

        Args:
            file_path: Source file path.
            symbol_name: Symbol name or qualified name.

        Returns:
            Stable symbol ID (SHA256 hash).
        """
        # Create deterministic ID from file path and symbol name
        content = f"{file_path.resolve()}#{symbol_name}"
        hash_obj = hashlib.sha256(content.encode())
        return hash_obj.hexdigest()[:16]
