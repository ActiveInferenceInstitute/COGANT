"""Deterministic Active-Inference trace artifacts for inspection dashboards."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cogant.runtime.loop import AgentRuntime

__all__ = [
    "default_demo_matrices",
    "run_deterministic_inference_demo",
    "write_inference_trace_artifact",
]


def default_demo_matrices() -> dict[str, Any]:
    """Return a tiny, deterministic A/B/C/D model used for smoke demos."""

    return {
        "A": [
            [0.90, 0.20],
            [0.10, 0.80],
        ],
        "B": [
            [[0.88, 0.30], [0.12, 0.70]],
            [[0.12, 0.70], [0.88, 0.30]],
        ],
        "C": [0.0, 1.0],
        "D": [0.55, 0.45],
        "labels": {
            "states": ["stable", "needs_attention"],
            "observations": ["quiet", "signal"],
            "actions": ["maintain", "intervene"],
        },
    }


def _preference_satisfaction(C: list[float], obs: int) -> float:
    if not C:
        return 0.0
    lo = min(C)
    hi = max(C)
    raw = C[obs] if 0 <= obs < len(C) else lo
    if hi == lo:
        return 1.0
    return (raw - lo) / (hi - lo)


def _predicted_observation(A: list[list[float]], state: list[float]) -> list[float]:
    """Multiply the likelihood matrix by a belief vector for trace display."""

    return [sum(a * b for a, b in zip(row, state, strict=False)) for row in A]


def run_deterministic_inference_demo(steps: int = 8) -> dict[str, Any]:
    """Run a deterministic perception-action loop and return JSON data."""

    matrices = default_demo_matrices()
    runtime = AgentRuntime.from_matrices_dict(matrices)
    records = []
    state = [float(value) for value in matrices["D"]]
    A = [[float(value) for value in row] for row in matrices["A"]]
    C = [float(value) for value in matrices["C"]]
    for t in range(steps):
        pred_obs = _predicted_observation(A, state)
        obs = max(range(len(pred_obs)), key=lambda idx: pred_obs[idx]) if pred_obs else 0
        step = runtime.step(state, obs, t=t)
        records.append(
            {
                "t": step.t,
                "belief": [round(x, 6) for x in step.state_dist],
                "predicted_observation": [round(float(x), 6) for x in pred_obs],
                "observation": step.obs,
                "action": step.action,
                "preference_satisfaction": round(
                    _preference_satisfaction(C, step.obs),
                    6,
                ),
                "free_energy": round(step.free_energy, 6),
            }
        )
        state = list(step.state_dist)

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "description": "Deterministic A/B/C/D runtime trace emitted by COGANT.",
        "matrices": matrices,
        "trace": records,
        "summary": {
            "steps": len(records),
            "initial_belief": matrices["D"],
            "final_belief": records[-1]["belief"] if records else matrices["D"],
            "final_free_energy": records[-1]["free_energy"] if records else None,
            "actions": [record["action"] for record in records],
        },
    }


def write_inference_trace_artifact(run_dir: str | Path, *, steps: int = 8) -> Path:
    """Write ``inference_trace.json`` under a run directory."""

    root = Path(run_dir)
    data_dir = root / "data" if (root / "data").is_dir() else root
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "inference_trace.json"
    path.write_text(json.dumps(run_deterministic_inference_demo(steps), indent=2), encoding="utf-8")
    return path
