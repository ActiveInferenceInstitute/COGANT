"""Tests for ``tools/audit_robustness_table.py`` — the robustness-table claim gate.

Two contracts, mirroring ``test_audit_stage_list.py``:

1. **Positive control** — the gate passes on the current tree: the manuscript
   robustness table (``{#tbl:robustness-transforms}`` in
   ``08_05_threats_to_validity.md``) agrees with the generator artifact
   ``cogant/evaluation/robustness/robustness_results.json``.

2. **Negative controls** — the gate FAILS on deliberately-corrupted inputs
   (wrong verdict, a point value where a DETECTED bound is required, a table
   transform absent from the generator, a generator transform absent from the
   table). This proves the gate binds the manuscript numbers to the generated
   numbers rather than merely checking that *a* table exists — closing the
   RedTeam science-gap finding that the table was hand-written and bound to
   nothing (project claim policy: no manuscript metric unless injected or
   audited). See PAI memory ``feedback-shape-tests-dont-bind-truth``.

No mocks: the negative controls write real forged files into ``tmp_path`` and
repoint the auditor's module-level paths at them.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tools" / "audit_robustness_table.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_robustness_table", AUDIT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so the module's frozen dataclass can resolve its
    # __module__ via sys.modules (dataclasses introspects it at class creation).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_REAL_TABLE = (
    "| Transform | Class | Role similarity | Verdict |\n"
    "|---|---|---:|---|\n"
    "| `reformat` (fmt) | semantics-preserving | 1.0000 | ROBUST |\n"
    "| `drop_half_definitions` | **negative control** | < 0.99 | DETECTED |\n"
    "\n"
    ": caption. {#tbl:robustness-transforms}\n"
)

_REAL_JSON = {
    "per_transform": {
        "reformat": {
            "category": "semantics_preserving",
            "fixtures": 3,
            "mean_similarity": 1.0,
            "min_similarity": 1.0,
            "status": "ROBUST",
        },
        "drop_half_definitions": {
            "category": "negative_control",
            "fixtures": 3,
            "mean_similarity": 0.9163,
            "min_similarity": 0.7882,
            "status": "DETECTED",
        },
    },
    "robust_threshold": 0.99,
    "summary": {"robust_threshold": 0.99},
}


def _stage(tmp_path: Path, table: str, data: dict) -> tuple[Path, Path]:
    table_path = tmp_path / "08_05_threats_to_validity.md"
    json_path = tmp_path / "robustness_results.json"
    table_path.write_text(table, encoding="utf-8")
    json_path.write_text(json.dumps(data), encoding="utf-8")
    return table_path, json_path


def test_audit_passes_on_current_tree() -> None:
    """The shipped manuscript table must agree with the generated results."""
    result = subprocess.run(
        [sys.executable, str(AUDIT)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, (
        f"robustness-table audit failed on current tree:\n{result.stdout}\n{result.stderr}"
    )
    assert "PASS" in result.stdout


def test_synthetic_consistent_inputs_pass(tmp_path: Path, monkeypatch) -> None:
    """A consistent forged pair passes — establishes the baseline for the
    negative controls below (so a FAIL there is attributable to the corruption,
    not to harness wiring)."""
    mod = _load_module()
    table_path, json_path = _stage(tmp_path, _REAL_TABLE, _REAL_JSON)
    monkeypatch.setattr(mod, "MANUSCRIPT_TABLE", table_path)
    monkeypatch.setattr(mod, "RESULTS_JSON", json_path)
    assert mod.audit() == []


def test_negative_control_wrong_verdict_fails(tmp_path: Path, monkeypatch) -> None:
    """A ROBUST row whose generator says DETECTED must FAIL."""
    mod = _load_module()
    bad_table = _REAL_TABLE.replace(
        "| `reformat` (fmt) | semantics-preserving | 1.0000 | ROBUST |",
        "| `reformat` (fmt) | semantics-preserving | 1.0000 | DETECTED |",
    )
    table_path, json_path = _stage(tmp_path, bad_table, _REAL_JSON)
    monkeypatch.setattr(mod, "MANUSCRIPT_TABLE", table_path)
    monkeypatch.setattr(mod, "RESULTS_JSON", json_path)
    problems = mod.audit()
    assert problems, "gate must reject a verdict that disagrees with the generator"
    assert any("verdict" in p.lower() for p in problems)


def test_negative_control_point_value_for_detected_fails(tmp_path: Path, monkeypatch) -> None:
    """A DETECTED negative control stated as a concrete similarity (not a bound)
    must FAIL — a point value would imply a measured preservation it does not
    have."""
    mod = _load_module()
    bad_table = _REAL_TABLE.replace(
        "| `drop_half_definitions` | **negative control** | < 0.99 | DETECTED |",
        "| `drop_half_definitions` | **negative control** | 1.0000 | DETECTED |",
    )
    table_path, json_path = _stage(tmp_path, bad_table, _REAL_JSON)
    monkeypatch.setattr(mod, "MANUSCRIPT_TABLE", table_path)
    monkeypatch.setattr(mod, "RESULTS_JSON", json_path)
    problems = mod.audit()
    assert problems, "gate must reject a point value on a DETECTED negative control"


def test_negative_control_similarity_drift_fails(tmp_path: Path, monkeypatch) -> None:
    """A robust row whose stated similarity differs from the generated mean
    must FAIL — this is the exact hand-edited-number drift the gate exists to
    catch."""
    mod = _load_module()
    drifted = dict(_REAL_JSON)
    drifted["per_transform"] = dict(_REAL_JSON["per_transform"])
    drifted["per_transform"]["reformat"] = {
        **_REAL_JSON["per_transform"]["reformat"],
        "mean_similarity": 0.93,
        "min_similarity": 0.93,
        "status": "ROBUST",
    }
    table_path, json_path = _stage(tmp_path, _REAL_TABLE, drifted)
    monkeypatch.setattr(mod, "MANUSCRIPT_TABLE", table_path)
    monkeypatch.setattr(mod, "RESULTS_JSON", json_path)
    problems = mod.audit()
    assert problems, "gate must reject a manuscript number that drifts from the generator mean"
    assert any("similarity" in p.lower() for p in problems)


def test_negative_control_extra_generator_transform_fails(tmp_path: Path, monkeypatch) -> None:
    """A transform the generator measured but the manuscript omits must FAIL —
    the table cannot silently drop a measured result."""
    mod = _load_module()
    extra = dict(_REAL_JSON)
    extra["per_transform"] = dict(_REAL_JSON["per_transform"])
    extra["per_transform"]["rename_locals"] = {
        "category": "semantics_preserving",
        "fixtures": 3,
        "mean_similarity": 1.0,
        "min_similarity": 1.0,
        "status": "ROBUST",
    }
    table_path, json_path = _stage(tmp_path, _REAL_TABLE, extra)
    monkeypatch.setattr(mod, "MANUSCRIPT_TABLE", table_path)
    monkeypatch.setattr(mod, "RESULTS_JSON", json_path)
    problems = mod.audit()
    assert problems, "gate must reject a generated transform absent from the manuscript table"
    assert any("absent from the manuscript" in p for p in problems)
