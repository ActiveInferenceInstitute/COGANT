"""Tests for the GNN upstream audit-surface helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "tools" / "gnn_upstream_audit_surface.py"

PIN = "a" * 40
OTHER = "b" * 40
TAG_COMMIT = "c" * 40
REPO_URL = "https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation.git"


def _load_module():
    spec = importlib.util.spec_from_file_location("gnn_upstream_audit_surface", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_pin_sources(
    tmp_path: Path,
    *,
    pin: str = PIN,
    lock_commit: str = PIN,
    version: str = "4.1.0",
) -> tuple[Path, Path]:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "\n".join(
            [
                "[project]",
                'name = "cogant"',
                'version = "0.0.0"',
                "[project.optional-dependencies]",
                "upstream = [",
                f'    "generalized-notation-notation @ git+{REPO_URL}@{pin}",',
                "]",
                'all = ["pytest>=7.4.0"]',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    lock = tmp_path / "uv.lock"
    lock.write_text(
        "\n".join(
            [
                "version = 1",
                "",
                "[[package]]",
                'name = "generalized-notation-notation"',
                f'version = "{version}"',
                f'source = {{ git = "{REPO_URL}?rev={lock_commit}#{lock_commit}" }}',
                "",
                "[[package]]",
                'name = "cogant"',
                'version = "0.0.0"',
                'source = { editable = "." }',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return pyproject, lock


def _write_fixture_audit_dir(tmp_path: Path, *, installed_commit: str = PIN) -> Path:
    audit = tmp_path / "audit"
    upstream = audit / "upstream_full"
    (upstream / "6_validation_output").mkdir(parents=True)
    (upstream / "11_render_output").mkdir(parents=True)
    (audit / "version_probe.txt").write_text(
        "\n".join(
            [
                "# probe",
                "dist=4.1.0",
                "engine=4.1.0",
                f"installed_commit={installed_commit}",
                f"origin_HEAD={OTHER}",
                f"release_tag_commit={TAG_COMMIT}",
                "bridge_available=True",
                "bridge_upstream_version=4.1.0",
                "negative_control_import=src.gnn",
                "returncode=1",
                "stderr_last=ModuleNotFoundError: No module named 'src'",
            ]
        ),
        encoding="utf-8",
    )
    (upstream / "upstream_pipeline_summary.json").write_text(
        json.dumps(
            {
                "available": True,
                "executed": [0, 3, 6, 11],
                "skipped": [1, 2, 4, 5, 7, 8, 9, 10, 12],
                "upstream_status": "SUCCESS_WITH_WARNINGS",
                "steps": [
                    {
                        "step_index": 0,
                        "script": "0_template.py",
                        "status": "SUCCESS",
                        "success": True,
                        "duration_s": 1.5,
                        "exit_code": 0,
                    },
                    {
                        "step_index": 3,
                        "script": "3_gnn.py",
                        "status": "SUCCESS",
                        "success": True,
                        "duration_s": 2.0,
                        "exit_code": 0,
                    },
                    {
                        "step_index": 6,
                        "script": "6_validation.py",
                        "status": "FAILED",
                        "success": False,
                        "exit_code": 1,
                        "error": "6_validation - ERROR - undeclared variable A_m0",
                        "output_dir": "/nonexistent/moved/6_validation_output",
                    },
                    {
                        "step_index": 11,
                        "script": "11_render.py",
                        "status": "FAILED",
                        "success": False,
                        "exit_code": 1,
                        "error": "render exited 1",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (upstream / "11_render_output" / "render_processing_summary.json").write_text(
        json.dumps(
            {
                "failed_framework_renderings": [
                    {"message": "POMDP not compatible with pymdp: missing modality metadata"}
                ]
            }
        ),
        encoding="utf-8",
    )
    (audit / "single_file_validation.json").write_text(
        json.dumps(
            {
                "results": [
                    {
                        "validator": "cogant GNNValidator",
                        "level": "package",
                        "ok": True,
                        "errors": [],
                        "detail": "score 100.0/100",
                    },
                    {
                        "validator": "upstream validate_gnn_syntax",
                        "level": "standard",
                        "ok": True,
                        "available": True,
                        "errors": [],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (audit / "pip_audit_path.json").write_text(
        json.dumps(
            {
                "dependencies": [
                    {
                        "name": "urllib3",
                        "version": "2.6.3",
                        "vulns": [{"id": "PYSEC-2026-142"}],
                    },
                    {"name": "numpy", "version": "2.3.0", "vulns": []},
                ]
            }
        ),
        encoding="utf-8",
    )
    return audit


@pytest.fixture()
def module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Module whose default pin/lock sources are tmp copies (never the live repo)."""
    loaded = _load_module()
    pyproject, lock = _write_pin_sources(tmp_path)
    monkeypatch.setattr(loaded, "PYPROJECT_PATH", pyproject)
    monkeypatch.setattr(loaded, "LOCK_PATH", lock)
    return loaded


