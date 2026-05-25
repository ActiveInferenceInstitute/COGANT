#!/usr/bin/env python3
"""Check that public exports keep adjacent ``.pyi`` stubs in sync.

The default pass verifies ``__all__`` name parity for public modules. A targeted
structural pass also verifies dataclass-field parity and top-level helper
signature parity for API modules whose stubs are part of the public contract.
Explicit file arguments opt those files into the structural checks too, which
keeps the audit useful for focused regression tests without turning every
legacy stub into a migration blocker.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "cogant" / "py" / "cogant"
TARGETED_STRUCTURAL_MODULES = {
    ROOT / "cogant" / "py" / "cogant" / "api" / "orchestration.py",
    ROOT / "cogant" / "py" / "cogant" / "api" / "pipeline.py",
}


def _literal_str_list(node: ast.AST) -> list[str] | None:
    if not isinstance(node, ast.List | ast.Tuple):
        return None
    values: list[str] = []
    for elt in node.elts:
        if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
            return None
        values.append(elt.value)
    return values


def _parse_ast(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise RuntimeError(f"cannot parse {path}: {exc}") from exc


def exported_names(path: Path) -> list[str]:
    tree = _parse_ast(path)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    return _literal_str_list(node.value) or []
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "__all__" and node.value is not None:
                return _literal_str_list(node.value) or []
    return []


def _top_level_declarations(
    path: Path,
) -> dict[str, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = _parse_ast(path)
    declarations: dict[str, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            declarations[node.name] = node
    return declarations


def declared_stub_names(path: Path) -> set[str]:
    tree = _parse_ast(path)
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".", 1)[0])
    return names


def _is_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
            return True
        if isinstance(decorator, ast.Call):
            wrapped = decorator.func
            if isinstance(wrapped, ast.Name) and wrapped.id == "dataclass":
                return True
            if isinstance(wrapped, ast.Attribute) and wrapped.attr == "dataclass":
                return True
    return False


def _annotation_text(node: ast.AST | None) -> str:
    if node is None:
        return ""
    return ast.unparse(node).replace(" ", "")


def _is_classvar_annotation(node: ast.AST | None) -> bool:
    text = _annotation_text(node)
    return (
        text == "ClassVar"
        or text.startswith("ClassVar[")
        or text.endswith(".ClassVar")
        or ".ClassVar[" in text
    )


def _dataclass_fields(node: ast.ClassDef) -> list[str]:
    fields: list[str] = []
    for stmt in node.body:
        if not isinstance(stmt, ast.AnnAssign):
            continue
        if not isinstance(stmt.target, ast.Name):
            continue
        if stmt.target.id.startswith("_") or _is_classvar_annotation(stmt.annotation):
            continue
        fields.append(stmt.target.id)
    return fields


def _function_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, tuple[tuple[str, str, str, bool], ...], str]:
    args = node.args
    positional = list(args.posonlyargs) + list(args.args)
    positional_defaults = [False] * (len(positional) - len(args.defaults)) + [
        True for _ in args.defaults
    ]
    params: list[tuple[str, str, str, bool]] = []
    for index, (arg, has_default) in enumerate(zip(positional, positional_defaults)):
        kind = "posonly" if index < len(args.posonlyargs) else "pos"
        params.append((kind, arg.arg, _annotation_text(arg.annotation), has_default))
    if args.vararg is not None:
        params.append(("vararg", args.vararg.arg, _annotation_text(args.vararg.annotation), False))
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        params.append(("kwonly", arg.arg, _annotation_text(arg.annotation), default is not None))
    if args.kwarg is not None:
        params.append(("kwarg", args.kwarg.arg, _annotation_text(args.kwarg.annotation), False))
    kind = "async" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return kind, tuple(params), _annotation_text(node.returns)


def _format_signature(sig: tuple[str, tuple[tuple[str, str, str, bool], ...], str]) -> str:
    kind, params, returns = sig
    parts = []
    for param_kind, name, annotation, has_default in params:
        annotation_text = f": {annotation}" if annotation else ""
        default_text = "=" if has_default else ""
        parts.append(f"{param_kind} {name}{annotation_text}{default_text}")
    return f"{kind}({', '.join(parts)}) -> {returns or 'Any'}"


def _should_check_structural_parity(py_path: Path, explicit_paths: bool) -> bool:
    if explicit_paths:
        return True
    resolved_targets = {p.resolve() for p in TARGETED_STRUCTURAL_MODULES}
    return py_path.expanduser().resolve() in resolved_targets


def structural_stub_findings(py_path: Path, stub_path: Path, exports: list[str]) -> list[str]:
    """Return targeted dataclass-field and top-level-function signature drift findings."""
    rel = py_path.relative_to(ROOT) if py_path.is_relative_to(ROOT) else py_path
    impl_decls = _top_level_declarations(py_path)
    stub_decls = _top_level_declarations(stub_path)
    findings: list[str] = []
    for name in exports:
        impl = impl_decls.get(name)
        stub = stub_decls.get(name)
        if impl is None or stub is None:
            continue
        if isinstance(impl, ast.ClassDef):
            if not isinstance(stub, ast.ClassDef) or not _is_dataclass(impl):
                continue
            impl_fields = _dataclass_fields(impl)
            stub_fields = _dataclass_fields(stub)
            if impl_fields != stub_fields:
                findings.append(
                    f"{rel}: dataclass field drift for {name}: "
                    f"implementation fields={impl_fields}; stub fields={stub_fields}"
                )
            continue
        if isinstance(impl, ast.FunctionDef | ast.AsyncFunctionDef):
            if not isinstance(stub, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            impl_sig = _function_signature(impl)
            stub_sig = _function_signature(stub)
            if impl_sig != stub_sig:
                findings.append(
                    f"{rel}: signature drift for {name}: "
                    f"implementation {_format_signature(impl_sig)}; "
                    f"stub {_format_signature(stub_sig)}"
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Optional package files/directories")
    args = parser.parse_args(argv)

    roots = args.paths or [PACKAGE_ROOT]
    py_files: list[Path] = []
    for root in roots:
        root = root.expanduser().resolve()
        if root.is_file() and root.suffix == ".py":
            py_files.append(root)
        elif root.is_dir():
            py_files.extend(
                p
                for p in sorted(root.rglob("*.py"))
                if "__pycache__" not in p.parts and p.name != "__main__.py"
            )

    findings: list[str] = []
    for py_path in py_files:
        exports = exported_names(py_path)
        if not exports:
            continue
        stub_path = py_path.with_suffix(".pyi")
        rel = py_path.relative_to(ROOT) if py_path.is_relative_to(ROOT) else py_path
        if not stub_path.exists():
            findings.append(f"{rel}: module defines __all__ but has no adjacent .pyi stub")
            continue
        declared = declared_stub_names(stub_path)
        missing = sorted(name for name in exports if name not in declared)
        if missing:
            findings.append(f"{rel}: .pyi missing exported name(s): {', '.join(missing)}")
        if _should_check_structural_parity(py_path, explicit_paths=bool(args.paths)):
            findings.extend(structural_stub_findings(py_path, stub_path, exports))

    if findings:
        print("Public export/.pyi drift found:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    print("Public export/.pyi parity passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
