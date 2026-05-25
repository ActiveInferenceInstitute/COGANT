"""No-mocks tests for the measured ablation visualization.

Real METRICS-shaped input, real matplotlib render, real PNG bytes — no
mocks, deterministic.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cogant.viz import render_ablation_png
from cogant.viz.ablation_view import _load_ablation

_METRICS_YAML = """\
schema_version: '1.0'
ablation:
  rule_family:
    calculator:
      baseline_mappings_total: 11
      structural_delta: 1
      semantic_delta: 10
      control_delta: 0
      behavioral_delta: 0
      resilience_delta: 0
    flask_app:
      baseline_mappings_total: 72
      structural_delta: 10
      semantic_delta: 53
      control_delta: 0
      behavioral_delta: 0
      resilience_delta: 1
  fixpoint:
    calculator: {k1: 11, k2: 11, k5: 11, k10: 11}
    flask_app: {k1: 72, k2: 72, k5: 72, k10: 72}
  matrix_fallback:
    calculator: {a_rows_uniform: 3, a_rows_total: 3}
"""

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _write_metrics(tmp_path: Path) -> Path:
    p = tmp_path / "METRICS.yaml"
    p.write_text(_METRICS_YAML, encoding="utf-8")
    return p


def test_render_ablation_png_writes_valid_png(tmp_path: Path) -> None:
    metrics = _write_metrics(tmp_path)
    out = tmp_path / "ablation.png"
    result = render_ablation_png(metrics, out)
    assert result == out
    assert out.is_file()
    data = out.read_bytes()
    assert data[:8] == _PNG_MAGIC, "output is not a valid PNG"
    assert len(data) > 5000, "PNG suspiciously small"


def test_render_ablation_png_is_deterministic(tmp_path: Path) -> None:
    metrics = _write_metrics(tmp_path)
    out = tmp_path / "a.png"
    render_ablation_png(metrics, out)
    first = hashlib.sha256(out.read_bytes()).hexdigest()
    render_ablation_png(metrics, out)
    second = hashlib.sha256(out.read_bytes()).hexdigest()
    assert first == second, "ablation render is not byte-deterministic"


def test_load_ablation_reads_real_keys(tmp_path: Path) -> None:
    metrics = _write_metrics(tmp_path)
    ablation = _load_ablation(metrics)
    assert set(ablation) == {"rule_family", "fixpoint", "matrix_fallback"}
    assert ablation["rule_family"]["flask_app"]["semantic_delta"] == 53
    assert ablation["fixpoint"]["calculator"]["k10"] == 11


def test_load_ablation_rejects_metrics_without_ablation(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("schema_version: '1.0'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no 'ablation' block"):
        _load_ablation(p)


def test_render_ablation_png_against_real_metrics_yaml() -> None:
    """Drive the real shipped METRICS.yaml (integration-style, no mocks)."""
    metrics = Path(__file__).resolve().parents[2] / "evaluation" / "METRICS.yaml"
    if not metrics.is_file():
        pytest.skip("shipped METRICS.yaml not present in this checkout")
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "real_ablation.png"
        render_ablation_png(metrics, out)
        assert out.read_bytes()[:8] == _PNG_MAGIC
