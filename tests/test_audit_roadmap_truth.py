from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import audit_roadmap_truth as art  # noqa: E402


def _write_clean_tree(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setattr(art, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(art, "ROADMAP_DIR", roadmap)
    monkeypatch.setattr(art, "TODO_PATH", todo)
    monkeypatch.setattr(art, "TASKS_PATH", tasks)


def test_audit_roadmap_truth_accepts_clean_refactor_tranche(tmp_path: Path, monkeypatch) -> None:
    _write_clean_tree(tmp_path, monkeypatch)

    assert art.audit() == []


def test_audit_roadmap_truth_rejects_removed_current_and_benchmark_claims(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_clean_tree(tmp_path, monkeypatch)
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


def test_audit_roadmap_truth_rejects_todo_task_drift(tmp_path: Path, monkeypatch) -> None:
    _write_clean_tree(tmp_path, monkeypatch)
    art.TODO_PATH.write_text("## Current Sequence\n1. Feature-first expansion\n", encoding="utf-8")
    art.TASKS_PATH.write_text(
        "- id: cog-m1\n  deps:\n  - cog-5\n",
        encoding="utf-8",
    )

    findings = art.audit()

    assert any("TODO.md" in finding for finding in findings)
    assert any("tasks.yaml" in finding for finding in findings)
