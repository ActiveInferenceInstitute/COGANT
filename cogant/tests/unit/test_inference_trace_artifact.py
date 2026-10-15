from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from cogant.runtime.inference import (
    load_inference_trace,
    run_gnn_inference,
    write_inference_trace_artifact,
)
from cogant.runtime.inference_records import InferenceOptions
from cogant.viz.inference_view import render_inference_trace_png
from tests.gnn_execution_fixture import MODEL, package


def test_conditioning_timing_policy_and_source_identity() -> None:
    result = run_gnn_inference(MODEL, InferenceOptions(steps=2, observations=(0, 1)))
    first = result.trace[0]
    assert result.source_sha256 == hashlib.sha256(MODEL.encode()).hexdigest()
    assert result.mode == "observations"
    assert first.prior == (0.75, 0.25)
    assert first.posterior == pytest.approx((0.675 / 0.725, 0.05 / 0.725))
    assert first.free_energy == pytest.approx(-math.log(0.725))
    assert first.action == 1
    assert first.policy_scores[1] < first.policy_scores[0]
    assert first.predicted_belief == (0.0, 1.0)
    assert result.trace[1].prior == first.predicted_belief
    assert result.trace[1].posterior == (0.0, 1.0)


def test_writer_loader_and_native_plot_bind_exact_inputs(tmp_path: Path) -> None:
    package(tmp_path / "gnn_package")
    (tmp_path / "data").mkdir()
    path = write_inference_trace_artifact(tmp_path, steps=3)
    result = load_inference_trace(tmp_path)
    assert path == tmp_path / "data" / "inference_trace.json"
    assert result.source_artifact == "gnn_package/model.gnn.md"
    assert len(result.trace) == 3
    png = render_inference_trace_png(tmp_path)
    assert png is not None and png.is_file()
    from PIL import Image

    with Image.open(png) as image:
        assert image.size == (2400, 1440)
    metadata = json.loads(png.with_suffix(".figure.json").read_text())
    assert metadata["trace_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert metadata["source_sha256"] == result.source_sha256
    assert metadata["matrices_sha256"] == result.matrices_sha256
    assert metadata["displayed_counts"] == {
        "steps": 3,
        "states": 2,
        "observations": 2,
        "actions": 2,
    }
    assert [panel["key"] for panel in metadata["panels"]] == [
        "posterior",
        "next_prediction",
        "policy_expected_free_energy",
        "filtering_free_energy",
    ]


@pytest.mark.parametrize("mutation", ["source", "matrix", "posterior", "mode", "missing"])
def test_old_png_cannot_admit_a_stale_or_corrupt_trace(tmp_path: Path, mutation: str) -> None:
    package(tmp_path / "gnn_package")
    path = write_inference_trace_artifact(tmp_path, steps=2)
    old_png = render_inference_trace_png(tmp_path)
    assert old_png is not None
    original_png = old_png.read_bytes()
    if mutation == "source":
        (tmp_path / "gnn_package" / "model.gnn.md").write_text(MODEL + "\n")
    elif mutation == "missing":
        path.rename(path.with_suffix(".preserved"))
    else:
        payload = json.loads(path.read_text())
        if mutation == "matrix":
            payload["matrices"]["D"] = [0.5, 0.5]
        elif mutation == "posterior":
            payload["trace"][0]["posterior"] = [0.5, 0.5]
        else:
            payload["mode"] = "invented"
        path.write_text(json.dumps(payload))
    with pytest.raises((ValueError, OSError)):
        render_inference_trace_png(tmp_path)
    assert old_png.read_bytes() == original_png


@pytest.mark.parametrize(
    "kwargs",
    [
        {"steps": 0},
        {"steps": True},
        {"steps": 2, "observations": (0,)},
        {"steps": 1, "observations": (True,)},
        {"max_work_units": 0},
    ],
)
def test_invalid_execution_options_are_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        InferenceOptions.model_validate(kwargs)


def test_budget_observation_axis_and_missing_matrices_are_rejected() -> None:
    with pytest.raises(ValueError, match="budget"):
        run_gnn_inference(MODEL, InferenceOptions(max_work_units=1))
    with pytest.raises(ValueError, match="observation"):
        run_gnn_inference(MODEL, InferenceOptions(steps=1, observations=(2,)))
    with pytest.raises(ValueError):
        run_gnn_inference("## ModelName\nIncomplete\n")
