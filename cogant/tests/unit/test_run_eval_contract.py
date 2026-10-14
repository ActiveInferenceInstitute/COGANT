"""Contract tests for ``evaluation/run_eval.py`` (real-world evaluation driver)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from cogant.api.bundle import Bundle
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
