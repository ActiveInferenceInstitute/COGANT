"""Contract tests for ``evaluation/run_eval.py`` (real-world evaluation driver)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from cogant.api.bundle import ArtifactKey, Bundle
from cogant.config.pipeline import PipelineConfig

_RUN_EVAL = Path(__file__).resolve().parents[2] / "evaluation" / "run_eval.py"


def _load_run_eval() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_eval_under_test", _RUN_EVAL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _RecordingRunner:
    """Stand-in ``PipelineRunner`` that records the config it was given."""

    configs: list[PipelineConfig] = []
    bundle_factory: Any = None

    def run(self, target: str, config: PipelineConfig) -> Bundle:
        type(self).configs.append(config)
        factory = type(self).bundle_factory
        return factory(target) if factory else Bundle(target=target)


@pytest.fixture
def run_eval(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    module = _load_run_eval()
    (tmp_path / "demo").mkdir()
    monkeypatch.setattr(module, "EVAL_REPOS", tmp_path)
    _RecordingRunner.configs = []
    _RecordingRunner.bundle_factory = None
    monkeypatch.setattr(module, "PipelineRunner", _RecordingRunner)
    return module


def _runs_stage(config: PipelineConfig, stage: str) -> bool:
    skipped = set(config.skip_stages) | ({"dynamic"} if config.skip_dynamic else set())
    return stage in config.stages and stage not in skipped


def test_include_dynamic_runs_the_dynamic_stage(run_eval: ModuleType) -> None:
    run_eval.run_one("demo", skip_dynamic=False)

    (config,) = _RecordingRunner.configs
    assert _runs_stage(config, "dynamic")
    # Stage order must follow the pipeline's canonical order.
    assert config.stages.index("graph") < config.stages.index("dynamic")
    assert config.stages.index("dynamic") < config.stages.index("translate")


def test_default_evaluation_skips_the_dynamic_stage(run_eval: ModuleType) -> None:
    run_eval.run_one("demo")

    (config,) = _RecordingRunner.configs
    assert not _runs_stage(config, "dynamic")


def _bundle_with_graph(target: str) -> Bundle:
    bundle = Bundle(target=target)
    bundle.artifacts[ArtifactKey.PROGRAM_GRAPH] = SimpleNamespace(nodes={"n1": object()}, edges={})
    bundle.artifacts[ArtifactKey.SEMANTIC_MAPPINGS] = {}
    bundle.artifacts[ArtifactKey.STATE_SPACE_MODEL] = object()
    return bundle


def test_gnn_matrix_failure_is_not_reported_as_pass(
    run_eval: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    _RecordingRunner.bundle_factory = _bundle_with_graph

    import cogant.gnn.matrices as matrices

    class _BrokenMatrices:
        def __init__(self, *_args: object) -> None:
            raise ValueError("state space has no factors")

    monkeypatch.setattr(matrices, "GNNMatrices", _BrokenMatrices)

    result = run_eval.run_one("demo")

    assert result["node_count"] == 1
    assert any("GNNMatrices error" in err for err in result["bundle_errors"])
    assert result["status"] == "partial"


def test_bundle_error_count_is_not_capped_by_the_error_preview(run_eval: ModuleType) -> None:
    def bundle_with_many_errors(target: str) -> Bundle:
        bundle = _bundle_with_graph(target)
        bundle.errors.extend(f"Stage s{i} failed: boom" for i in range(7))
        return bundle

    _RecordingRunner.bundle_factory = bundle_with_many_errors

    result = run_eval.run_one("demo")

    assert result["bundle_error_count"] >= 7
    assert len(result["bundle_errors"]) <= 5 + 1  # preview plus evaluation errors
    assert result["status"] == "partial"
