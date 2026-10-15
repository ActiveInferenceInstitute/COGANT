import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.cli.main import app
from cogant.statespace import FiniteModelSpec, compile_finite_model

pytestmark = pytest.mark.unit
SPEC = Path(__file__).parents[2] / "examples" / "finite_models" / "toggle.json"
runner = CliRunner()


def test_compile_stdout_is_a_readable_matrix_artifact() -> None:
    result = runner.invoke(app, ["finite", "compile", str(SPEC)])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["D"] == [1.0, 0.0]


def test_compile_to_file_and_verify_all_entries(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "toggle.json"
    built = runner.invoke(app, ["finite", "compile", str(SPEC), "-o", str(target)])
    assert built.exit_code == 0, built.output

    result = runner.invoke(app, ["finite", "verify", str(SPEC), str(target)])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "passed": True,
        "checked_entries": 16,
        "mismatch_count": 0,
        "counterexamples": [],
    }


def test_existing_output_is_preserved(tmp_path: Path) -> None:
    target = tmp_path / "existing.json"
    target.write_text("preserve existing work")

    result = runner.invoke(app, ["finite", "compile", str(SPEC), "-o", str(target)])

    assert result.exit_code == 2
    assert target.read_text() == "preserve existing work"


def test_wrong_but_stochastic_artifact_exits_one_with_counterexamples(tmp_path: Path) -> None:
    spec = FiniteModelSpec.model_validate_json(SPEC.read_text())
    model = compile_finite_model(spec).model_dump(mode="json")
    model["B"][0][0][1], model["B"][1][0][1] = 1.0, 0.0
    target = tmp_path / "wrong.json"
    target.write_text(json.dumps(model))

    result = runner.invoke(app, ["finite", "verify", str(SPEC), str(target)])

    assert result.exit_code == 1
    assert json.loads(result.stdout)["mismatch_count"] == 2


@pytest.mark.parametrize("contents", ["{}", "not JSON", '{"name": "incomplete"}'])
def test_invalid_spec_has_no_output_artifact(tmp_path: Path, contents: str) -> None:
    source, target = tmp_path / "bad.json", tmp_path / "target.json"
    source.write_text(contents)

    result = runner.invoke(app, ["finite", "compile", str(source), "-o", str(target)])

    assert result.exit_code == 2
    assert not target.exists()


def test_budget_exhaustion_has_no_output_artifact(tmp_path: Path) -> None:
    target = tmp_path / "target.json"

    result = runner.invoke(
        app, ["finite", "compile", str(SPEC), "-o", str(target), "--max-entries", "15"]
    )

    assert result.exit_code == 2
    assert not target.exists()


def test_invalid_compiled_artifact_exits_two(tmp_path: Path) -> None:
    target = tmp_path / "bad.json"
    target.write_text("{}")

    result = runner.invoke(app, ["finite", "verify", str(SPEC), str(target)])

    assert result.exit_code == 2
    assert result.stderr
