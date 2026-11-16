"""Failed/missing producers cannot masquerade as publishable artifacts."""

from pathlib import Path

from cogant.api.bundle import Bundle, StageOutcome
from cogant.api.pipeline import PipelineConfig, PipelineRunner


def test_missing_ingest_captures_failure_and_refuses_export(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "work.py").write_text("def work():\n    return 1\n", encoding="utf-8")
    out = tmp_path / "out"
    result = PipelineRunner().run(
        str(repo), PipelineConfig(stages=["static", "export"], output_dir=str(out))
    )
    assert result.pipeline_status is StageOutcome.FAILED
    assert result.stage_outcomes == {"static": StageOutcome.FAILED, "export": StageOutcome.FAILED}
    assert any("ingest stage must run before static" in error for error in result.errors)
    assert not out.exists()
    assert result.metadata["artifact_manifest"]["pipeline_status"] == "failed"


def test_supplied_dynamic_data_requires_a_graph(tmp_path: Path):
    (tmp_path / "trace.json").write_text('{"traceEvents": []}', encoding="utf-8")
    result = PipelineRunner().run(
        str(tmp_path),
        PipelineConfig(stages=["dynamic"], trace_path=str(tmp_path / "trace.json")),
    )
    assert result.stage_outcomes["dynamic"] is StageOutcome.FAILED
    assert any("_program_graph" in error for error in result.errors)


def test_valid_partial_plan_exports_its_actual_graph_without_other_models(tmp_path: Path):
    (tmp_path / "work.py").write_text("def work():\n    return 1\n", encoding="utf-8")
    out = tmp_path / "out"
    result = PipelineRunner().run(
        str(tmp_path),
        PipelineConfig(
            stages=["ingest", "graph", "export"],
            output_dir=str(out),
            render_visualizations=False,
        ),
    )
    assert result.errors == []
    assert result.pipeline_status is StageOutcome.SUCCESS
    assert (out / "program_graph.json").is_file()
    assert not (out / "gnn_package").exists()


def test_explicit_upstream_validation_cannot_skip_missing_package(tmp_path: Path):
    (tmp_path / "work.py").write_text("def work():\n    return 1\n", encoding="utf-8")
    result = PipelineRunner().run(
        str(tmp_path),
        PipelineConfig(stages=["ingest", "graph", "validate"], upstream_gnn_validation=True),
    )
    assert result.stage_outcomes["validate"] is StageOutcome.FAILED
    assert any("_gnn_package_dir" in error for error in result.errors)


def test_bundle_errors_dominate_even_successful_or_missing_outcomes():
    result = Bundle(target="local", errors=["producer failed"])
    assert result.pipeline_status is StageOutcome.FAILED
    result.stage_outcomes["ingest"] = StageOutcome.SUCCESS
    assert result.pipeline_status is StageOutcome.FAILED
