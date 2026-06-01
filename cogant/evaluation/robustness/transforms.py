"""Semantics-preserving (and one deliberately semantics-changing) source
transforms for the COGANT robustness suite.

Each public transform takes Python source text and returns transformed source
text that is **behaviorally equivalent** (same observable semantics) but
syntactically different, exercising whether COGANT's role extraction is robust
to the kinds of edits a refactor or a different author would introduce:

* ``reformat``          — canonical AST round-trip (drops comments / whitespace),
                          i.e. parser/frontend formatting variation.
* ``insert_comments``   — comment and blank-line injection.
* ``insert_dead_code``  — unreachable ``if False:`` blocks inside each function.
* ``rename_locals``     — consistent renaming of function local variables and
                          their in-body uses (call-safe identifier renaming).
* ``reorder_methods``   — reverse method-definition order within each class
                          (definition order is semantics-irrelevant).
* ``swap_if_branches``  — rewrite ``if c: A else: B`` to ``if not c: B else: A``.
* ``outline_first_function`` — extract a function body into a nested helper and
                          call it (an *outlining* refactor that adds a node;
                          used to probe expected sensitivity, not robustness).

The suite also ships ``drop_last_method`` as a **negative control**: it removes
a method, genuinely changing semantics and the role multiset, so the
semantic-oracle test can prove it is not vacuously passing.

Every transform validates its output with :func:`ast.parse` and falls back to
the original source if it would otherwise emit invalid Python, so a transform
can never inject a syntax error into a fixture run.
"""

from __future__ import annotations

import ast


def _safe(transform):
    """Wrap a ``src -> src`` transform so invalid output falls back to input."""

    def _wrapped(src: str) -> str:
        try:
            out = transform(src)
            ast.parse(out)  # reject anything that would not import
            return out
        except SyntaxError:
            return src

    _wrapped.__name__ = getattr(transform, "__name__", "transform")
    return _wrapped


@_safe
def reformat(src: str) -> str:
    """Canonical AST round-trip: strips comments/formatting, re-emits source."""
    return ast.unparse(ast.parse(src))


@_safe
def insert_comments(src: str) -> str:
    """Prepend a banner comment and interleave blank lines + comments."""
    lines = src.splitlines()
    out = ["# robustness: comment/formatting variation (semantics-preserving)", ""]
    for i, line in enumerate(lines):
        out.append(line)
        if line.strip() and not line.lstrip().startswith("#") and i % 5 == 4:
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}# step {i}")
    return "\n".join(out) + "\n"


class _DeadCodeInserter(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        guard = ast.If(
            test=ast.Constant(value=False),
            body=[ast.Assign(
                targets=[ast.Name(id="_unreachable", ctx=ast.Store())],
                value=ast.Constant(value=0),
            )],
            orelse=[],
        )
        # Keep any leading docstring first, then the dead block.
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(
            getattr(body[0], "value", None), ast.Constant
        ):
            node.body = [body[0], guard, *body[1:]]
        else:
            node.body = [guard, *body]
        return node

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]


@_safe
def insert_dead_code(src: str) -> str:
    tree = _DeadCodeInserter().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _is_flat_scope(node: ast.AST) -> bool:
    """True if a function body introduces NO nested binding scopes (nested
    functions, classes, lambdas, or comprehensions). Renaming locals is only
    done for flat functions so a simple ``ast.walk`` cannot leak the rename into
    an inner scope with different binding rules."""
    for child in ast.walk(node):
        if child is node:
            continue
        if isinstance(child, (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
            ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
        )):
            return False
    return True


class _LocalRenamer(ast.NodeTransformer):
    """Rename a function's LOCAL VARIABLES (assigned names that are not
    parameters) and their in-body uses with a suffix.

    Local variables are never visible at call sites, so renaming them — unlike
    renaming parameters — can never break a keyword caller. This makes the
    transform a genuinely behaviour-preserving identifier rename. Functions that
    declare ``global``/``nonlocal`` or contain nested scopes (closures,
    comprehensions) are skipped to keep the rewrite provably scope-local.
    """

    _SUFFIX = "_lv"
    _SKIP = {"self", "cls"}

    def _func(self, node):
        self.generic_visit(node)
        if any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(node)):
            return node
        if not _is_flat_scope(node):
            return node
        params: set[str] = {a.arg for a in (
            *node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs
        )}
        if node.args.vararg:
            params.add(node.args.vararg.arg)
        if node.args.kwarg:
            params.add(node.args.kwarg.arg)
        locals_assigned: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                locals_assigned.add(child.id)
        rename = {
            name: name + self._SUFFIX
            for name in (locals_assigned - params - self._SKIP)
        }
        if rename:
            _RenameNames(rename).visit(node)
        return node

    visit_FunctionDef = _func
    visit_AsyncFunctionDef = _func


class _RenameNames(ast.NodeTransformer):
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if node.arg in self.mapping:
            node.arg = self.mapping[node.arg]
        return node

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node


