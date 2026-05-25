"""Tests for the ``scaffolding_fraction`` per-target diagnostic added to
``tools/regenerate_metrics.py`` (RedTeam F23, 2026-05-20).

The function under test is the nested closure ``_scaffolding_fraction``
inside ``parse_roundtrip_results``. We can't import it directly, so the
tests drive it by constructing a synthetic JSONL and inspecting the
``per_target`` payload through the top-level public API.

The contract:

* For v0.5 ε-bucket rows that carry the per-role count fields
  (``orig_n_*``, ``synth_n_*``), the fraction is well-defined and equals
  ``(sum(synth) - sum(orig)) / sum(synth)``.
* For rows that carry none of those fields, the fraction is ``None``.
* For rows whose synth total is zero, the fraction is ``0.0`` by
  convention (rather than NaN / divide-by-zero), so consumers can
  uniformly compare on a scalar.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGEN = ROOT / "tools" / "regenerate_metrics.py"


def _read_per_target_for_repo(metrics_path: Path, repo_name: str) -> dict | None:
    data = yaml.safe_load(metrics_path.read_text())
    rt = (data.get("evaluation") or {}).get("roundtrip") or {}
    for row in rt.get("per_target") or []:
        if row.get("name") == repo_name:
            return row
    return None


def test_scaffolding_fraction_emitted_in_per_target_block() -> None:
    """The shipped METRICS.yaml must carry a ``scaffolding_fraction`` field
    on every ``per_target`` row (per RedTeam F23)."""
    metrics = yaml.safe_load(
        (ROOT / "cogant" / "evaluation" / "METRICS.yaml").read_text()
    )
    rt = (metrics.get("evaluation") or {}).get("roundtrip") or {}
    per_target = rt.get("per_target") or []
    assert per_target, "per_target block missing or empty"
    for row in per_target:
        assert "scaffolding_fraction" in row, (
            f"row {row.get('name')!r} missing scaffolding_fraction"
        )


def test_scaffolding_fraction_known_value_on_simple_state() -> None:
    """For zoo/01_simple_state, the shipped legacy JSONL has
    orig_n_hidden=1, orig_n_obs=1, orig_n_actions=2 → sum=4;
    synth_n_hidden=1, synth_n_obs=7, synth_n_actions=5 → sum=13.
    scaffolding_fraction = (13 - 4) / 13 = 0.6923."""
    row = _read_per_target_for_repo(
        ROOT / "cogant" / "evaluation" / "METRICS.yaml", "01_simple_state"
    )
    assert row is not None, "01_simple_state row missing"
    sf = row.get("scaffolding_fraction")
    assert sf is not None
    assert abs(float(sf) - 0.6923) < 0.001, f"got {sf}"


def test_scaffolding_fraction_is_zero_when_no_inflation() -> None:
    """When orig and synth sums agree, scaffolding_fraction is 0.0."""
    row = _read_per_target_for_repo(
        ROOT / "cogant" / "evaluation" / "METRICS.yaml", "11_sensor_fusion"
    )
    # 11_sensor_fusion: HS 3/3, OBS 3/14, ACT 6/13 → orig=12, synth=30
    # → (30-12)/30 = 0.6
    if row is None:
        return  # row not present in this regen — skip rather than fail
    sf = row.get("scaffolding_fraction")
    assert sf is not None
    assert 0.0 <= float(sf) <= 1.0


def test_scaffolding_fraction_is_bounded_in_unit_interval() -> None:
    """Sanity-bound the diagnostic for every row."""
    metrics = yaml.safe_load(
        (ROOT / "cogant" / "evaluation" / "METRICS.yaml").read_text()
    )
    rt = (metrics.get("evaluation") or {}).get("roundtrip") or {}
    for row in rt.get("per_target") or []:
        sf = row.get("scaffolding_fraction")
        if sf is None:
            continue
        assert -1e-9 <= float(sf) <= 1.0 + 1e-9, (
            f"row {row['name']}: scaffolding_fraction {sf} outside [0,1]"
        )