def test_expectation_is_derived_from_pyproject_pin_and_uv_lock(module, tmp_path: Path) -> None:
    expectation = module.load_upstream_expectation()

    assert expectation.pinned_commit == PIN
    assert expectation.locked_commit == PIN
    assert expectation.locked_version == "4.1.0"
    assert expectation.lock_matches_pin is True
    assert expectation.release_tag == "v4.1.0"
    assert expectation.repository_url == REPO_URL

    other = tmp_path / "other"
    other.mkdir()
    pyproject, lock = _write_pin_sources(other, pin=OTHER, lock_commit=OTHER, version="5.0.1")
    moved = module.load_upstream_expectation(pyproject, lock)
    assert (moved.pinned_commit, moved.locked_version, moved.release_tag) == (
        OTHER,
        "5.0.1",
        "v5.0.1",
    )


def test_live_repository_pin_matches_its_lock() -> None:
    expectation = _load_module().load_upstream_expectation()

    assert expectation.pinned_commit is not None
    assert expectation.lock_matches_pin is True
    assert expectation.locked_version


def test_lock_entry_for_a_different_commit_fails_the_version_claim(module, tmp_path: Path) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    drifted = tmp_path / "drifted"
    drifted.mkdir()
    pyproject, lock = _write_pin_sources(drifted, pin=PIN, lock_commit=OTHER)

    expectation = module.load_upstream_expectation(pyproject, lock)
    surface = module.build_surface(audit, expectation)

    assert expectation.lock_matches_pin is False
    assert surface.upstream_commit_expected is True
    assert surface.version_claim_pass is False


def test_build_surface_separates_version_pass_from_upstream_failures(
    module, tmp_path: Path
) -> None:
    surface = module.build_surface(_write_fixture_audit_dir(tmp_path))

    assert surface.version_claim_pass is True
    assert surface.expected_commit == PIN
    assert surface.locked_version == "4.1.0"
    assert surface.release_tag == "v4.1.0"
    assert surface.release_tag_commit == TAG_COMMIT
    assert surface.origin_head == OTHER
    assert surface.upstream_summary_dir == "upstream_full"
    assert surface.upstream_all_steps_pass is False
    assert surface.upstream_steps_success == 2
    assert surface.upstream_steps_failed == 2
    assert surface.upstream_steps_skipped == (1, 2, 4, 5, 7, 8, 9, 10, 12)
    assert surface.upstream_status == "SUCCESS_WITH_WARNINGS"
    assert [failure.script for failure in surface.upstream_failures] == [
        "6_validation.py",
        "11_render.py",
    ]
    # Bridge error field is used when no step-specific artifact explains the failure.
    assert surface.upstream_failures[0].reason == "6_validation - ERROR - undeclared variable A_m0"
    # Step-specific upstream artifacts in the summary dir win over the generic error line.
    assert "missing modality metadata" in surface.upstream_failures[1].reason
    assert surface.single_file_validation_pass is True
    assert surface.supply_chain_scanned is True
    assert surface.supply_chain_pass is False


def test_installed_commit_off_the_pin_fails_the_version_claim(module, tmp_path: Path) -> None:
    surface = module.build_surface(_write_fixture_audit_dir(tmp_path, installed_commit=OTHER))

    assert surface.upstream_commit_expected is False
    assert surface.version_claim_pass is False


def test_engine_or_negative_control_mismatch_fails_the_version_claim(
    module, tmp_path: Path
) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    probe = audit / "version_probe.txt"
    text = probe.read_text(encoding="utf-8")
    probe.write_text(
        text.replace("engine=4.1.0", "engine=1.0.0").replace(
            "bridge_upstream_version=4.1.0", "bridge_upstream_version=1.0.0"
        ),
        encoding="utf-8",
    )
    assert module.build_surface(audit).version_claim_pass is False

    probe.write_text(text.replace("returncode=1", "returncode=0"), encoding="utf-8")
    surface = module.build_surface(audit)
    assert surface.raw_import_negative_control is False
    assert surface.version_claim_pass is False


