"""Semantic-preservation & robustness suite (TODO: robustness transforms).

For each semantics-preserving source transform, COGANT's role extraction must
be invariant: running the forward pipeline on a transformed copy of a fixture
must yield the SAME role multiset as the original. A negative control
(``drop_half_definitions``) that genuinely changes semantics must be DETECTED
by the same oracle, proving these assertions are not vacuously passing.

The oracle is ``cogant.reverse.metrics.compare_role_distributions`` — the same
similarity used by the roundtrip evaluator — so "robust to a transform" here
means exactly "the roundtrip semantic oracle sees no role drift from it".
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parents[1]  # cogant/tests
_PKG_ROOT = _TESTS_ROOT.parent  # cogant
_ROBUSTNESS = _PKG_ROOT / "evaluation" / "robustness"
for _p in (str(_PKG_ROOT / "py"), str(_ROBUSTNESS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import transforms as T  # noqa: E402

from cogant.reverse.idempotency import (  # noqa: E402
    _role_multiset_from_mappings,
    _run_forward,
)
from cogant.reverse.metrics import compare_role_distributions  # noqa: E402

_CALCULATOR = _PKG_ROOT / "examples" / "control_positive" / "calculator"
_ROBUST_THRESHOLD = 0.99


def _forward_roles(repo: Path) -> Counter:
    fwd = _run_forward(repo)
    assert not fwd.get("error"), f"forward pipeline failed on {repo}: {fwd.get('error')}"
    return _role_multiset_from_mappings(fwd.get("mappings"))


def _transformed_roles(fn) -> Counter:
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / _CALCULATOR.name
        shutil.copytree(_CALCULATOR, dst)
        for py in dst.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            py.write_text(fn(py.read_text(encoding="utf-8")), encoding="utf-8")
        return _forward_roles(dst)


@pytest.fixture(scope="module")
def base_roles() -> Counter:
    roles = _forward_roles(_CALCULATOR)
    assert roles, "calculator fixture must extract a non-empty role multiset"
    return roles


@pytest.mark.parametrize("transform_name", sorted(T.SEMANTICS_PRESERVING))
def test_semantics_preserving_transform_preserves_roles(
    transform_name: str, base_roles: Counter
) -> None:
    """Each semantics-preserving transform must leave the role multiset
    exactly unchanged (and the oracle similarity at 1.0)."""
    transformed = _transformed_roles(T.SEMANTICS_PRESERVING[transform_name])
    similarity = compare_role_distributions(base_roles, transformed)
    assert transformed == base_roles, (
        f"{transform_name} changed the role multiset: "
        f"base={dict(base_roles)} transformed={dict(transformed)}"
    )
    assert similarity == pytest.approx(1.0), (
        f"{transform_name} role-similarity {similarity:.4f} < 1.0"
    )


def test_negative_control_is_detected(base_roles: Counter) -> None:
    """The negative control genuinely changes semantics; the oracle MUST report
    role drift (else the preserving-transform assertions are vacuous)."""
    transformed = _transformed_roles(T.NEGATIVE_CONTROLS["drop_half_definitions"])
    similarity = compare_role_distributions(base_roles, transformed)
    assert transformed != base_roles, "negative control left the role multiset unchanged"
    assert similarity < _ROBUST_THRESHOLD, (
        f"negative control similarity {similarity:.4f} >= {_ROBUST_THRESHOLD} "
        "— oracle failed to detect a real semantic change (vacuous suite)"
    )


_FLASK_MINI = _PKG_ROOT / "examples" / "control_positive" / "flask_mini"


def _imports_cleanly(repo: Path) -> tuple[bool, str]:
    """Import every top-level module in ``repo`` in a subprocess. Catches
    behaviour-breaking edits that fire at definition time (decorators with
    keyword args, ``@x.setter`` ordering) which static parsing misses."""
    mods = sorted(
        p.stem for p in repo.glob("*.py")
        if p.stem != "__init__" and "__pycache__" not in p.parts
    )
    for mod in mods:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {mod}"],
            cwd=str(repo), capture_output=True, text=True, timeout=60, check=False,
        )
        if proc.returncode != 0:
            return False, proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "?"
    return True, ""


@pytest.mark.parametrize("transform_name", sorted(T.SEMANTICS_PRESERVING))
def test_semantics_preserving_transform_keeps_fixture_importable(transform_name: str) -> None:
    """A semantics-preserving transform must not break the fixture at runtime.

    Regression for the RedTeam finding that an earlier ``rename_parameters``
    renamed parameters without rewriting keyword call sites (e.g. flask_mini's
    ``@app.route('/users', method='POST')``), and ``reorder_methods`` could
    reorder ``@property``/``@x.setter`` pairs — both pass ``ast.parse`` but raise
    at import. flask_mini is the fixture that exercises a keyword-bearing
    decorator call, so the original must import and the transformed copy must too.
    """
    base_ok, _ = _imports_cleanly(_FLASK_MINI)
    assert base_ok, "flask_mini fixture must import cleanly as a baseline"
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / _FLASK_MINI.name
        shutil.copytree(_FLASK_MINI, dst)
        for py in dst.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            py.write_text(
                T.SEMANTICS_PRESERVING[transform_name](py.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
        ok, err = _imports_cleanly(dst)
    assert ok, f"{transform_name} broke flask_mini at import time: {err}"


def test_reorder_methods_preserves_property_class() -> None:
    """reorder_methods must not break a @property/@x.setter pair (which would
    raise NameError at class-definition time if the setter is moved first)."""
    src = (
        "class C:\n"
        "    def __init__(self):\n        self._v = 0\n"
        "    @property\n    def v(self):\n        return self._v\n"
        "    @v.setter\n    def v(self, x):\n        self._v = x\n"
    )
    out = T.reorder_methods(src)
    ns: dict = {}
    exec(compile(out, "<reorder-property>", "exec"), ns)  # must not raise NameError
    obj = ns["C"]()
    obj.v = 7
    assert obj.v == 7


def test_transforms_emit_valid_python() -> None:
    """Every transform (including the negative control) must emit importable
    Python on the calculator source — a transform may never inject a SyntaxError."""
    import ast

    src = (_CALCULATOR / "calculator.py").read_text(encoding="utf-8")
    for _name, fn in T.ALL_TRANSFORMS.items():
        ast.parse(fn(src))  # raises SyntaxError on regression
