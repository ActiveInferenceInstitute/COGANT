"""Type inference: extract type annotations and infer basic types.

This module walks Python source with the raw ``ast`` library (rather than
only the pre-parsed :class:`~cogant.static.parser.PythonModule`) so that it
can see argument annotations, class attribute annotations, and assignments
inside ``__init__``. It produces :class:`TypeInfo` records suitable for
attaching to graph nodes.

The inferencer is intentionally conservative: explicit annotations get
confidence ``1.0``, literal-based heuristics get ``0.7``, and the simple
``@property`` fallback gets ``0.6``. When no information is available the
symbol is skipped rather than being given a guessed type.
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogant.static.parser import AssignmentDef, FunctionDef, PythonASTParser
from cogant.static.symbols import SymbolExtractor

logger = logging.getLogger(__name__)


@dataclass
class TypeInfo:
    """Type information for a symbol."""

    symbol_id: str
    """Symbol ID."""

    symbol_name: str
    """Symbol name."""

    symbol_kind: str
    """Symbol kind (function, variable, parameter, attribute)."""

    inferred_type: Optional[str] = None
    """Inferred type."""

    annotation: Optional[str] = None
    """Explicit type annotation."""

    is_mutable: bool = True
    """Whether the symbol is mutable."""

    confidence: float = 0.0
    """Confidence score (0.0 to 1.0)."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional type metadata."""