def test_earlier_summary_dir_name_and_reason_files_still_resolve(module, tmp_path: Path) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    (audit / "upstream_full").rename(audit / "upstream_full_after_A_patch")
    tests_dir = audit / "upstream_full_after_A_patch" / "2_tests_output"
    tests_dir.mkdir()
    (tests_dir / "pytest_reliable_output.txt").write_text(
        "ModuleNotFoundError: No module named 'scripts'",
        encoding="utf-8",
    )
    summary_path = audit / "upstream_full_after_A_patch" / "upstream_pipeline_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["steps"].append(
        {"step_index": 2, "script": "2_tests.py", "status": "FAILED", "success": False}
    )
    summary["steps"].append(
        {"step_index": 4, "script": "4_model_registry.py", "status": "NOT_RUN", "success": False}
    )
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    surface = module.build_surface(audit)

    assert surface.upstream_summary_dir == "upstream_full_after_A_patch"
    reasons = {failure.script: failure.reason for failure in surface.upstream_failures}
    assert "missing modality metadata" in reasons["11_render.py"]
    assert "scripts.check_capability_contracts" in reasons["2_tests.py"]
    assert reasons["4_model_registry.py"] == "step absent from the upstream pipeline summary"


def test_upstream_plan_reconciles_auto_included_and_unplanned_steps(module, tmp_path: Path) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    upstream = audit / "upstream_full"
    summary_path = upstream / "upstream_pipeline_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["executed"] = [0, 3, 13, 16]
    summary["skipped"] = [11, 12]
    summary["steps"] = [
        {"step_index": 0, "script": "0_template.py", "status": "SUCCESS", "success": True},
        {"step_index": 3, "script": "3_gnn.py", "status": "SUCCESS", "success": True},
        {
            "step_index": 13,
            "script": "13_llm.py",
            "status": "NOT_RUN",
            "success": False,
            "error": "step absent from the upstream pipeline summary",
        },
        {"step_index": 16, "script": "16_analysis.py", "status": "SUCCESS", "success": True},
    ]
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    (upstream / "00_pipeline_summary").mkdir()
    (upstream / "00_pipeline_summary" / "pipeline_execution_summary.json").write_text(
        json.dumps(
            {
                "overall_status": "SUCCESS_WITH_WARNINGS",
                "arguments": {"skip_steps": "13", "skip_llm": True},
                "planned_steps": [
                    "0_template.py",
                    "3_gnn.py",
                    "11_render.py",
                    "12_execute.py",
                    "16_analysis.py",
                ],
                "steps": [
                    {"script_name": "0_template.py", "status": "SUCCESS"},
                    {"script_name": "3_gnn.py", "status": "SUCCESS"},
                    {"script_name": "11_render.py", "status": "SUCCESS", "duration_seconds": 0.9},
                    {
                        "script_name": "12_execute.py",
                        "status": "FAILED",
                        "exit_code": 1,
                        "stderr": "Traceback\nRuntimeError: pymdp runner crashed",
                    },
                    {"script_name": "16_analysis.py", "status": "SUCCESS"},
                ],
            }
        ),
        encoding="utf-8",
    )

    surface = module.build_surface(audit)

    assert surface.upstream_planned_steps == (0, 3, 11, 12, 16)
    assert [(s.step_index, s.status, s.success) for s in surface.upstream_auto_included] == [
        (11, "SUCCESS", True),
        (12, "FAILED", False),
    ]
    assert surface.upstream_auto_included[1].reason == "RuntimeError: pymdp runner crashed"
    assert surface.upstream_unplanned_steps == (13,)
    # The all-step gate covers the bridge selection only.
    assert surface.upstream_steps_total == 4
    assert [f.script for f in surface.upstream_failures] == ["13_llm.py"]
    assert surface.upstream_failures[0].reason == (
        "selected but never planned by upstream (upstream skip_steps=13, skip_llm=True)"
    )
    markdown = module.render_markdown(surface)
    assert "## Upstream Selection Reconciliation" in markdown
    assert "| 12 | `12_execute.py` | FAILED |" in markdown
    svg = module.render_svg(surface)
    assert "#9fd3b8" in svg and "#f0a8a8" in svg


