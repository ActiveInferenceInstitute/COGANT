"""Tests for ``tools/audit_stage_list.py`` — the stage-list drift gate.

This suite enforces two contracts:

1. **Positive control** — the gate passes on the current tree. If a future
   doc reconstruction re-introduces a 9-stage list (missing ``dynamic``) or
   re-orders stages, the gate flips red and this test fails before the bad
   commit lands.

2. **Negative control** — the gate fails on a deliberately-corrupted
   snapshot. This proves the gate is *not* shape-blind: it isn't just
   counting tokens, it is verifying canonical order. Without this control,
   a token-counting bug ("all 10 stages present in any order") would pass
   silently and the gate would not bind truth (see PAI memory
   ``feedback-shape-tests-dont-bind-truth``).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tools" / "audit_stage_list.py"


def _run() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


def test_audit_stage_list_passes_on_current_tree() -> None:
    """The shipped tree must satisfy the drift gate.

    If this fails, a docstring or doc file has drifted away from the
    canonical ``cogant.pipeline.RUNNER_STAGES`` tuple. Read the failure
    output for ``file:line`` + diff and fix the doc, not the audit.
    """
    result = _run()
    assert result.returncode == 0, (
        f"Stage-list drift gate failed on current tree:\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "PASS" in result.stdout


def test_audit_stage_list_fails_on_corrupted_canonical(tmp_path: Path, monkeypatch) -> None:
    """Negative control: when the canonical tuple is overridden to be wrong,
    the gate must fail. This proves the gate enforces canonical order, not
    merely token presence.
    """
    # Make a minimal staging dir matching what the auditor expects.
    fake_root = tmp_path / "cogant_test"
    (fake_root / "cogant" / "py" / "cogant" / "pipeline").mkdir(parents=True)
    (fake_root / "cogant" / "docs").mkdir(parents=True)
    (fake_root / "manuscript").mkdir(parents=True)

    # Forge a pipeline package that exports a WRONG canonical tuple. The
    # audit script reads ``RUNNER_STAGES`` at import time, so we hand it a
    # tuple with two stages swapped.
    (fake_root / "cogant" / "py" / "cogant" / "__init__.py").write_text("")
    (fake_root / "cogant" / "py" / "cogant" / "pipeline" / "__init__.py").write_text(
        "RUNNER_STAGES = ('ingest', 'static', 'normalize', 'graph', 'translate',"
        " 'dynamic', 'statespace', 'process', 'export', 'validate')\n"
        "__all__ = ['RUNNER_STAGES']\n"
    )

    # Create a doc that lists the REAL canonical order. With the forged
    # canonical, this doc now diverges and must trigger a FAIL.
    real_list = (
        "Runs the full COGANT pipeline: ingest → static → normalize → graph "
        "→ dynamic → translate → statespace → process → export → validate.\n"
    )
    (fake_root / "cogant" / "docs" / "cli_reference.md").write_text(real_list)

    # Stage other auditor targets as empty so the audit doesn't trip on
    # missing-file warnings.
    for name in (
        "cogant/docs/getting-started/quickstart.md",
        "cogant/docs/faq.md",
        "cogant/py/cogant/cli/main.py",
        "cogant/py/cogant/api/README.md",
        "cogant/py/cogant/api/AGENTS.md",
        "cogant/py/cogant/gnn/AGENTS.md",
        "manuscript/03_api_and_workflows.md",
    ):
        target = fake_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("")

    # Copy the audit script into fake_root so its ``ROOT`` resolves to
    # fake_root (the script uses ``Path(__file__).resolve().parents[1]``).
    (fake_root / "tools").mkdir()
    (fake_root / "tools" / "audit_stage_list.py").write_text(AUDIT.read_text())

    result = subprocess.run(
        [sys.executable, str(fake_root / "tools" / "audit_stage_list.py")],
        capture_output=True,
        text=True,
        cwd=fake_root,
        check=False,
    )
    assert result.returncode != 0, (
        "Stage-list drift gate FAILED to detect a forged canonical mismatch — "
        "this is a regression in the gate itself, not in the docs. "
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "FAIL" in result.stdout or "drift" in result.stdout.lower()


def test_audit_stage_list_json_mode_emits_canonical_and_findings() -> None:
    """``--json`` mode must emit the canonical tuple and per-file findings;
    this is the machine-readable shape downstream tooling can consume.
    """
    result = subprocess.run(
        [sys.executable, str(AUDIT), "--json"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
    import json

    payload = json.loads(result.stdout)
    assert payload["canonical"] == [
        "ingest",
        "static",
        "normalize",
        "graph",
        "dynamic",
        "translate",
        "statespace",
        "process",
        "export",
        "validate",
    ]
    assert "findings" in payload
    assert all("status" in f for f in payload["findings"])


def test_audit_targets_include_critical_drift_loci() -> None:
    """The cli_reference, quickstart, FAQ, and translate docstring were the
    four loci that drifted on the iter-4 review (May 2026). If any future
    refactor removes one of them from ``DOC_TARGETS``, the gate would lose
    coverage of that drift class — pin them here.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        # Importing the module is sufficient — DOC_TARGETS is a module-level
        # constant. We dodge the import-once issue by inspecting the source.
        text = AUDIT.read_text()
    finally:
        sys.path.pop(0)
    for must_include in (
        "cogant/docs/cli_reference.md",
        "cogant/docs/getting-started/quickstart.md",
        "cogant/docs/faq.md",
        "cogant/py/cogant/cli/main.py",
    ):
        assert must_include in text, f"DOC_TARGETS lost coverage of {must_include}"


def test_audit_script_is_python_executable() -> None:
    """Smoke check — the audit script must remain runnable as a CLI."""
    result = subprocess.run(
        [sys.executable, str(AUDIT), "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
    assert "audit" in result.stdout.lower() or "stage" in result.stdout.lower()


def test_runner_stages_constant_is_exported_from_pipeline() -> None:
    """``cogant.pipeline.RUNNER_STAGES`` must be public and exactly 10 stages.

    This pins the constant against accidental deletion or re-naming. The
    drift gate depends on it; if someone removes ``RUNNER_STAGES`` from
    ``pipeline/__init__.py`` the gate breaks at import time, but this test
    surfaces the regression at the package level.
    """
    sys.path.insert(0, str(ROOT / "cogant" / "py"))
    try:
        # Force-reimport via importlib to avoid stale module state.
        import importlib

        import cogant.pipeline as pipeline_module

        importlib.reload(pipeline_module)
    finally:
        sys.path.pop(0)
    assert hasattr(pipeline_module, "RUNNER_STAGES")
    stages = pipeline_module.RUNNER_STAGES
    assert isinstance(stages, tuple)
    assert len(stages) == 10
    assert stages[0] == "ingest"
    assert stages[-1] == "validate"
    # Ensure all stage names are lowercase, non-empty, and unique.
    assert len(set(stages)) == 10
    assert all(isinstance(s, str) and s == s.lower() and s for s in stages)


def test_audit_excerpt_truncated_for_log_safety() -> None:
    """The CLI excerpt for a failure should not blow up to multi-kilobyte
    paragraphs in CI logs. Limit is ~240 chars per finding excerpt.
    """
    result = _run()
    for line in result.stdout.splitlines():
        if "excerpt:" in line:
            # excerpt: '...' - the quoted contents should not exceed 260 chars
            match = re.search(r"excerpt:\s*['\"](.*?)['\"]?$", line)
            if match:
                assert len(match.group(1)) <= 260
