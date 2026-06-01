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


def _module_level_names(tree: ast.Module) -> set[str]:
    """Names a module exposes at top level: defs, classes, assignments, and the
    aliases it imports (re-exports count — ``module.name`` resolves them)."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def resolve_renderer(path: str) -> str:
    """Statically resolve a dotted ``module.attr`` renderer path.

    Locates the module file via :func:`importlib.util.find_spec` and confirms
    ``attr`` is defined (or re-exported) in it by parsing the source with
    :mod:`ast` — WITHOUT executing the module body. This keeps the audit free of
    the renderers' heavy runtime imports (matplotlib, the cogant package), so it
    behaves identically in every environment (CI, the coverage-instrumented
    project runner, a bare checkout). Handles ``tools`` not being an importable
    package by stripping a leading ``tools.`` (``tools/`` is on ``sys.path``).
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
    (
        "roundtrip_batch_gantt caption: dark diamond markers mark validate/roundtrip gates",
        "tools/manuscript_figures.py",
        ('marker="D"', 'gate_stages = {"validate", "roundtrip"}'),
    ),
)


def audit_encodings() -> list[str]:
    """Confirm each locked caption-encoding constant still exists in its renderer."""
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
        f"{len(_ENCODING_ASSERTIONS)} caption-encoding assertion(s) checked, "
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
