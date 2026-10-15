from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _module():
    path = Path(__file__).resolve().parents[1] / "tools" / "manuscript_vars.py"
    spec = importlib.util.spec_from_file_location("roundtrip_table_vars", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_roundtrip_table_uses_current_targets_scores_and_strict_flags():
    module = _module()
    rows = [
        {
            "name": "application",
            "group": "real_world",
            "role_preservation_score": 0.8667,
            "roundtrip_status": "ROLE_PRESERVED",
            "strict_structural": False,
        },
        {
            "name": "reversible",
            "group": "control_positive",
            "role_preservation_score": 1.0,
            "roundtrip_status": "STRUCTURALLY_ISOMORPHIC",
            "strict_structural": True,
        },
    ]
    metrics = {"evaluation": {"roundtrip": {"per_target": rows}}}
    result, _ = module.substitute_text("{{ROUNDTRIP_TARGET_ROWS}}", metrics)
    assert result == (
        "| `application` | real_world | 0.8667 | `ROLE_PRESERVED` | no |\n"
        "| `reversible` | control_positive | 1 | `STRUCTURALLY_ISOMORPHIC` | yes |"
    )
    rows.pop()
    result, _ = module.substitute_text("{{ROUNDTRIP_TARGET_ROWS}}", metrics)
    assert "reversible" not in result
    assert len(result.splitlines()) == 1


@pytest.mark.parametrize("value", [None, {}, ["bad row"], [{"name": "missing fields"}]])
def test_roundtrip_table_rejects_invalid_data(value):
    module = _module()
    with pytest.raises((ValueError, KeyError, TypeError)):
        module.format_value_for_path("evaluation.roundtrip.per_target", value)
