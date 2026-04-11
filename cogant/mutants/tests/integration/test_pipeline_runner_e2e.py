"""End-to-end tests for PipelineRunner on a tiny fixture repository."""

from pathlib import Path

import pytest

from cogant.api.pipeline import PipelineConfig, PipelineRunner


@pytest.mark.integration
def test_pipeline_runner_produces_graph(tmp_path: Path) -> None:
    repo = tmp_path / "mini"
    pkg = repo / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""pkg."""\n', encoding="utf-8")
    (pkg / "mod.py").write_text(
        "def hello():\n    return 1\n\nclass C:\n    def m(self):\n        return 2\n",
        encoding="utf-8",
    )

    cfg = PipelineConfig(output_dir=str(tmp_path / "out"), verbose=False)
    runner = PipelineRunner()
    bundle = runner.run(str(repo), cfg)

    assert bundle.errors == []
    graph = bundle.stage_results.get("graph", {})
    stats = graph.get("statistics", {})
    assert stats.get("total_nodes", 0) >= 1
    assert bundle.stage_results.get("ingest", {}).get("file_count", 0) >= 1
