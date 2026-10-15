from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from cogant.gnn.runner import GNNModelRunner, load_gnn_package
from tests.gnn_execution_fixture import MODEL, package, runner

pytestmark = pytest.mark.unit


def test_posterior_uses_exported_likelihood_and_prior(tmp_path: Path) -> None:
    model = runner(tmp_path)
    result = model.run(1)
    first = result["traces"][0]
    assert list(first["beliefs_prior"].values()) == [0.75, 0.25]
    assert list(first["beliefs"].values()) == pytest.approx([27 / 29, 2 / 29])
    assert first["free_energy_after"] == pytest.approx(-math.log(0.725))
    assert list(first["predicted_state"].values()) == pytest.approx([0.0, 1.0])
    assert result["source_sha256"] == hashlib.sha256(MODEL.encode()).hexdigest()


def test_rollout_uses_previous_action_prediction_as_next_prior(tmp_path: Path) -> None:
    result = runner(tmp_path).run(3)
    for previous, current in zip(result["traces"][:-1], result["traces"][1:], strict=True):
        assert current["beliefs_prior"] == previous["predicted_state"]
    assert result["final_beliefs"] == result["traces"][-1]["beliefs"]
    assert result["final_state"] == result["traces"][-1]["predicted_state"]


@pytest.mark.parametrize("steps", [0, -1, 10001, True, 1.5, "2"])
def test_step_admission_fails_before_success_report(tmp_path: Path, steps) -> None:
    model = runner(tmp_path)
    model.run(1)
    with pytest.raises(ValueError):
        model.run(steps)
    assert model.traces == []
    assert "Execution rejected:" in model.generate_execution_report()


@pytest.mark.parametrize("file", ["manifest.json", "model.gnn.md"])
def test_missing_required_file_rejects_loading(tmp_path: Path, file: str) -> None:
    package(tmp_path)
    (tmp_path / file).unlink()
    with pytest.raises(FileNotFoundError):
        GNNModelRunner().load_package(str(tmp_path))


@pytest.mark.parametrize("manifest", ["[]", "null", "{broken"])
def test_invalid_manifest_rejects_loading(tmp_path: Path, manifest: str) -> None:
    package(tmp_path)
    (tmp_path / "manifest.json").write_text(manifest)
    with pytest.raises(ValueError):
        GNNModelRunner().load_package(str(tmp_path))


@pytest.mark.parametrize(
    "old,new",
    [
        ("0.9 0.2", "0.9 0.9"),
        ("0.9 0.2", "-0.1 0.2"),
        ("0.75\n0.25", "0.0\n0.0"),
        ("0.75\n0.25", "0.75\n0.5"),
        ("1.0 0.0\n0.0 1.0", "0.0 0.0\n0.0 1.0"),
        ("0.0\n4.0", "0.0\n1e999"),
        ("A[[rows=2][cols=2]]", "A[[rows=3][cols=2]]"),
        ("B[[rows=2][cols=2][depth=2]]", "B[[rows=2][cols=3][depth=2]]"),
    ],
)
def test_corrupted_matrices_reject_loading(tmp_path: Path, old: str, new: str) -> None:
    package(tmp_path, MODEL.replace(old, new))
    with pytest.raises(ValueError):
        GNNModelRunner().load_package(str(tmp_path))


@pytest.mark.parametrize(
    "block",
    [
        "A[[rows=2][cols=2]]\n0.9 0.2\n0.1 0.8\n",
        "B[[rows=2][cols=2][depth=2]]\n# action=0\n1.0 0.0\n0.0 1.0\n# action=1\n0.0 0.0\n1.0 1.0\n",
        "C[[rows=2][cols=1]]\n0.0\n4.0\n",
        "D[[rows=2][cols=1]]\n0.75\n0.25\n",
    ],
)
def test_missing_matrix_is_not_invented(tmp_path: Path, block: str) -> None:
    package(tmp_path, MODEL.replace(block, ""))
    with pytest.raises(ValueError):
        GNNModelRunner().load_package(str(tmp_path))


def test_factorized_projection_is_not_admitted_as_exact_execution(tmp_path: Path) -> None:
    from tests.unit.test_reverse_callable import MINIMAL_GNN

    package(tmp_path, MINIMAL_GNN.split("## State Space")[0])
    with pytest.raises(ValueError, match="non-degraded"):
        GNNModelRunner().load_package(str(tmp_path))


def test_failed_reload_cannot_execute_previous_package(tmp_path: Path) -> None:
    model = runner(tmp_path / "valid")
    model.run(1)
    with pytest.raises(FileNotFoundError):
        model.load_package(str(tmp_path / "missing"))
    with pytest.raises(RuntimeError, match="not loaded"):
        model.run(1)
    assert "No traces" in model.generate_execution_report()


def test_loading_freezes_exact_text_for_reproducible_runs(tmp_path: Path) -> None:
    model = runner(tmp_path)
    (tmp_path / "model.gnn.md").write_text("corrupted after load")
    result = model.run(2)
    assert result["source_sha256"] == hashlib.sha256(MODEL.encode()).hexdigest()


def test_report_exposes_scope_and_truncates_only_display(tmp_path: Path) -> None:
    model = runner(tmp_path)
    result = model.run(35)
    report = model.generate_execution_report(result)
    assert "one-step expected free energy" in report
    assert "not measured execution" in report
    assert "5 more steps" in report
    assert len(result["traces"]) == 35
    assert result["source_sha256"] in report
    assert set(result) == {
        "success",
        "error",
        "steps_completed",
        "source_sha256",
        "matrices_sha256",
        "observation_mode",
        "policy_horizon",
        "policy_objective",
        "traces",
        "final_state",
        "final_beliefs",
        "statistics",
        "free_energy_trajectory",
        "action_distribution",
    }
    assert result["observation_mode"] == "model_rollout"
    assert result["policy_horizon"] == 1
    assert result["policy_objective"] == "risk_plus_ambiguity"
    energies = [trace.free_energy_after for trace in model.traces]
    assert result["free_energy_trajectory"] == energies
    assert result["statistics"] == {
        "unique_actions": 2,
        "mean_free_energy": sum(energies) / len(energies),
    }
    assert sum(result["action_distribution"].values()) == 35
    json.dumps(result, allow_nan=False)


def test_report_uses_supplied_result_not_subsequent_run(tmp_path: Path) -> None:
    model = runner(tmp_path)
    result = model.run(2)
    model.run(5)
    assert "Steps completed: 2" in model.generate_execution_report(result)


def test_run_requires_loaded_package() -> None:
    with pytest.raises(RuntimeError, match="not loaded"):
        GNNModelRunner().run(1)


def test_load_alias_validates_real_model(tmp_path: Path) -> None:
    assert load_gnn_package(str(package(tmp_path)))["version"] == "1.0"


def test_trace_json_copies_mutable_fields(tmp_path: Path) -> None:
    model = runner(tmp_path)
    model.run(1)
    saved = model.traces[0]
    exported = saved.to_dict()
    exported["beliefs"].clear()
    exported["policy_scores"].clear()
    assert len(saved.beliefs) == 2
    assert len(saved.policy_scores) == 2


def test_metadata_sidecars_do_not_replace_matrix_semantics(tmp_path: Path) -> None:
    package(tmp_path)
    (tmp_path / "state_space.json").write_text('{"variables":[{"name":"observation"}]}')
    (tmp_path / "transitions.json").write_text('{"transition":"invented"}')
    model = GNNModelRunner()
    model.load_package(str(tmp_path))
    assert list(model.run(1)["final_state"].values()) == pytest.approx([0.0, 1.0])
