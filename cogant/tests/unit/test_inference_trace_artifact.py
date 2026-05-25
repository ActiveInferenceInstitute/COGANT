"""Tests for deterministic runtime inference artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from cogant.runtime.inference_demo import (
    run_deterministic_inference_demo,
    write_inference_trace_artifact,
)


def test_run_deterministic_inference_demo_emits_belief_policy_preference_vfe() -> None:
    payload = run_deterministic_inference_demo(steps=4)

    assert payload["summary"]["steps"] == 4
    first = payload["trace"][0]
    assert set(first) >= {
        "belief",
        "action",
        "preference_satisfaction",
        "free_energy",
        "predicted_observation",
    }
    assert abs(sum(first["belief"]) - 1.0) < 1e-6


def test_write_inference_trace_artifact_uses_data_dir(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    path = write_inference_trace_artifact(tmp_path, steps=2)

    assert path == tmp_path / "data" / "inference_trace.json"
    assert json.loads(path.read_text(encoding="utf-8"))["summary"]["steps"] == 2
