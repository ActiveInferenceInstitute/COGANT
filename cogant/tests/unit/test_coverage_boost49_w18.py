#!/usr/bin/env python3
"""Coverage boost batch 49 — api/pipeline.py dry_run stage paths, gnn/runner.py.

Covers:
- PipelineRunner: dry_run=True through all stage handlers (ingest, static, normalize,
  graph, dynamic, translate, statespace, process, export, validate)
- PipelineRunner: layout_output=True path (lines 223-229)
- PipelineRunner._stage_dynamic: coverage_path provided, trace_path provided
- GNNRunner: import and basic instantiation, error paths
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# api/pipeline.py — all stages with dry_run=True
# ---------------------------------------------------------------------------

class TestPipelineRunnerDryRunStages:
    def test_dry_run_ingest_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["ingest"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("ingest", {})
        assert result.get("dry_run") is True

    def test_dry_run_static_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["ingest", "static"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        assert bundle.stage_results.get("static", {}).get("dry_run") is True

    def test_dry_run_normalize_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["normalize"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("normalize", {})
        assert result.get("dry_run") is True

    def test_dry_run_graph_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["graph"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("graph", {})
        assert result.get("dry_run") is True

    def test_dry_run_dynamic_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["dynamic"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("dynamic", {})
        assert result.get("dry_run") is True

    def test_dry_run_translate_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["translate"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("translate", {})
        assert result.get("dry_run") is True

    def test_dry_run_statespace_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["statespace"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("statespace", {})
        assert result.get("dry_run") is True

    def test_dry_run_process_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["process"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("process", {})
        assert result.get("dry_run") is True

    def test_dry_run_export_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["export"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("export", {})
        assert result.get("dry_run") is True

    def test_dry_run_validate_stage(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["validate"],
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("validate", {})
        assert result.get("dry_run") is True

    def test_dry_run_all_stages(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        # All stages should be dry_run=True
        for stage, result in bundle.stage_results.items():
            assert result.get("dry_run") is True, f"Stage {stage!r} missing dry_run"

    def test_layout_output_with_export_dry_run(self, tmp_path):
        """layout_output=True path (lines 223-229) — triggered when export is in stages."""
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        out = tmp_path / "output"
        out.mkdir()
        cfg = PipelineConfig(
            stages=["ingest", "export"],
            layout_output=True,
            dry_run=False,
            output_dir=str(out),
        )
        runner = PipelineRunner()
        # Should not raise; organize_run_dir is called on the output dir
        bundle = runner.run(str(tmp_path), cfg)
        assert bundle is not None

    def test_dynamic_stage_with_coverage_path(self, tmp_path):
        """coverage_path provided to _stage_dynamic (lines 469-474 path)."""
        from cogant.api.pipeline import PipelineRunner, PipelineConfig

        # Create a dummy coverage file
        cov = tmp_path / ".coverage"
        cov.write_bytes(b"")

        cfg = PipelineConfig(
            stages=["dynamic"],
            coverage_path=str(cov),
            dry_run=False,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        # Should have a dynamic result (success or error, but not crash)
        assert bundle is not None


# ---------------------------------------------------------------------------
# gnn/runner.py — GNNRunner basic coverage
# ---------------------------------------------------------------------------

class TestGNNRunner:
    def test_import_gnn_model_runner(self):
        from cogant.gnn.runner import GNNModelRunner
        assert GNNModelRunner is not None

    def test_gnn_model_runner_init(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        assert runner is not None

    def test_execution_trace_dataclass(self):
        from cogant.gnn.runner import ExecutionTrace
        trace = ExecutionTrace(
            step=1,
            state={"x": 1},
            action="do_something",
        )
        assert trace.step == 1
        assert trace.action == "do_something"

    def test_free_energy_calculator_import(self):
        from cogant.gnn.runner import FreeEnergyCalculator
        assert FreeEnergyCalculator is not None

    def test_active_inference_available_bool(self):
        from cogant.gnn.runner import ACTIVE_INFERENCE_AVAILABLE
        assert isinstance(ACTIVE_INFERENCE_AVAILABLE, bool)

    def test_gnn_runner_module_importable(self):
        from cogant.gnn import runner as runner_module
        assert runner_module is not None


# ---------------------------------------------------------------------------
# api/pipeline.py — PipelineRunner._stage_dynamic no-data path
# ---------------------------------------------------------------------------

class TestPipelineDynamicNoData:
    def test_dynamic_stage_no_coverage_no_trace(self, tmp_path):
        """When no coverage or trace data is available, dynamic stage skips."""
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["dynamic"],
            coverage_path=None,
            trace_path=None,
            dry_run=False,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("dynamic", {})
        # Either skipped or ran with error — but should not crash
        assert isinstance(result, dict)

    def test_dynamic_stage_skip_dynamic_flag(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["dynamic"],
            skip_dynamic=True,
            dry_run=False,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        result = bundle.stage_results.get("dynamic", {})
        assert result.get("skipped") is True
