"""Unit tests for ``tools/inject_manuscript_vars.py``.

Covers the substitute-and-write behaviour plus the new ``--strict`` gate
that flags unresolved placeholders as an error. Tests invoke the CLI as a
subprocess against a tiny synthetic METRICS.yaml in ``tmp_path`` so we
don't depend on (or clobber) the real ``cogant/evaluation/METRICS.yaml``.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

_STAGING_ROOT = Path(__file__).resolve().parents[3]
_INJECT_SCRIPT = _STAGING_ROOT / "tools" / "inject_manuscript_vars.py"


def _fake_repo(tmp_path: Path, metrics_yaml: str) -> Path:
    """Create a throwaway clone of the injector pointing at ``tmp_path/cogant``.

    Returns the path of the synthesised CLI script. The fake repo layout is::

        tmp_path/
          tools/manuscript_vars.py   (copied verbatim from real tools/)
          tools/inject_manuscript_vars.py   (real script, patched anchor)
          cogant/evaluation/METRICS.yaml
    """
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "cogant" / "evaluation").mkdir(parents=True, exist_ok=True)
    # Copy the real manuscript_vars.py so the imports inside the CLI still work.
    real_vars = (_STAGING_ROOT / "tools" / "manuscript_vars.py").read_text(encoding="utf-8")
    (tmp_path / "tools" / "manuscript_vars.py").write_text(real_vars, encoding="utf-8")
    real_inject = _INJECT_SCRIPT.read_text(encoding="utf-8")
    (tmp_path / "tools" / "inject_manuscript_vars.py").write_text(real_inject, encoding="utf-8")
    (tmp_path / "cogant" / "evaluation" / "METRICS.yaml").write_text(metrics_yaml, encoding="utf-8")
    return tmp_path / "tools" / "inject_manuscript_vars.py"


_METRICS = (
    textwrap.dedent(
        """
    schema_version: '1.0'
    package:
      name: cogant
      version: '0.6.0'
      python_min: '3.11'
    testing:
      test_count_passing: 6915
      test_count_total: 7027
      coverage_percent: 90.44
      mypy_strict_errors: 0
      ruff_violations: 0
    pipeline:
      stage_count: 10
      translation_rules: 19
    """
    ).strip()
    + "\n"
)


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_inject_substitutes_placeholders_in_place(tmp_path: Path) -> None:
    cli = _fake_repo(tmp_path, _METRICS)
    md = tmp_path / "input.md"
    md.write_text(
        "cogant v{{VERSION}} ships {{TEST_COUNT}} passing tests at {{COVERAGE_PCT}}% coverage.\n",
        encoding="utf-8",
    )
    result = _run(cli, str(md))
    assert result.returncode == 0, result.stderr
    written = md.read_text(encoding="utf-8")
    assert "0.6.0" in written
    assert "6915" in written
    assert "90.44" in written
    assert "{{" not in written


def test_inject_dry_run_does_not_modify(tmp_path: Path) -> None:
    cli = _fake_repo(tmp_path, _METRICS)
    md = tmp_path / "input.md"
    original = "cogant v{{VERSION}}.\n"
    md.write_text(original, encoding="utf-8")
    result = _run(cli, str(md), "--dry-run")
    assert result.returncode == 0, result.stderr
    assert md.read_text(encoding="utf-8") == original


def test_inject_strict_mode_fails_on_unresolved(tmp_path: Path) -> None:
    cli = _fake_repo(tmp_path, _METRICS)
    md = tmp_path / "input.md"
    md.write_text(
        "v{{VERSION}} but also {{UNREGISTERED_TOKEN}} remains\n",
        encoding="utf-8",
    )
    result = _run(cli, str(md), "--strict")
    assert result.returncode == 1
    assert "Unresolved" in result.stderr
    assert "{{UNREGISTERED_TOKEN}}" in result.stderr


def test_inject_non_strict_warns_but_succeeds(tmp_path: Path) -> None:
    cli = _fake_repo(tmp_path, _METRICS)
    md = tmp_path / "input.md"
    md.write_text(
        "v{{VERSION}} but also {{UNREGISTERED_TOKEN}} remains\n",
        encoding="utf-8",
    )
    result = _run(cli, str(md))
    # Without --strict, exit code is still 0; warning lands on stderr.
    assert result.returncode == 0
    assert "Unresolved" in result.stderr


def test_inject_report_exits_zero(tmp_path: Path) -> None:
    cli = _fake_repo(tmp_path, _METRICS)
    result = _run(cli, "--report")
    assert result.returncode == 0, result.stderr
    # Every placeholder from the fake metrics should appear in the table.
    assert "VERSION" in result.stdout
    assert "TEST_COUNT" in result.stdout


def test_inject_missing_metrics_yaml_errors_out(tmp_path: Path) -> None:
    # Build a fake tree and then delete METRICS.yaml.
    cli = _fake_repo(tmp_path, _METRICS)
    (tmp_path / "cogant" / "evaluation" / "METRICS.yaml").unlink()
    md = tmp_path / "input.md"
    md.write_text("ok\n", encoding="utf-8")
    result = _run(cli, str(md))
    assert result.returncode == 1
    assert "METRICS.yaml not found" in result.stderr


def test_inject_directory_mode_with_output_dir(tmp_path: Path) -> None:
    cli = _fake_repo(tmp_path, _METRICS)
    src_dir = tmp_path / "manuscript"
    src_dir.mkdir()
    (src_dir / "a.md").write_text("cogant v{{VERSION}}\n", encoding="utf-8")
    (src_dir / "b.md").write_text("{{TEST_COUNT}} tests\n", encoding="utf-8")
    out_dir = tmp_path / "staging"
    result = _run(cli, str(src_dir), "--all", "--output-dir", str(out_dir))
    assert result.returncode == 0, result.stderr
    assert (out_dir / "a.md").read_text(encoding="utf-8").strip() == "cogant v0.6.0"
    assert (out_dir / "b.md").read_text(encoding="utf-8").strip() == "6915 tests"
    # Originals must be untouched.
    assert "{{VERSION}}" in (src_dir / "a.md").read_text(encoding="utf-8")


def test_inject_is_idempotent(tmp_path: Path) -> None:
    cli = _fake_repo(tmp_path, _METRICS)
    md = tmp_path / "input.md"
    md.write_text("cogant v{{VERSION}}\n", encoding="utf-8")
    first = _run(cli, str(md))
    assert first.returncode == 0
    after_first = md.read_text(encoding="utf-8")
    second = _run(cli, str(md))
    assert second.returncode == 0
    assert md.read_text(encoding="utf-8") == after_first
