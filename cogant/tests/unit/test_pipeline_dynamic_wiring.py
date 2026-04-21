"""Unit tests for dynamic-analysis wiring inside ``PipelineRunner``.

These tests cover three things:

1. ``PipelineConfig.skip_dynamic`` really skips the stage and records a
   skipped stage-result so downstream tooling can tell.
2. When no coverage or trace data is available, the dynamic stage runs
   to completion, reports ``skipped=True`` with a descriptive reason,
   and does not crash the pipeline.
3. When a real coverage file is provided via ``config.coverage_path``,
   the dynamic stage picks it up and records the path in its result.

All tests use real ``PipelineRunner``/``PipelineConfig`` instances and
a real on-disk fixture — no mocks, per the project testing policy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.api.pipeline import PipelineConfig, PipelineRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CALCULATOR = REPO_ROOT / "examples" / "control_positive" / "calculator"
FIXTURE_FLASK_MINI = REPO_ROOT / "examples" / "control_positive" / "flask_mini"


# ---------------------------------------------------------------------------
# skip_dynamic short-circuits the stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_skip_dynamic_records_skipped_stage_result(tmp_path):
    """``skip_dynamic=True`` skips the stage and records ``skipped=True``."""
    if not FIXTURE_CALCULATOR.exists():
        pytest.skip("calculator fixture missing")
    config = PipelineConfig(
        output_dir=str(tmp_path / "out"),
        skip_stages=["export", "validate"],
        skip_dynamic=True,
    )
    runner = PipelineRunner()
    bundle = runner.run(str(FIXTURE_CALCULATOR), config)

    assert "dynamic" in bundle.stage_results, (
        "skip_dynamic should still record a stage_result entry"
    )
    result = bundle.stage_results["dynamic"]
    assert result.get("skipped") is True
    assert result.get("reason") == "skip_dynamic=True"


@pytest.mark.unit
def test_skip_dynamic_does_not_mutate_caller_config():
    """``skip_dynamic`` must not permanently mutate caller-supplied skip lists."""
    if not FIXTURE_CALCULATOR.exists():
        pytest.skip("calculator fixture missing")
    skip = ["export", "validate"]
    config = PipelineConfig(
        skip_stages=skip,
        skip_dynamic=True,
        output_dir="/tmp/cogant-test-mutate",
    )
    runner = PipelineRunner()
    runner.run(str(FIXTURE_CALCULATOR), config)

    # The original skip_stages list should be untouched by the runner.
    assert "dynamic" not in skip, "skip_stages list provided by the caller must not be mutated"
    assert config.skip_stages == skip


@pytest.mark.unit
def test_skip_dynamic_default_is_false():
    """The opt-out flag defaults to ``False`` (dynamic stage enabled)."""
    config = PipelineConfig()
    assert config.skip_dynamic is False


# ---------------------------------------------------------------------------
# Dynamic stage is a graceful no-op when no data is present
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dynamic_stage_skips_when_no_coverage_or_trace(tmp_path):
    """Running dynamic without coverage/trace data yields a clean skip."""
    if not FIXTURE_CALCULATOR.exists():
        pytest.skip("calculator fixture missing")
    config = PipelineConfig(
        output_dir=str(tmp_path / "out"),
        skip_stages=["export", "validate"],
    )
    runner = PipelineRunner()
    bundle = runner.run(str(FIXTURE_CALCULATOR), config)

    assert "dynamic" in bundle.stage_results
    result = bundle.stage_results["dynamic"]
    assert result.get("skipped") is True, (
        "dynamic stage should report skipped=True when no data is present"
    )
    assert "no dynamic data" in result.get("reason", "")
    # Counters must default to zero even when the stage is a no-op.
    assert result.get("coverage_nodes_enriched", 0) == 0
    assert result.get("trace_nodes_enriched", 0) == 0


@pytest.mark.unit
def test_pipeline_completes_without_dynamic_errors(tmp_path):
    """The full pipeline survives a no-data dynamic stage without errors."""
    if not FIXTURE_CALCULATOR.exists():
        pytest.skip("calculator fixture missing")
    config = PipelineConfig(
        output_dir=str(tmp_path / "out"),
        skip_stages=["export", "validate"],
    )
    runner = PipelineRunner()
    bundle = runner.run(str(FIXTURE_CALCULATOR), config)

    # No error should mention the dynamic stage.
    dynamic_errors = [e for e in bundle.errors if "dynamic" in e.lower()]
    assert dynamic_errors == [], f"Unexpected dynamic errors: {dynamic_errors}"


# ---------------------------------------------------------------------------
# Explicit coverage_path is honoured
# ---------------------------------------------------------------------------


_COBERTURA_XML = """\
<?xml version="1.0" ?>
<coverage version="5.5" timestamp="1234567890"
         lines-valid="10" lines-covered="5" line-rate="0.5"
         branches-valid="0" branches-covered="0" branch-rate="0"
         complexity="0">
  <packages>
    <package name="calculator" line-rate="0.5">
      <classes>
        <class name="calculator.py" filename="calculator.py" line-rate="0.5">
          <lines>
            <line number="1" hits="1"/>
            <line number="2" hits="1"/>
            <line number="3" hits="1"/>
            <line number="5" hits="1"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


