from pathlib import Path

import pytest

from cogant.gnn.runner import GNNModelRunner
from tests.gnn_execution_fixture import MODEL, package, runner

pytestmark = pytest.mark.unit


def test_empty_model_rejected_before_execution(tmp_path: Path) -> None:
    package(tmp_path, "## ModelName\nEmpty\n")
    with pytest.raises(ValueError):
        GNNModelRunner().load_package(str(tmp_path))


def test_incomplete_reload_clears_completed_run(tmp_path: Path) -> None:
    model = runner(tmp_path / "valid")
    model.run(3)
    package(tmp_path / "bad", MODEL.replace("D[[rows=2][cols=1]]\n0.75\n0.25\n", ""))
    with pytest.raises(ValueError):
        model.load_package(str(tmp_path / "bad"))
    assert model.traces == []
    with pytest.raises(RuntimeError):
        model.run(1)


def test_successful_run_reports_completed_model_steps(tmp_path: Path) -> None:
    result = runner(tmp_path).run(3)
    assert result["success"] is True
    assert result["error"] is None
    assert result["steps_completed"] == 3
    assert sum(result["action_distribution"].values()) == 3
