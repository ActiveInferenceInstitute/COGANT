"""The perf regression harness must not time (or pass on) a failed pipeline.

``PipelineRunner.run`` records stage exceptions in ``bundle.errors`` instead
of raising, so a harness that ignores the returned bundle would measure a
broken pipeline that bails out early as a speed-up.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_HARNESS = Path(__file__).resolve().parents[2] / "benchmarks" / "bench_perf_regression.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bench_perf_regression_under_test", _HARNESS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    return repo


def test_measure_raises_when_a_pipeline_stage_fails(
    monkeypatch: pytest.MonkeyPatch, tiny_repo: Path
) -> None:
    import cogant.api.orchestration as orchestration

    harness = _load_harness()

    def broken_graph(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("graph stage exploded")

    monkeypatch.setattr(orchestration, "run_graph", broken_graph)

    with pytest.raises(RuntimeError, match="graph stage exploded"):
        harness.measure(tiny_repo, iterations=1)


def test_measure_returns_timings_for_a_healthy_pipeline(tiny_repo: Path) -> None:
    harness = _load_harness()

    result = harness.measure(tiny_repo, iterations=1)

    assert result["median_ms"] > 0
    assert len(result["samples"]) == 1