@pytest.mark.unit
def test_explicit_coverage_path_is_picked_up(tmp_path):
    """Providing ``config.coverage_path`` forwards it to the enrichment call."""
    if not FIXTURE_CALCULATOR.exists():
        pytest.skip("calculator fixture missing")
    coverage_file = tmp_path / "coverage.xml"
    coverage_file.write_text(_COBERTURA_XML)

    config = PipelineConfig(
        output_dir=str(tmp_path / "out"),
        skip_stages=["export", "validate"],
        coverage_path=str(coverage_file),
    )
    runner = PipelineRunner()
    bundle = runner.run(str(FIXTURE_CALCULATOR), config)

    result = bundle.stage_results.get("dynamic", {})
    assert result.get("skipped") is not True, (
        f"dynamic stage unexpectedly skipped with result={result}"
    )
    assert result.get("coverage_path") == str(coverage_file)
    assert "coverage_nodes_enriched" in result


@pytest.mark.unit
def test_plugins_dynamic_coverage_path_still_supported(tmp_path):
    """Legacy plugins['dynamic']['coverage_path'] is honoured too."""
    if not FIXTURE_CALCULATOR.exists():
        pytest.skip("calculator fixture missing")
    coverage_file = tmp_path / "coverage.xml"
    coverage_file.write_text(_COBERTURA_XML)

    config = PipelineConfig(
        output_dir=str(tmp_path / "out"),
        skip_stages=["export", "validate"],
        plugins={"dynamic": {"coverage_path": str(coverage_file)}},
    )
    runner = PipelineRunner()
    bundle = runner.run(str(FIXTURE_CALCULATOR), config)

    result = bundle.stage_results.get("dynamic", {})
    assert result.get("skipped") is not True, (
        f"dynamic stage unexpectedly skipped with legacy plugins config, got {result}"
    )
    assert result.get("coverage_path") == str(coverage_file)


# ---------------------------------------------------------------------------
# skip_dynamic takes precedence over any explicit paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_skip_dynamic_overrides_explicit_coverage(tmp_path):
    """``skip_dynamic=True`` trumps ``coverage_path`` for the same run."""
    if not FIXTURE_CALCULATOR.exists():
        pytest.skip("calculator fixture missing")
    coverage_file = tmp_path / "coverage.xml"
    coverage_file.write_text(_COBERTURA_XML)

    config = PipelineConfig(
        output_dir=str(tmp_path / "out"),
        skip_stages=["export", "validate"],
        skip_dynamic=True,
        coverage_path=str(coverage_file),
    )
    runner = PipelineRunner()
    bundle = runner.run(str(FIXTURE_CALCULATOR), config)

    result = bundle.stage_results["dynamic"]
    assert result.get("skipped") is True
    assert result.get("reason") == "skip_dynamic=True"
    # The coverage path must NOT have been consumed.
    assert "coverage_path" not in result
