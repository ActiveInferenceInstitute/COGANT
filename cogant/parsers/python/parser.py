"""Python language parser plugin."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from parsers._base import CogantLanguagePlugin  # noqa: E402

# Add py directory to path for imports (needed for cogant.static.parser)
_PY_ROOT = str(Path(__file__).parent.parent.parent / "py")
if _PY_ROOT not in sys.path:
    sys.path.insert(0, _PY_ROOT)

from cogant.static.parser import (  # noqa: E402
    ClassDef,
    FunctionDef,
    ImportDef,
    PythonASTParser,
    PythonModule,
)


@dataclass
class ParseResult:
    """Result from parsing a file."""

    file_path: Path
    classes: list[dict[str, Any]] = field(default_factory=list)
    functions: list[dict[str, Any]] = field(default_factory=list)
    imports: list[dict[str, Any]] = field(default_factory=list)
    assignments: list[dict[str, Any]] = field(default_factory=list)
    docstring: str | None = None
    errors: list[str] = field(default_factory=list)


class PythonLanguageParser(CogantLanguagePlugin):
    """Parser for Python source files."""

    PLUGIN_NAME = "python"
    PLUGIN_DESCRIPTION = "Python AST-based parser for extracting code structure"
    SUPPORTED_LANGUAGES = {"python"}
    SUPPORTED_EXTENSIONS = {".py", ".pyx", ".pyi"}

    def __init__(self) -> None:
        super().__init__()
        self.ast_parser = PythonASTParser()

    def parse(self, source_code: str) -> dict[str, Any]:
        """Parse Python source code and return AST.

        Args:
            source_code: Python source code as string.

        Returns:
            Dictionary representation of AST.
        """
        module = self.ast_parser.parse_string(source_code)
        return self._module_to_dict(module)

    def extract_symbols(self, ast: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract symbols from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            List of symbol dictionaries.
        """
        symbols = []

        # Extract classes
        for cls in ast.get("classes", []):
            symbols.append(
                {
                    "type": "class",
                    "name": cls["name"],
                    "line_start": cls["line_start"],
                    "line_end": cls["line_end"],
                    "bases": cls.get("bases", []),
                    "methods": [m["name"] for m in cls.get("methods", [])],
                }
            )

        # Extract functions
        for func in ast.get("functions", []):
            symbols.append(
                {
                    "type": "function",
                    "name": func["name"],
                    "line_start": func["line_start"],
                    "line_end": func["line_end"],
                    "args": func.get("args", []),
                    "parent": func.get("parent"),
                }
            )

        return symbols

    def extract_types(self, ast: dict[str, Any]) -> dict[str, Any]:
        """Extract type information from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            Type information dictionary.
        """
        types = {"classes": [], "functions": [], "variables": []}

        # Class type info
        for cls in ast.get("classes", []):
            types["classes"].append(
                {
                    "name": cls["name"],
                    "bases": cls.get("bases", []),
                    "methods": [
                        {
                            "name": m["name"],
                            "return_type": m.get("return_annotation"),
                            "args": m.get("args", []),
                        }
                        for m in cls.get("methods", [])
                    ],
                }
            )

        # Function type info
        for func in ast.get("functions", []):
            types["functions"].append(
                {
                    "name": func["name"],
                    "return_type": func.get("return_annotation"),
                    "args": func.get("args", []),
                }
            )

        # Variable type info
        for assign in ast.get("assignments", []):
            types["variables"].append(
                {
                    "name": assign["target_name"],
                    "type": assign.get("annotation"),
                    "scope": assign.get("parent_scope"),
                }
            )

        return types

    def resolve_imports(self, ast: dict[str, Any]) -> list[str]:
        """Resolve import dependencies from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            List of module names imported.
        """
        imports = []
        for imp in ast.get("imports", []):
            module_name = imp.get("module_name")
            if module_name and module_name not in imports:
                imports.append(module_name)
        return imports

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Python file and extract structure.

        Args:
            file_path: Path to Python file.

        Returns:
            ParseResult with extracted information.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        module = self.ast_parser.parse_file(file_path)
        return self._module_to_parse_result(module)

    def extract_symbols_from_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Extract symbols from a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            List of symbol dictionaries.
        """
        parse_result = self.parse_file(file_path)

        symbols = []
        for cls in parse_result.classes:
            symbols.append(
                {
                    "type": "class",
                    "name": cls["name"],
                    "line_start": cls["line_start"],
                    "line_end": cls["line_end"],
                }
            )

        for func in parse_result.functions:
            symbols.append(
                {
                    "type": "function",
                    "name": func["name"],
                    "line_start": func["line_start"],
                    "line_end": func["line_end"],
                }
            )

        return symbols

    def extract_calls(
        self,
        source_or_path: Any,
        file_path: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Extract function/method calls from a file or source string.

        Delegates to :class:`cogant.static.calls.CallGraphBuilder` and
        serializes each :class:`CallEdge` to a plain dictionary so that the
        parser layer stays decoupled from the ``static`` dataclasses.

        Accepts either a ``Path``/``str`` pointing at a Python file or a raw
        source string together with a ``file_path`` for context.

        Args:
            source_or_path: Either a ``Path``/``str`` file path or raw
                source code.
            file_path: Optional file path to use when the first argument is
                source code.

        Returns:
            List of call dictionaries. Each dict contains ``caller``,
            ``callee``, ``line``, ``is_method``, ``receiver``, ``args``, and
            ``callee_id`` keys.
        """
        from cogant.static.calls import CallEdge, CallGraphBuilder

        # Figure out whether we were handed a path or source.
        source: str | None = None
        resolved_path: Path

        if isinstance(source_or_path, (str, Path)):
            candidate = Path(source_or_path)
            # Heuristic: if the string looks like a path that exists, treat
            # it as a file; if it contains newlines or Python keywords, treat
            # it as source; otherwise fall back to path semantics.
            looks_like_source = isinstance(source_or_path, str) and (
                "\n" in source_or_path or len(source_or_path) > 260
            )
            if looks_like_source and file_path is not None:
                source = source_or_path  # type: ignore[assignment]
                resolved_path = Path(file_path)
            else:
                resolved_path = candidate
        else:
            # Unexpected type — fail soft with empty list.
            return []

        repo_root = (
            resolved_path.parent
            if resolved_path != Path(".") and resolved_path.parent != Path("")
            else Path(".")
        )
        builder = CallGraphBuilder(repo_root=repo_root)

        try:
            if source is not None:
                edges: list[CallEdge] = builder.extract_calls_from_source(source, resolved_path)
            elif resolved_path.exists():
                edges = builder.extract_calls_from_file(resolved_path)
            else:
                # Path-like string but no file — nothing to extract.
                return []
        except (OSError, SyntaxError, ValueError):
            return []

        return [
            {
                "id": edge.id,
                "caller": edge.caller_name,
                "caller_id": edge.caller_id,
                "callee": edge.callee_name,
                "callee_id": edge.callee_id,
                "line": edge.line_num,
                "is_method": edge.is_method_call,
                "receiver": edge.receiver,
                "args": edge.args,
                "source_file": str(edge.source_file),
            }
            for edge in edges
        ]

    def get_node_kinds(self) -> set[str]:
        """Get supported node kinds.

        Returns:
            Set of supported NodeKind values.
        """
        return {
            "ClassDef",
            "FunctionDef",
            "AsyncFunctionDef",
            "Import",
            "ImportFrom",
            "Assign",
            "AnnAssign",
        }

    def _module_to_dict(self, module: PythonModule) -> dict[str, Any]:
        """Convert PythonModule to dictionary.

        Args:
            module: PythonModule instance.

        Returns:
            Dictionary representation.
        """
        return {
            "file_path": str(module.file_path),
            "docstring": module.docstring,
            "classes": [self._class_to_dict(c) for c in module.classes],
            "functions": [self._function_to_dict(f) for f in module.functions],
            "imports": [self._import_to_dict(i) for i in module.imports],
            "assignments": [self._assignment_to_dict(a) for a in module.assignments],
            "errors": module.errors,
        }

    def _module_to_parse_result(self, module: PythonModule) -> ParseResult:
        """Convert PythonModule to ParseResult.

        Args:
            module: PythonModule instance.

        Returns:
            ParseResult instance.
        """
        return ParseResult(
            file_path=module.file_path,
            classes=[self._class_to_dict(c) for c in module.classes],
            functions=[self._function_to_dict(f) for f in module.functions],
            imports=[self._import_to_dict(i) for i in module.imports],
            assignments=[self._assignment_to_dict(a) for a in module.assignments],
            docstring=module.docstring,
            errors=module.errors,
        )

    def _class_to_dict(self, cls: ClassDef) -> dict[str, Any]:
        """Convert ClassDef to dictionary.

        Args:
            cls: ClassDef instance.

        Returns:
            Dictionary representation.
        """
        return {
            "name": cls.name,
            "line_start": cls.line_start,
            "line_end": cls.line_end,
            "bases": cls.bases,
            "decorators": cls.decorators,
            "docstring": cls.docstring,
            "methods": [self._function_to_dict(m) for m in cls.methods],
            "attributes": cls.attributes,
        }

    def _function_to_dict(self, func: FunctionDef) -> dict[str, Any]:
        """Convert FunctionDef to dictionary.

        Args:
            func: FunctionDef instance.

        Returns:
            Dictionary representation.
        """
        return {
            "name": func.name,
            "line_start": func.line_start,
            "line_end": func.line_end,
            "decorators": func.decorators,
            "args": func.args,
            "return_annotation": func.return_annotation,
            "docstring": func.docstring,
            "parent": func.parent,
            "is_async": func.is_async,
        }

    def _import_to_dict(self, imp: ImportDef) -> dict[str, Any]:
        """Convert ImportDef to dictionary.

        Args:
            imp: ImportDef instance.

        Returns:
            Dictionary representation.
        """
        return {
            "module_name": imp.module_name,
            "is_relative": imp.is_relative,
            "names": imp.names,
            "line_num": imp.line_num,
        }

    def _assignment_to_dict(self, assign) -> dict[str, Any]:
        """Convert AssignmentDef to dictionary.

        Args:
            assign: AssignmentDef instance.

        Returns:
            Dictionary representation.
        """
        return {
            "target_name": assign.target_name,
            "line_num": assign.line_num,
            "annotation": assign.annotation,
            "value": assign.value,
            "parent_scope": assign.parent_scope,
        }