def test_version_probe_records_pin_and_negative_control_round_trip(module, tmp_path: Path) -> None:
    """The probe runs the clean-interpreter negative control and round-trips."""
    expectation = module.load_upstream_expectation()
    values = module.probe_versions(expectation, ls_remote=False)

    assert values["pinned_commit"] == PIN
    assert values["locked_version"] == "4.1.0"
    assert values["release_tag"] == "v4.1.0"
    assert values["negative_control_import"] == "src.gnn"
    assert values["returncode"] == "1"
    assert "ModuleNotFoundError" in values["stderr_last"]

    probe = tmp_path / "version_probe.txt"
    module._write_probe(probe, values)
    assert module.parse_version_probe(probe) == values


def test_missing_pip_audit_is_reported_as_not_scanned(module, tmp_path: Path) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    (audit / "pip_audit_path.json").unlink()

    surface = module.build_surface(audit)

    assert surface.supply_chain_scanned is False
    assert surface.supply_chain_pass is False
    assert "Supply-chain scan: NOT SCANNED" in module.render_markdown(surface)
    assert module.main(["--audit-dir", str(audit), "--strict-supply-chain"]) == 1


def test_historical_probe_cannot_override_current_probe(module, tmp_path: Path) -> None:
    audit = _write_fixture_audit_dir(tmp_path, installed_commit=OTHER)
    (audit / "version_probe_refreshed.txt").write_text(f"installed_commit={PIN}\n")
    assert module.build_surface(audit).version_claim_pass is False


@pytest.mark.parametrize("phase", [{"ran": False}, {"ran": True, "returncode": 2}, {}])
def test_failed_collection_does_not_admit_old_scan(module, tmp_path: Path, phase) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    (audit / "pip_audit_path.json").write_text('{"dependencies": []}')
    (audit / "collect_manifest.json").write_text(
        json.dumps({"finished_at": "2026-10-15", "phases": {"pip_audit": phase}})
    )
    surface = module.build_surface(audit)
    assert not surface.supply_chain_scanned
    assert not surface.supply_chain_pass


def test_recollection_preserves_existing_evidence(module, tmp_path: Path) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    old_probe = (audit / "version_probe.txt").read_bytes()
    with pytest.raises(FileExistsError, match="empty directory"):
        module.collect_audit_dir(audit, pip_audit=False, ls_remote=False)
    assert (audit / "version_probe.txt").read_bytes() == old_probe


def test_main_writes_json_markdown_svg_and_strict_exit(module, tmp_path: Path) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    output = tmp_path / "surface"

    assert module.main(["--audit-dir", str(audit), "--output-dir", str(output)]) == 0
    assert (
        module.main(["--audit-dir", str(audit), "--output-dir", str(output), "--strict-upstream"])
        == 1
    )
    assert (
        module.main(
            ["--audit-dir", str(audit), "--output-dir", str(output), "--strict-supply-chain"]
        )
        == 1
    )
    assert (
        module.main(["--audit-dir", str(audit), "--output-dir", str(output), "--strict-version"])
        == 0
    )
    payload = json.loads((output / "gnn_upstream_audit_surface.json").read_text(encoding="utf-8"))
    assert payload["version_claim_pass"] is True
    assert payload["upstream_all_steps_pass"] is False
    assert payload["supply_chain_pass"] is False
    assert payload["release_tag"] == "v4.1.0"
    assert payload["expected_commit"] == PIN
    markdown = (output / "gnn_upstream_audit_surface.md").read_text(encoding="utf-8")
    assert markdown.startswith("# GNN Upstream Audit Surface (generalized-notation-notation 4.1.0)")
    assert "A high COGANT validator score is not an all-25" in markdown
    assert "| 6 | `6_validation.py` | FAILED |" in markdown
    svg = (output / "gnn_upstream_audit_surface.svg").read_text(encoding="utf-8")
    assert "<svg" in svg
    assert "upstream steps 2/4" in svg
    assert "generalized-notation-notation 4.1.0" in svg
    # Cells are labelled by real step index (0..12 here), with unselected steps grey.
    assert "#c9d1cb" in svg
    assert ">12</text>" in svg


def test_strict_version_fails_when_pin_moves_without_reinstall(module, tmp_path: Path) -> None:
    audit = _write_fixture_audit_dir(tmp_path)
    moved = tmp_path / "moved"
    moved.mkdir()
    pyproject, lock = _write_pin_sources(moved, pin=OTHER, lock_commit=OTHER, version="4.2.0")

    exit_code = module.main(
        [
            "--audit-dir",
            str(audit),
            "--output-dir",
            str(tmp_path / "surface"),
            "--pyproject",
            str(pyproject),
            "--lock",
            str(lock),
            "--strict-version",
        ]
    )

    assert exit_code == 1
