from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

def _write_obsolete_tree(tmp_path: Path) -> ModuleType:
    roadmap = tmp_path / "cogant" / "docs" / "roadmap"
    roadmap.mkdir(parents=True)
    todo = tmp_path / "TODO.md"
    tasks = tmp_path / "tasks.yaml"
    (roadmap / "current_version.md").write_text(
        "## Current validated baseline\nCurrent page only.\n",
        encoding="utf-8",
    )
    (roadmap / "cogant_benchmarks.md").write_text(
        "## COGANT Benchmarks\nCurrent numbers come from run_manifest.json and METRICS.yaml.\n",
        encoding="utf-8",
    )
    (roadmap / "feature_backlog.md").write_text(
        "### R2. Keep roadmap version docs aligned with release history and evidence\n",
        encoding="utf-8",
    )
    todo.write_text(
        "\n".join(
            [
                "## Current Sequence",
                "1. Refactor-first maintainability tranche",
                "2. roadmap truth audit",
                "3. tools/manuscript_figures.py",
                "4. viz/inspection_dashboard.py",
            ]
        ),
        encoding="utf-8",
    )
    tasks.write_text(
        "\n".join(
            [
                "- id: cog-8",
                "  title: Roadmap truth audit + current benchmark cleanup",
                "- id: cog-9",
                "  title: Refactor manuscript figure and inspection dashboard modules",
                "- id: cog-m1",
                "  deps:",
                "  - cog-6",
                "  - cog-7",
                "  - cog-8",
                "  - cog-9",
            ]
        ),
        encoding="utf-8",
    )
    tools = tmp_path / "tools"
    tools.mkdir()
    script = tools / "audit_roadmap_truth.py"
    shutil.copyfile(TOOLS / script.name, script)
    spec = importlib.util.spec_from_file_location("isolated_roadmap_audit", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_audit_roadmap_truth_rejects_obsolete_tranche(tmp_path: Path) -> None:
    art = _write_obsolete_tree(tmp_path)

    findings = art.audit()
    assert any("current sequence missing 'cog-p5-01'" in item for item in findings)
    assert any("dependency missing cog-p4-01" in item for item in findings)


def _write_current_tree(tmp_path: Path) -> ModuleType:
    art = _write_obsolete_tree(tmp_path)
    for name in ("TODO.md", "tasks.yaml"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    return art


def test_current_coordination_passes(tmp_path: Path) -> None:
    assert _write_current_tree(tmp_path).audit() == []


@pytest.mark.parametrize("marker", ["cog-p0-01", "cog-p1-01", "cog-p2-01", "cog-p3-01", "cog-p5-01"])
def test_missing_current_marker_fails(tmp_path: Path, marker: str) -> None:
    art = _write_current_tree(tmp_path)
    art.TODO_PATH.write_text(art.TODO_PATH.read_text().replace(marker, "removed-task"))
    assert f"TODO.md: current sequence missing {marker!r}" in art.audit()


@pytest.mark.parametrize("blocker", ["cog-p0", "cog-p1-03", "cog-p2-03", "cog-p3-04", "cog-p4-01"])
def test_missing_current_release_dependency_fails(tmp_path: Path, blocker: str) -> None:
    art = _write_current_tree(tmp_path)
    art.TASKS_PATH.write_text(
        art.TASKS_PATH.read_text().replace(f"  - {blocker}\n", "  - removed-task\n")
    )
    assert f"tasks.yaml: release milestone dependency missing {blocker}" in art.audit()


def test_audit_roadmap_truth_rejects_removed_current_and_benchmark_claims(
    tmp_path: Path,
) -> None:
    art = _write_current_tree(tmp_path)
    (art.ROADMAP_DIR / "version_010_current.md").write_text(
        "## Version 0" + ".1.0 (current)\n",
        encoding="utf-8",
    )
    (art.ROADMAP_DIR / "cogant_benchmarks.md").write_text(
        "Stage latency for the nine pipeline stages. All three achieve **100% GNN validation score** and emit **111 files**.\n",
        encoding="utf-8",
    )

    findings = art.audit()

    assert any("current version" in finding for finding in findings)
    assert any("nine-stage" in finding for finding in findings)
    assert any("perfect validation" in finding for finding in findings)
    assert any("artifact counts" in finding for finding in findings)


def test_audit_roadmap_truth_rejects_todo_task_drift(tmp_path: Path) -> None:
    art = _write_current_tree(tmp_path)
    art.TODO_PATH.write_text("## Current Sequence\n1. Feature-first expansion\n", encoding="utf-8")
    art.TASKS_PATH.write_text(
        "- id: cog-m1\n  deps:\n  - cog-5\n",
        encoding="utf-8",
    )

    findings = art.audit()

    assert any("TODO.md" in finding for finding in findings)
    assert any("tasks.yaml" in finding for finding in findings)
