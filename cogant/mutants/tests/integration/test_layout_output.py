"""Integration tests for layout_output pipeline and Session.export_all(layout=)."""

from __future__ import annotations

from pathlib import Path

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.api.session import Session


def test_pipeline_layout_output_moves_exports(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text(
        "def hello():\n    return 1\n",
        encoding="utf-8",
    )

    out = tmp_path / "out"
    cfg = PipelineConfig(
        output_dir=str(out),
        layout_output=True,
        skip_stages=["dynamic"],
    )
    runner = PipelineRunner()
    bundle = runner.run(str(repo), cfg)
    assert not bundle.errors
    assert (out / "data" / "program_graph.json").is_file()


def test_session_export_all_layout_moves_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo2"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")

    out = tmp_path / "session_out"
    session = Session.from_target(str(repo))
    session.export_all(str(out), layout=True)

    assert (out / "data" / "program_graph.json").is_file()
