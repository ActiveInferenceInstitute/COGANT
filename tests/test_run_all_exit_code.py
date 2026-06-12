"""Regression guard for run_all.py batch exit-code propagation.

Before this guard, ``run_all.main()`` ended with an unconditional
``return 0``: a sweep where every target failed still exited 0 unless
``--fail-fast`` was passed, so CI and ``run.sh`` callers could not detect a
failed batch from the process exit code. The fix hoists ``failures`` above
the ``try`` block and returns ``1 if failures else 0``.

No mocks: the success path is exercised via a real subprocess; the fix
itself is pinned by parsing the actual ``run_all.py`` source AST.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

RUN_ALL = Path(__file__).resolve().parent.parent / "run_all.py"
ROOT = RUN_ALL.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_all_runner  # noqa: E402


def test_run_all_py_exists_and_parses() -> None:
    source = RUN_ALL.read_text(encoding="utf-8")
    ast.parse(source)  # raises SyntaxError on a broken edit


def test_dry_run_success_path_returns_zero() -> None:
    """The success path must still exit 0 after the exit-code change."""
    proc = subprocess.run(
        [sys.executable, str(RUN_ALL), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(RUN_ALL.parent),
    )
    assert proc.returncode == 0, (
        f"dry-run regressed: rc={proc.returncode}\n"
        f"stdout tail:\n{proc.stdout[-800:]}\n"
        f"stderr tail:\n{proc.stderr[-800:]}"
    )


def test_print_default_config_returns_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUN_ALL), "--print-default-config"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(RUN_ALL.parent),
    )
    assert proc.returncode == 0
    assert proc.stdout.strip().startswith("{")


def test_target_roundtrip_threshold_is_forwarded() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUN_ALL), "--dry-run", "--targets", "zoo_13_js_observer"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(RUN_ALL.parent),
    )
    assert proc.returncode == 0
    assert "roundtrip_threshold" not in proc.stdout
    assert "--threshold 0.0" in proc.stdout


def _main_func(source: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError("run_all.py has no top-level main()")


def test_main_final_return_is_failure_aware() -> None:
    """Pin the C1 fix: the last statement of main() must return nonzero
    when ``failures`` is non-empty (``return 1 if failures else 0``)."""
    main = _main_func(RUN_ALL.read_text(encoding="utf-8"))
    last = main.body[-1]
    assert isinstance(last, ast.Return), "main() must end with a return"
    expr = last.value
    assert isinstance(expr, ast.IfExp), (
        "main() final return must be a conditional on failures, "
        "not an unconditional constant (C1 regression)"
    )
    # condition references the `failures` name
    cond_names = {n.id for n in ast.walk(expr.test) if isinstance(n, ast.Name)}
    assert "failures" in cond_names
    # truthy branch is a nonzero int, falsy branch is 0
    assert isinstance(expr.body, ast.Constant) and expr.body.value == 1
    assert isinstance(expr.orelse, ast.Constant) and expr.orelse.value == 0


def test_failures_is_hoisted_before_try() -> None:
    """`failures` must be bound before the try block so the post-finally
    return can reference it on every non-early-return path (and so mypy
    strict does not see a possibly-unbound name)."""
    main = _main_func(RUN_ALL.read_text(encoding="utf-8"))
    saw_failures_assign = False
    for stmt in main.body:
        if isinstance(stmt, ast.Try):
            assert saw_failures_assign, (
                "`failures` must be assigned before the try block (C1 fix)"
            )
            return
        targets: list[ast.expr] = []
        if isinstance(stmt, ast.AnnAssign):
            targets = [stmt.target]
        elif isinstance(stmt, ast.Assign):
            targets = stmt.targets
        for t in targets:
            if isinstance(t, ast.Name) and t.id == "failures":
                saw_failures_assign = True
    raise AssertionError("no try block found in main()")


def test_cross_target_summary_invalid_package_is_fatal(tmp_path) -> None:
    """Fresh summary validation failures must propagate to the batch exit path."""
    run_dir = tmp_path / "out" / "bad_target"
    (run_dir / "data").mkdir(parents=True)
    (run_dir / "gnn_package").mkdir()
    (run_dir / "data" / "bundle.json").write_text(
        '{"stage_results": {"validate": {"gnn_validation": {"score": 100, "valid": true}}}}',
        encoding="utf-8",
    )
    manifest = {
        "summary": {"failed_steps": [], "total_wall_time_s": 0.1},
        "targets": [{"id": "bad_target", "run_dir": str(run_dir), "path": "demo"}],
    }

    failures = run_all_runner._write_cross_target_summary(
        tmp_path / "out",
        manifest,
        package_root=ROOT / "cogant",
        log_fp=sys.stdout,
    )

    assert failures == ["summary_validate:bad_target"]
    summary = (tmp_path / "out" / "summary.json").read_text(encoding="utf-8")
    assert "summary_validate:bad_target" in summary
