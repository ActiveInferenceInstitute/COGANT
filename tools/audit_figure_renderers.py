#!/usr/bin/env python3
"""Audit that every dotted renderer path in the manuscript figure registry resolves.

Guards the failure mode where a renderer is refactored into a new module
(e.g. ``cogant.viz.png_export`` -> ``cogant.viz.png``) but the registry's
``renderer`` metadata is left pointing at the old, non-existent path. That is a
silent provenance lie: a caption claims a figure was drawn by a function that no
longer exists at the stated location, and no number / crossref / citation /
module-ref audit catches it (the module-ref audit only scans backticked refs in
the manuscript prose, not the registry metadata).

A ``renderer`` value is treated as a dotted import path only when it contains no
spaces and has a ``module.attr`` shape; free-text descriptions such as
``"upstream GNN visualization pipeline"`` or ``"cogant.viz.inspection_dashboard
roundtrip renderer"`` are skipped by design.

Run from the repo (``uv run --project cogant python ../tools/audit_figure_renderers.py``)
or import :func:`audit` from the test suite.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TOOLS_ROOT = _REPO_ROOT / "tools"
_PKG_ROOT = _REPO_ROOT / "cogant" / "py"
_EVAL_FIGURES_ROOT = _REPO_ROOT / "cogant" / "evaluation" / "figures"
for _p in (str(_TOOLS_ROOT), str(_PKG_ROOT), str(_EVAL_FIGURES_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

from manuscript_figure_registry import MANUSCRIPT_FIGURES  # noqa: E402

# module.attr with at least one dot, no spaces, identifier-shaped segments.
_DOTTED = re.compile(r"^[A-Za-z_][\w.]*\.[A-Za-z_]\w*$")


def looks_like_import_path(value: str) -> bool:
    """True when ``value`` is a dotted ``module.attr`` path, not a description."""
    return " " not in value and bool(_DOTTED.match(value))


def _collect_names(body: list[ast.stmt], names: set[str]) -> None:
    """Collect names bound at module scope, recursing into control-flow blocks
    (if/try/with/for) but NOT into def/class bodies — so a symbol guarded by a
    ``try/except`` import or an ``if`` (the common optional-dependency pattern) is
    captured, while a class's methods are not mistaken for module attributes."""
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)  # named here; do not descend into its body
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.If):
            _collect_names(node.body, names)
            _collect_names(node.orelse, names)
        elif isinstance(node, ast.Try):
            _collect_names(node.body, names)
            _collect_names(node.orelse, names)
            _collect_names(node.finalbody, names)
            for handler in node.handlers:
                _collect_names(handler.body, names)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            _collect_names(node.body, names)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            _collect_names(node.body, names)
            _collect_names(node.orelse, names)


def _module_level_names(tree: ast.Module) -> set[str]:
    """Names a module exposes at module scope: defs, classes, assignments, and the
    aliases it imports (re-exports count — ``module.name`` resolves them), including
    those guarded by ``try/except`` / ``if`` (optional-dependency re-exports)."""
    names: set[str] = set()
    _collect_names(tree.body, names)
    return names


def resolve_renderer(path: str) -> str:
    """Statically resolve a dotted ``module.attr`` renderer path.

    Locates the module file via :func:`importlib.util.find_spec` and confirms
    ``attr`` is defined (or re-exported) in it by parsing the source with
    :mod:`ast` — WITHOUT executing the *leaf renderer* module body. This keeps the
    audit free of the renderers' heavy, env-sensitive runtime imports (matplotlib,
    numpy), which the cogant renderers import lazily inside their draw functions.
    Caveat: ``find_spec`` does execute the *parent packages'* ``__init__`` modules,
    so the ``cogant`` package must be importable (``cogant/py`` is placed on
    ``sys.path`` at module load); this is why the audit runs cleanly under CI, the
    coverage-instrumented project runner, and a checkout with cogant installed, but
    is not claimed to work where the package cannot be imported at all. Handles
    ``tools`` not being an importable package by stripping a leading ``tools.``
    (``tools/`` is on ``sys.path``).
    Raises ModuleNotFoundError / AttributeError / ValueError on any failure.
    Returns the normalized ``module.attr`` string on success.
    """
    module_path, _, attr = path.rpartition(".")
    if module_path == "tools":
        raise ValueError(f"renderer path names no submodule: {path!r}")
    if module_path.startswith("tools."):
        module_path = module_path[len("tools.") :]
    spec = importlib.util.find_spec(module_path)
    if spec is None or not spec.origin:
        raise ModuleNotFoundError(f"no importable module {module_path!r}")
    source = Path(spec.origin).read_text(encoding="utf-8")
    if attr not in _module_level_names(ast.parse(source)):
        raise AttributeError(f"module {module_path!r} defines/exports no {attr!r}")
    return f"{module_path}.{attr}"


