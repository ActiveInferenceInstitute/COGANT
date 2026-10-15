"""Contract tests for ``evaluation/run_eval.py`` (real-world evaluation driver)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from cogant.api.bundle import ArtifactKey, Bundle

_RUN_EVAL = Path(__file__).resolve().parents[2] / "evaluation" / "run_eval.py"


def _load_run_eval() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_eval_under_test", _RUN_EVAL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run_eval(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    module = _load_run_eval()
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "main.py").write_text("def add(a, b):\n    return a + b\n")
    monkeypatch.setattr(module, "EVAL_REPOS", tmp_path)
    return module


def test_include_dynamic_runs_the_dynamic_stage(run_eval: ModuleType) -> None:
    result = run_eval.run_one("demo", skip_dynamic=False)
    assert result["node_count"] > 0
    assert "dynamic" in result["stage_outcomes"]
    stages = list(result["stage_outcomes"])
    assert stages.index("graph") < stages.index("dynamic") < stages.index("translate")


def test_default_evaluation_skips_the_dynamic_stage(run_eval: ModuleType) -> None:
    result = run_eval.run_one("demo")
    assert result["node_count"] > 0
    assert "dynamic" not in result["stage_outcomes"]


def _bundle_with_graph(target: str) -> Bundle:
    bundle = Bundle(target=target)
    bundle.artifacts[ArtifactKey.PROGRAM_GRAPH] = SimpleNamespace(nodes={"n1": object()}, edges={})
    bundle.artifacts[ArtifactKey.SEMANTIC_MAPPINGS] = {}
    bundle.artifacts[ArtifactKey.STATE_SPACE_MODEL] = object()
    return bundle


def _empty_result() -> dict:
    return {"node_count": 0, "edge_count": 0, "exception": None}


def test_gnn_matrix_failure_is_not_reported_as_pass(run_eval: ModuleType) -> None:
    result = run_eval._inspect_bundle(_bundle_with_graph("demo"), _empty_result())

    assert result["node_count"] == 1
    assert any("GNNMatrices error" in err for err in result["bundle_errors"])
    assert result["status"] == "partial"


def test_bundle_error_count_is_not_capped_by_the_error_preview(run_eval: ModuleType) -> None:
    bundle = _bundle_with_graph("demo")
    bundle.errors.extend(f"Stage s{i} failed: boom" for i in range(7))
    result = run_eval._inspect_bundle(bundle, _empty_result())

    assert result["bundle_error_count"] >= 7
    assert len(result["bundle_errors"]) <= 5 + 1  # preview plus evaluation errors
    assert result["status"] == "partial"