@_safe
def rename_locals(src: str) -> str:
    tree = _LocalRenamer().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _has_decorator_coupling(node: ast.ClassDef) -> bool:
    """True if the class has decorator-coupled methods whose definition order is
    NOT free to change — e.g. ``@property`` + ``@<name>.setter``/``.getter``/
    ``.deleter``, where the setter's decorator references the property name and
    must be defined after it. Reordering such a class would raise NameError at
    class-definition time, so it is left in place.
    """
    for m in node.body:
        if not isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in m.decorator_list:
            # @x.setter / @x.getter / @x.deleter — attribute on another name.
            if isinstance(dec, ast.Attribute) and dec.attr in {"setter", "getter", "deleter"}:
                return True
    return False


class _MethodReorderer(ast.NodeTransformer):
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.generic_visit(node)
        if _has_decorator_coupling(node):
            return node  # reordering would break @property/@x.setter pairing
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if len(methods) > 1:
            rev = list(reversed(methods))
            it = iter(rev)
            node.body = [
                next(it) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) else n
                for n in node.body
            ]
        return node


@_safe
def reorder_methods(src: str) -> str:
    tree = _MethodReorderer().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


class _IfBranchSwapper(ast.NodeTransformer):
    def visit_If(self, node: ast.If) -> ast.If:
        self.generic_visit(node)
        if node.orelse and not (
            len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If)
        ):
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            node.body, node.orelse = node.orelse, node.body
        return node


@_safe
def swap_if_branches(src: str) -> str:
    tree = _IfBranchSwapper().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


class _Outliner(ast.NodeTransformer):
    """Outline the first eligible top-level function's body into a nested
    helper that is immediately called and returned — an outlining refactor
    that introduces an additional function node."""

    def __init__(self) -> None:
        self._done = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        if self._done or not node.body:
            return node
        if any(isinstance(n, (ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom))
               for n in ast.walk(node)):
            return node
        body = node.body
        doc = None
        if isinstance(body[0], ast.Expr) and isinstance(
            getattr(body[0], "value", None), ast.Constant
        ):
            doc, body = body[0], body[1:]
        if not body:
            return node
        helper = ast.FunctionDef(
            name="_outlined",
            args=ast.arguments(
                posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
                kw_defaults=[], kwarg=None, defaults=[],
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )
        call = ast.Return(value=ast.Call(
            func=ast.Name(id="_outlined", ctx=ast.Load()), args=[], keywords=[]
        ))
        node.body = ([doc] if doc else []) + [helper, call]
        self._done = True
        return node


@_safe
def outline_first_function(src: str) -> str:
    tree = _Outliner().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _drop_latter_half(defs: list) -> set[int]:
    """Indices (object ids) of the latter half of a definition list to drop."""
    if len(defs) <= 1:
        return set()
    keep = (len(defs) + 1) // 2  # keep the first half (rounded up)
    return {id(d) for d in defs[keep:]}


class _HalfDefinitionDropper(ast.NodeTransformer):
    """Remove the latter half of function/method definitions at module level
    and within each class — a decisive, semantics-changing edit that collapses
    a large fraction of the role multiset on every multi-definition fixture."""

    def _filter(self, body: list) -> list:
        defs = [n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        drop = _drop_latter_half(defs)
        return [n for n in body if id(n) not in drop]

    def visit_Module(self, node: ast.Module) -> ast.Module:
        self.generic_visit(node)
        node.body = self._filter(node.body)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.generic_visit(node)
        kept = self._filter(node.body)
        node.body = kept or [ast.Pass()]
        return node


@_safe
def drop_half_definitions(src: str) -> str:
    """NEGATIVE CONTROL — removes the latter half of functions/methods,
    genuinely changing semantics and the role multiset. Proves the semantic
    oracle is not vacuously passing on the preserving transforms."""
    tree = _HalfDefinitionDropper().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# Public registry. ``preserving`` flags whether the transform is expected to
# preserve the role multiset (the robustness claim) or not.
SEMANTICS_PRESERVING: dict[str, object] = {
    "reformat": reformat,
    "insert_comments": insert_comments,
    "insert_dead_code": insert_dead_code,
    "rename_locals": rename_locals,
    "reorder_methods": reorder_methods,
    "swap_if_branches": swap_if_branches,
}

# Outlining adds a function node; it is semantics-preserving at runtime but may
# shift the role multiset, so it is tracked separately as a sensitivity probe.
SENSITIVITY_PROBES: dict[str, object] = {
    "outline_first_function": outline_first_function,
}

# Negative control: NOT semantics-preserving.
NEGATIVE_CONTROLS: dict[str, object] = {
    "drop_half_definitions": drop_half_definitions,
}

ALL_TRANSFORMS: dict[str, object] = {
    **SEMANTICS_PRESERVING,
    **SENSITIVITY_PROBES,
    **NEGATIVE_CONTROLS,
}