class TypeInferencer:
    """Infer and extract type information from Python code."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize type inferencer.

        Args:
            repo_root: Root path of repository.
        """
        self.repo_root = Path(repo_root or "/")
        self.parser = PythonASTParser()
        self.symbol_extractor = SymbolExtractor(repo_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def infer_types_from_file(self, file_path: Path) -> List[TypeInfo]:
        """Infer types for all symbols in a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            List of TypeInfo for symbols with inferred types.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            logger.debug(f"Failed to read {file_path}: {e}")
            return []

        return self.infer_types_from_source(source, file_path)

    def infer_types_from_source(
        self, source: str, file_path: Path
    ) -> List[TypeInfo]:
        """Infer types from Python source code.

        Args:
            source: Python source code.
            file_path: Path for reference.

        Returns:
            List of TypeInfo for symbols with inferred types.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.debug(f"Syntax error in type inference for {file_path}: {e}")
            return []
        except ValueError as e:
            logger.debug(f"Parse error in type inference for {file_path}: {e}")
            return []

        try:
            symbol_table = self.symbol_extractor.extract_from_source(
                source, file_path
            )
        except (SyntaxError, ValueError) as e:
            logger.debug(f"Symbol extraction failed for {file_path}: {e}")
            symbol_table = None

        type_infos: List[TypeInfo] = []

        # Walk each top-level definition.
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                type_infos.extend(
                    self._infer_from_function(node, scope="module")
                )
            elif isinstance(node, ast.ClassDef):
                type_infos.extend(self._infer_from_class(node))
            elif isinstance(node, ast.Assign):
                info = self._infer_from_assign(node, scope="module")
                type_infos.extend(info)
            elif isinstance(node, ast.AnnAssign):
                info = self._infer_from_annassign(node, scope="module")
                if info is not None:
                    type_infos.append(info)

        # Back-fill symbol_ids from the symbol table when possible.
        if symbol_table is not None:
            self._resolve_symbol_ids(type_infos, symbol_table)

        return type_infos

    # ------------------------------------------------------------------
    # AST walkers
    # ------------------------------------------------------------------

    def _infer_from_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        scope: str,
    ) -> List[TypeInfo]:
        """Return TypeInfos for a function/method: return type and params."""
        results: List[TypeInfo] = []

        qualified = (
            node.name if scope == "module" else f"{scope}.{node.name}"
        )

        # Return annotation
        return_annotation = (
            self._annotation_to_str(node.returns) if node.returns else None
        )
        inferred_return = return_annotation
        confidence = 1.0 if return_annotation else 0.0

        if inferred_return is None:
            fallback = self._infer_return_from_body(node)
            if fallback:
                inferred_return = fallback
                confidence = 0.6

        if inferred_return is not None:
            results.append(
                TypeInfo(
                    symbol_id="",
                    symbol_name=node.name,
                    symbol_kind="method" if scope != "module" else "function",
                    inferred_type=inferred_return,
                    annotation=return_annotation,
                    confidence=confidence,
                    metadata={
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "qualified_name": qualified,
                        "scope": scope,
                        "role": "return",
                    },
                )
            )

        # Parameter annotations
        all_args: List[ast.arg] = []
        all_args.extend(node.args.args)
        all_args.extend(getattr(node.args, "kwonlyargs", []))
        all_args.extend(getattr(node.args, "posonlyargs", []))
        if node.args.vararg is not None:
            all_args.append(node.args.vararg)
        if node.args.kwarg is not None:
            all_args.append(node.args.kwarg)

        for arg in all_args:
            if arg.annotation is None:
                continue
            ann_str = self._annotation_to_str(arg.annotation)
            results.append(
                TypeInfo(
                    symbol_id="",
                    symbol_name=arg.arg,
                    symbol_kind="parameter",
                    inferred_type=ann_str,
                    annotation=ann_str,
                    confidence=1.0,
                    metadata={
                        "parent": qualified,
                        "scope": qualified,
                        "role": "parameter",
                    },
                )
            )

        return results

    def _infer_from_class(self, node: ast.ClassDef) -> List[TypeInfo]:
        """Return TypeInfos for a class body and all its methods."""
        results: List[TypeInfo] = []

        # Class-level annotated attributes (``x: int = 0``)
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                info = self._infer_from_annassign(item, scope=node.name)
                if info is not None:
                    info.symbol_kind = "attribute"
                    info.metadata["class"] = node.name
                    results.append(info)
            elif isinstance(item, ast.Assign):
                results.extend(
                    self._infer_from_assign(item, scope=node.name, kind="attribute")
                )

        # Method return types and parameters
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                results.extend(
                    self._infer_from_function(item, scope=node.name)
                )
                if item.name == "__init__":
                    results.extend(self._infer_init_attributes(item, node.name))

        return results

    def _infer_init_attributes(
        self,
        init: ast.FunctionDef | ast.AsyncFunctionDef,
        class_name: str,
    ) -> List[TypeInfo]:
        """Detect ``self.x = ...`` assignments in ``__init__``."""
        results: List[TypeInfo] = []
        for stmt in ast.walk(init):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        inferred = self._infer_literal_type(stmt.value)
                        if inferred is not None:
                            results.append(
                                TypeInfo(
                                    symbol_id="",
                                    symbol_name=target.attr,
                                    symbol_kind="attribute",
                                    inferred_type=inferred,
                                    annotation=None,
                                    confidence=0.7,
                                    metadata={
                                        "class": class_name,
                                        "scope": f"{class_name}.__init__",
                                        "source": "self-assignment",
                                    },
                                )
                            )
            elif isinstance(stmt, ast.AnnAssign):
                target = stmt.target
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    ann = self._annotation_to_str(stmt.annotation)
                    results.append(
                        TypeInfo(
                            symbol_id="",
                            symbol_name=target.attr,
                            symbol_kind="attribute",
                            inferred_type=ann,
                            annotation=ann,
                            confidence=1.0,
                            metadata={
                                "class": class_name,
                                "scope": f"{class_name}.__init__",
                                "source": "self-annotation",
                            },
                        )
                    )
        return results

    def _infer_from_assign(
        self,
        node: ast.Assign,
        scope: str,
        kind: str = "variable",
    ) -> List[TypeInfo]:
        """Handle plain ``x = value`` assignments outside of __init__."""
        results: List[TypeInfo] = []
        inferred = self._infer_literal_type(node.value)
        if inferred is None:
            return results
        for target in node.targets:
            if isinstance(target, ast.Name):
                results.append(
                    TypeInfo(
                        symbol_id="",
                        symbol_name=target.id,
                        symbol_kind=kind,
                        inferred_type=inferred,
                        annotation=None,
                        confidence=0.7,
                        metadata={
                            "scope": scope,
                            "value": self._safe_unparse(node.value),
                        },
                    )
                )
        return results

    def _infer_from_annassign(
        self, node: ast.AnnAssign, scope: str
    ) -> Optional[TypeInfo]:
        """Handle ``x: int`` or ``x: int = 5`` at module or class scope."""
        if not isinstance(node.target, ast.Name):
            return None
        ann = self._annotation_to_str(node.annotation)
        return TypeInfo(
            symbol_id="",
            symbol_name=node.target.id,
            symbol_kind="variable",
            inferred_type=ann,
            annotation=ann,
            confidence=1.0,
            metadata={
                "scope": scope,
                "has_value": node.value is not None,
                "value": self._safe_unparse(node.value) if node.value else None,
            },
        )

    # ------------------------------------------------------------------
    # Deprecated single-item helpers retained for backwards compatibility
    # ------------------------------------------------------------------

    def _infer_function_return_type(
        self, func: FunctionDef, symbol_table
    ) -> Optional[TypeInfo]:
        """Infer return type of a function from a parser FunctionDef."""
        symbol = next(
            (s for s in symbol_table.symbols if s.name == func.name), None
        )
        if symbol is None:
            return None

        annotation = func.return_annotation
        inferred_type = annotation
        confidence = 1.0 if annotation else 0.0

        if inferred_type is None and any(
            d == "property" for d in func.decorators
        ):
            inferred_type = "Any"
            confidence = 0.6

        if inferred_type is None:
            return None

        return TypeInfo(
            symbol_id=symbol.id,
            symbol_name=symbol.name,
            symbol_kind="function",
            inferred_type=inferred_type,
            annotation=annotation,
            confidence=confidence,
            metadata={"is_async": func.is_async},
        )

    def _infer_variable_type(
        self, assign: AssignmentDef, symbol_table
    ) -> Optional[TypeInfo]:
        """Infer type of a variable from a parser AssignmentDef."""
        symbol = next(
            (s for s in symbol_table.symbols if s.name == assign.target_name),
            None,
        )
        if symbol is None:
            return None

        annotation = assign.annotation
        inferred_type = annotation
        confidence = 1.0 if annotation else 0.0

        if inferred_type is None and assign.value:
            inferred_type = self._infer_type_from_value(assign.value)
            if inferred_type:
                confidence = 0.7

        if inferred_type is None:
            return None

        return TypeInfo(
            symbol_id=symbol.id,
            symbol_name=symbol.name,
            symbol_kind="variable",
            inferred_type=inferred_type,
            annotation=annotation,
            confidence=confidence,
            metadata={"value": assign.value},
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _annotation_to_str(node: Optional[ast.AST]) -> Optional[str]:
        """Convert an annotation AST node to a display string."""
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except (AttributeError, ValueError):
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Constant):
                return repr(node.value)
            return type(node).__name__

    @staticmethod
    def _safe_unparse(node: Optional[ast.AST]) -> Optional[str]:
        """Best-effort :func:`ast.unparse`."""
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except (AttributeError, ValueError):
            return None

    def _infer_return_from_body(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> Optional[str]:
        """Very simple return-type heuristic."""
        if any(
            isinstance(dec, ast.Name) and dec.id == "property"
            for dec in func.decorator_list
        ):
            return "Any"
        # Detect yield → Iterator
        for sub in ast.walk(func):
            if isinstance(sub, (ast.Yield, ast.YieldFrom)):
                return "Iterator"
        return None

    def _infer_literal_type(self, node: Optional[ast.AST]) -> Optional[str]:
        """Infer type from an AST literal expression."""
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            if node.value is None:
                return "None"
            if isinstance(node.value, bool):
                return "bool"
            if isinstance(node.value, int):
                return "int"
            if isinstance(node.value, float):
                return "float"
            if isinstance(node.value, str):
                return "str"
            if isinstance(node.value, bytes):
                return "bytes"
            return type(node.value).__name__
        if isinstance(node, ast.List):
            return "list"
        if isinstance(node, ast.Tuple):
            return "tuple"
        if isinstance(node, ast.Set):
            return "set"
        if isinstance(node, ast.Dict):
            return "dict"
        if isinstance(node, ast.Call):
            callee = self._call_name(node.func)
            if callee in {
                "list", "dict", "set", "tuple", "str",
                "int", "float", "bool", "bytes", "frozenset",
            }:
                return callee
        return None

    @staticmethod
    def _call_name(node: ast.AST) -> Optional[str]:
        """Return the name of a call callee if simple."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    @staticmethod
    def _infer_type_from_value(value: Optional[str]) -> Optional[str]:
        """Try to infer type from the string repr of an assigned value.

        Retained from the original implementation for callers using the
        parser-level :class:`AssignmentDef`.
        """
        if not value:
            return None

        value = value.strip()
        if value == "None":
            return "None"
        if value in {"True", "False"}:
            return "bool"
        if value.startswith("["):
            return "list"
        if value.startswith("{"):
            return "dict" if ":" in value else "set"
        if value.startswith("("):
            return "tuple"
        if value.startswith('"') or value.startswith("'"):
            return "str"
        if value.isdigit() or (
            len(value) > 1 and value[0] == "-" and value[1:].isdigit()
        ):
            return "int"
        if "." in value and all(c.isdigit() or c == "." or c == "-" for c in value):
            return "float"
        for ctor in (
            "dict(", "list(", "set(", "tuple(", "str(",
            "int(", "float(", "bool(",
        ):
            if value.startswith(ctor):
                return ctor[:-1]
        return None

    def _resolve_symbol_ids(
        self, infos: List[TypeInfo], symbol_table
    ) -> None:
        """Populate ``symbol_id`` from the symbol table where possible."""
        by_name: Dict[str, str] = {}
        for sym in symbol_table.symbols:
            by_name.setdefault(sym.name, sym.id)
        for info in infos:
            if not info.symbol_id and info.symbol_name in by_name:
                info.symbol_id = by_name[info.symbol_name]