# Caption-encoding claims locked to the renderer constants that back them. Path
# resolution proves the renderer exists; THIS proves the renderer still draws what
# the caption says it draws. Each entry: (caption claim, source file relative to
# repo root, required substrings). If a renderer changes a color/marker the caption
# asserts, the substring disappears and the audit fails — defending exactly the
# "a color change silently makes a caption lie" surface that motivated this tool.
_ENCODING_ASSERTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "forward_state_space_factor caption: purple=hidden state, green=observation, orange=action",
        "cogant/py/cogant/viz/png/state_space.py",
        ('"state": "#8e44ad"', '"obs": "#27ae60"', '"act": "#e67e22"'),
    ),
    (
        "forward_abcd_matrices: A/B/C/D heatmap colormaps Blues/Greens/Oranges/Purples",
        "cogant/py/cogant/viz/png/state_space.py",
        ('"Blues"', '"Greens"', '"Oranges"', '"Purples"'),
    ),
)


def _has_scatter_with_diamond(tree: ast.AST) -> bool:
    """True iff some ``scatter(...)`` call passes ``marker="D"`` — i.e. a diamond
    is drawn on the LIVE path, not merely present as a decorative legend handle."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name != "scatter":
            continue
        for kw in node.keywords:
            if kw.arg == "marker" and isinstance(kw.value, ast.Constant) and kw.value.value == "D":
                return True
    return False


def _has_gate_stage_set(tree: ast.AST) -> bool:
    """True iff a ``gate_stages = {...}`` set literal lists validate + roundtrip."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Set):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "gate_stages" for t in node.targets):
            continue
        members = {e.value for e in node.value.elts if isinstance(e, ast.Constant)}
        if {"validate", "roundtrip"} <= members:
            return True
    return False


def _gantt_diamond_marker_errors() -> list[str]:
    """AST-confirm the gantt caption claim ("dark diamond markers mark
    validate/roundtrip gates"): a ``scatter`` call must draw ``marker="D"`` and the
    gate-stage set must list validate+roundtrip. Stronger than a substring check —
    it cannot be satisfied by a diamond that survives only on a legend handle."""
    relpath = "tools/manuscript_figures.py"
    source_file = _REPO_ROOT / relpath
    if not source_file.exists():
        return [f"roundtrip_batch_gantt: renderer source missing: {relpath}"]
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not _has_scatter_with_diamond(tree):
        errors.append(
            f'roundtrip_batch_gantt caption "dark diamond markers": no '
            f'scatter(marker="D") draw call in {relpath} — the gate glyph changed'
        )
    if not _has_gate_stage_set(tree):
        errors.append(
            f'roundtrip_batch_gantt caption "validate/roundtrip gates": gate_stages '
            f"set in {relpath} no longer lists validate+roundtrip"
        )
    return errors


def audit_encodings() -> list[str]:
    """Confirm each locked caption-encoding claim still holds in its renderer.

    Color/colormap claims are checked as exact source substrings (dict/list
    literals, low ambiguity); the gantt diamond-marker claim is checked via AST
    against the actual ``scatter`` draw call (a glyph reused in a legend cannot
    satisfy it)."""
    errors: list[str] = []
    for claim, relpath, required in _ENCODING_ASSERTIONS:
        source_file = _REPO_ROOT / relpath
        if not source_file.exists():
            errors.append(f"{claim}: renderer source missing: {relpath}")
            continue
        text = source_file.read_text(encoding="utf-8")
        missing = [token for token in required if token not in text]
        if missing:
            errors.append(
                f"{claim}: {relpath} no longer contains {missing} — the renderer "
                "encoding changed; update the caption AND this assertion together"
            )
    errors.extend(_gantt_diamond_marker_errors())
    return errors


def audit() -> list[str]:
    """Return a list of human-readable errors (empty list means clean).

    Two layers: every dotted ``renderer`` path must resolve to a defined symbol,
    AND every locked caption-encoding constant must still exist in its renderer.
    """
    errors: list[str] = []
    checked = 0
    for fig in MANUSCRIPT_FIGURES:
        renderer = fig.renderer.strip()
        if not looks_like_import_path(renderer):
            continue
        checked += 1
        try:
            resolve_renderer(renderer)
        except Exception as exc:  # noqa: BLE001 - any resolution failure is a finding
            errors.append(f"{fig.key}: renderer {renderer!r} does not resolve: {exc}")
    encoding_errors = audit_encodings()
    errors.extend(encoding_errors)
    print(
        f"audit_figure_renderers: {checked} dotted renderer path(s) + "
        f"{len(_ENCODING_ASSERTIONS) + 1} caption-encoding assertion(s) checked, "
        f"{len(errors)} error(s)"
    )
    return errors


def main() -> int:
    errors = audit()
    for err in errors:
        print(f"  FAIL {err}")
    if errors:
        return 1
    print(
        "audit_figure_renderers: OK (every dotted renderer path resolves to a defined "
        "symbol; every locked caption-encoding constant is present)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
