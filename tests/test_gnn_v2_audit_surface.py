"""Tests for the GNN v2 audit-surface helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "tools" / "gnn_v2_audit_surface.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("gnn_v2_audit_surface", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_fixture_audit_dir(tmp_path: Path) -> Path:
    audit = tmp_path / "audit"
    upstream = audit / "upstream_full_after_A_patch"
    (upstream / "2_tests_output").mkdir(parents=True)
    (upstream / "11_render_output").mkdir(parents=True)
    (upstream / "12_execute_output" / "summaries").mkdir(parents=True)
    (audit / "version_probe.txt").write_text(
        "\n".join(
            [
                "head=out-of-sync",
                "origin_head=out-of-sync",
                "tag_v2_0_0=out-of-sync",
                "dist=2.0.0",
                "bridge_available=True",
                "bridge_upstream_version=1.6.0",
                "returncode=1",
                "stderr_last=ModuleNotFoundError: No module named 'gnn'",
            ]
        ),
        encoding="utf-8",
    )
    (audit / "version_probe_refreshed.txt").write_text(
        "\n".join(
            [
                "HEAD=11a89f0615f1e48ddacca58d1bcf3c5092b1b055",
                "origin_HEAD=b46076d0b02c74da596a735bf403f81575b3e05e",
                "v2.0.0_tag=11a89f0615f1e48ddacca58d1bcf3c5092b1b055",
            ]
        ),
        encoding="utf-8",
    )
    (upstream / "upstream_pipeline_summary.json").write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "step_index": 0,
                        "script": "0_template.py",
                        "status": "SUCCESS",
                        "success": True,
                    },
                    {
                        "step_index": 2,
                        "script": "2_tests.py",
                        "status": "FAILED",
                        "success": False,
                        "exit_code": 1,
                    },
                    {
                        "step_index": 11,
                        "script": "11_render.py",
                        "status": "FAILED",
                        "success": False,
                        "exit_code": 1,
                    },
                    {
                        "step_index": 12,
                        "script": "12_execute.py",
                        "status": "FAILED",
                        "success": False,
                        "exit_code": 2,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (upstream / "2_tests_output" / "pytest_reliable_output.txt").write_text(
        "ModuleNotFoundError: No module named 'scripts'",
        encoding="utf-8",
    )
    (upstream / "11_render_output" / "render_processing_summary.json").write_text(
        json.dumps(
            {
                "failed_framework_renderings": [
                    {
                        "message": (
                            "POMDP not compatible with pymdp: "
                            "Factored POMDP is missing observation modality metadata"
                        )
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (upstream / "12_execute_output" / "summaries" / "execution_summary.json").write_text(
        json.dumps({"total_scripts_found": 0}),
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
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return audit


def test_build_surface_separates_version_pass_from_upstream_failures(tmp_path: Path) -> None:
    module = _load_module()
    surface = module.build_surface(_write_fixture_audit_dir(tmp_path))

    assert surface.version_claim_pass is True
    assert surface.upstream_all_steps_pass is False
    assert surface.upstream_steps_success == 1
    assert surface.upstream_steps_failed == 3
    assert [failure.script for failure in surface.upstream_failures] == [
        "2_tests.py",
        "11_render.py",
        "12_execute.py",
    ]
    assert "missing observation modality metadata" in surface.upstream_failures[1].reason
    assert surface.supply_chain_pass is False


def test_main_writes_json_markdown_svg_and_strict_exit(tmp_path: Path) -> None:
    module = _load_module()
    audit = _write_fixture_audit_dir(tmp_path)
    output = tmp_path / "surface"

    assert module.main(["--audit-dir", str(audit), "--output-dir", str(output)]) == 0
    assert module.main(
        ["--audit-dir", str(audit), "--output-dir", str(output), "--strict-upstream"]
    ) == 1
    payload = json.loads((output / "gnn_v2_audit_surface.json").read_text(encoding="utf-8"))
    assert payload["version_claim_pass"] is True
    assert payload["upstream_all_steps_pass"] is False
    assert payload["supply_chain_pass"] is False
    assert "A high COGANT validator score is not an all-25" in (
        output / "gnn_v2_audit_surface.md"
    ).read_text(encoding="utf-8")
    svg = (output / "gnn_v2_audit_surface.svg").read_text(encoding="utf-8")
    assert "<svg" in svg
    assert "upstream steps 1/4" in svg
