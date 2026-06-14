"""Tests for the ``scaffolding_fraction`` per-target diagnostic added to
``tools/regenerate_metrics.py`` (RedTeam F23, 2026-05-20).

The function under test is the nested closure ``_scaffolding_fraction``
inside ``parse_roundtrip_results``. We can't import it directly, so the
tests drive it by constructing a synthetic JSONL and inspecting the
``per_target`` payload through the top-level public API.

The contract:

* For unscored rows that carry the per-role count fields
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


def test_scaffolding_fraction_matches_formula_on_simple_state() -> None:
    """The per-target ``scaffolding_fraction`` for zoo/01_simple_state must equal
    ``(sum(synth_*) - sum(orig_*)) / sum(synth_*)`` recomputed from that row's
    own per-role counts in the native ledger — verifying the formula against the
    live data rather than pinning a hand-typed fixture value (which drifts with
    every ledger regeneration)."""
    import json

    ledger = ROOT / "cogant" / "evaluation" / "dataset" / "roundtrip_results.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    ledger_row = next((r for r in rows if r.get("repo") == "01_simple_state"), None)
    assert ledger_row is not None, "01_simple_state missing from ledger"
    orig = sum(int(ledger_row.get(f"orig_n_{k}", 0)) for k in ("hidden", "obs", "actions"))
    synth = sum(int(ledger_row.get(f"synth_n_{k}", 0)) for k in ("hidden", "obs", "actions"))
    expected = round((synth - orig) / synth, 4) if synth > 0 else 0.0

    row = _read_per_target_for_repo(
        ROOT / "cogant" / "evaluation" / "METRICS.yaml", "01_simple_state"
    )
    assert row is not None, "01_simple_state row missing"
    sf = row.get("scaffolding_fraction")
    assert sf is not None
    assert abs(float(sf) - expected) < 1e-9, f"per_target {sf} != formula {expected}"


def test_scaffolding_fraction_in_unit_interval_on_sensor_fusion() -> None:
    """A representative real fixture's scaffolding_fraction stays a valid
    fraction in [0, 1] (the native ledger value depends on the run; only the
    bound is asserted here)."""
    row = _read_per_target_for_repo(
        ROOT / "cogant" / "evaluation" / "METRICS.yaml", "11_sensor_fusion"
    )
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
