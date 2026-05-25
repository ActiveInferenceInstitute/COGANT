"""Focused tests for the inspection-dashboard no-run-data guard.

A pseudo-target directory with no real run artifacts (no program graph, no
GNN package, no run bundle) must NOT render a board of all-zeros that is
indistinguishable from a real result. It must render an unmissable
``NO RUN DATA`` banner instead. A real run directory must keep rendering the
real metric numbers with no banner and a byte-identical metric region.

No mocks: tests build a real empty directory with ``tmp_path`` and use the
real on-disk ``output/calculator`` run directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.viz.inspection_dashboard import (
    build_inspection_model,
    render_inspection_dashboard_html,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CALCULATOR_RUN_DIR = _REPO_ROOT / "output" / "calculator"


def _metric_region(html: str) -> str:
    """Return just the metric-grid section the guard rewrites."""
    start = html.index('<section class="metric-grid" aria-label="Run metrics">')
    end = html.index("</section>", start) + len("</section>")
    return html[start:end]


def test_empty_run_dir_renders_no_run_data_banner_not_zero_cards(
    tmp_path: Path,
) -> None:
    """Zero-data run dir -> banner present, zero misleading "0" metric cards."""
    empty_run = tmp_path / "dashboard"
    empty_run.mkdir()

    model = build_inspection_model(empty_run)
    assert model["no_run_data"] is True
    assert model["program"]["nodes"] == 0
    assert model["program"]["edges"] == 0

    out = render_inspection_dashboard_html(
        empty_run,
        tmp_path / "empty.html",
        embed_assets=False,
    )
    html = out.read_text(encoding="utf-8")
    region = _metric_region(html)

    # Unmissable banner is present.
    assert html.count("NO RUN DATA") >= 1
    assert 'class="no-run-data"' in region
    # No misleading zero-valued metric cards leaked into the metric region.
    assert '<div class="metric-value">0</div>' not in region
    assert '<div class="metric-value">0%</div>' not in region
    # The five real metric cards are NOT rendered when there is no data.
    assert '<div class="metric-label">Program graph</div>' not in region


def test_partial_artifact_breaks_no_run_data(tmp_path: Path) -> None:
    """A single real data artifact must flip the guard off (conservative)."""
    run = tmp_path / "partial"
    (run / "data").mkdir(parents=True)
    (run / "data" / "bundle.json").write_text("{}", encoding="utf-8")

    model = build_inspection_model(run)
    assert model["no_run_data"] is False

    html = render_inspection_dashboard_html(
        run,
        tmp_path / "partial.html",
        embed_assets=False,
    ).read_text(encoding="utf-8")
    assert "NO RUN DATA" not in html


def test_program_graph_with_nodes_breaks_no_run_data(tmp_path: Path) -> None:
    """Any nonzero graph node count must flip the guard off."""
    run = tmp_path / "withnodes"
    (run / "data").mkdir(parents=True)
    (run / "data" / "program_graph.json").write_text(
        json.dumps({"nodes": [{"id": "n1", "kind": "function"}], "edges": []}),
        encoding="utf-8",
    )

    model = build_inspection_model(run)
    assert model["no_run_data"] is False
    assert model["program"]["nodes"] == 1


@pytest.mark.skipif(
    not (_CALCULATOR_RUN_DIR / "data" / "program_graph.json").is_file(),
    reason="calculator run dir not present in this checkout",
)
def test_real_calculator_run_dir_renders_real_numbers_no_banner(
    tmp_path: Path,
) -> None:
    """Real run dir -> real numbers, no banner, untouched metric region."""
    model = build_inspection_model(_CALCULATOR_RUN_DIR)
    assert model["no_run_data"] is False
    assert model["program"]["nodes"] == 12
    assert model["program"]["edges"] == 25

    html = render_inspection_dashboard_html(
        _CALCULATOR_RUN_DIR,
        tmp_path / "calculator.html",
        embed_assets=False,
    ).read_text(encoding="utf-8")
    region = _metric_region(html)

    assert "NO RUN DATA" not in html
    assert 'class="no-run-data"' not in region
    assert '<div class="metric-value">12</div>' in region
    for label in (
        "Program graph",
        "Semantic roles",
        "State space",
        "Coverage",
        "Roundtrip",
    ):
        assert f'<div class="metric-label">{label}</div>' in region


@pytest.mark.skipif(
    not (_CALCULATOR_RUN_DIR / "site" / "inspection_dashboard.html").is_file(),
    reason="pre-existing calculator dashboard not present in this checkout",
)
def test_real_calculator_metric_region_is_byte_identical(tmp_path: Path) -> None:
    """The fix must not perturb real-target metric-region bytes."""
    existing = (
        _CALCULATOR_RUN_DIR / "site" / "inspection_dashboard.html"
    ).read_text(encoding="utf-8")
    regenerated = render_inspection_dashboard_html(
        _CALCULATOR_RUN_DIR,
        tmp_path / "calculator.html",
        embed_assets=True,
    ).read_text(encoding="utf-8")
    assert _metric_region(regenerated) == _metric_region(existing)
