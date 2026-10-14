"""Behavior tests for ``examples/run_diff.py`` (drift-report example)."""

from __future__ import annotations

import ast
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
_RUN_DIFF = _EXAMPLES / "run_diff.py"


def _load_run_diff() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_diff_under_test", _RUN_DIFF)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _methods_by_class(tree: ast.Module) -> dict[str, list[str]]:
    return {
        node.name: [f.name for f in node.body if isinstance(f, ast.FunctionDef)]
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def test_modify_codebase_adds_a_method_and_keeps_the_source_valid(tmp_path: Path) -> None:
    repo = tmp_path / "flask_mini"
    shutil.copytree(_EXAMPLES / "control_positive" / "flask_mini", repo)
    before = {p: p.read_text(encoding="utf-8") for p in repo.rglob("*.py")}

    _load_run_diff().modify_codebase(repo)

    changed = [p for p in before if p.read_text(encoding="utf-8") != before[p]]
    assert len(changed) == 1
    tree = ast.parse(changed[0].read_text(encoding="utf-8"))  # must stay valid Python
    old_methods = _methods_by_class(ast.parse(before[changed[0]]))
    new_methods = _methods_by_class(tree)
    grown = {
        cls: set(new_methods[cls]) - set(old_methods.get(cls, []))
        for cls in new_methods
        if set(new_methods[cls]) != set(old_methods.get(cls, []))
    }
    assert grown == {next(iter(grown)): {"new_method_added"}}
    # Every pre-existing method keeps its body.
    for cls, methods in old_methods.items():
        assert set(methods) <= set(new_methods[cls])


def test_run_diff_script_can_import_the_roundtrip_orchestrator(tmp_path: Path) -> None:
    # ``python examples/run_diff.py`` puts only ``examples/`` on sys.path, not
    # the package root that ``examples.orchestrate_roundtrip`` resolves from.
    # ``-I`` keeps the cwd off sys.path, mirroring a script launched from
    # anywhere.
    probe = (
        "import runpy, sys\n"
        f"sys.path.insert(0, {str(_EXAMPLES)!r})\n"
        f"runpy.run_path({str(_RUN_DIFF)!r}, run_name='run_diff_probe')\n"
        "from examples.orchestrate_roundtrip import RoundtripOrchestrator\n"
        "print(RoundtripOrchestrator.__name__)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-I", "-c", probe],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip().endswith("RoundtripOrchestrator")


def test_run_diff_main_exits_non_zero_when_the_orchestrator_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_run_diff()
    monkeypatch.setattr(module, "run_orchestrator", lambda *_args: False)

    # ``SystemExit(None)`` exits 0, so ``None`` counts as success here.
    assert module.main() not in (0, None)


@pytest.mark.parametrize("indent", ["    ", "  "])
def test_modify_codebase_matches_the_class_indentation(tmp_path: Path, indent: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = (
        "class Counter:\n"
        f"{indent}def bump(self):\n"
        f"{indent}{indent}return 1\n"
        "\n"
        "\n"
        "def helper():\n"
        f"{indent}return 2\n"
    )
    (repo / "counter.py").write_text(source, encoding="utf-8")

    _load_run_diff().modify_codebase(repo)

    tree = ast.parse((repo / "counter.py").read_text(encoding="utf-8"))
    assert _methods_by_class(tree) == {"Counter": ["bump", "new_method_added"]}
