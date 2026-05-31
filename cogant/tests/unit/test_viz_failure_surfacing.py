"""Regression tests: visualization must not silently mask renderer failures.

Two related defects are pinned here:

* **B1** — ``render_all_pngs`` caught every per-renderer exception and logged a
  warning, but returned only the successes, so a half-failed run reported the
  same green ``✓ Wrote N`` as a complete one. It now collects those warnings,
  emits a single distinct ERROR summary, and exposes them via a ``failures``
  out-parameter.
* **B2** — ``MatrixVisualizer.plot_A_matrix`` / ``plot_B_matrix`` drew a blank
  ``zeros((1, 1))`` heatmap under the *normal* title on empty data (a single
  dark cell that reads as a legitimate 1-state model). They now label the
  no-data case explicitly, matching ``plot_C_vector`` / ``plot_D_vector``.

No mocks: the failure-capture test feeds real ``logging.LogRecord`` objects and
the matrix tests render real matplotlib figures.
"""

import logging
import tempfile
from pathlib import Path

import pytest

from cogant.viz.png.orchestrator import _RendererFailureCapture, render_all_pngs


def _warning(msg: str) -> logging.LogRecord:
    return logging.LogRecord("t", logging.WARNING, "f.py", 1, msg, (), None)


def test_failure_capture_records_warnings_not_info() -> None:
    cap = _RendererFailureCapture()
    cap.emit(_warning("gnn markdown PNG failed: boom"))
    cap.emit(logging.LogRecord("t", logging.INFO, "f.py", 1, "wrote 3 files", (), None))
    cap.emit(_warning("summary cover PNG failed: kaboom"))
    # INFO is ignored; both WARNINGs captured verbatim.
    assert cap.messages == [
        "gnn markdown PNG failed: boom",
        "summary cover PNG failed: kaboom",
    ]


def test_render_all_pngs_accepts_failures_out_param_and_returns_dict() -> None:
    """A clean (empty) run dir produces no failures and a dict result."""
    with tempfile.TemporaryDirectory() as d:
        failures: list[str] = []
        out = render_all_pngs(Path(d), failures=failures)
    assert isinstance(out, dict)
    assert failures == []  # nothing to render, nothing failed


def test_render_all_pngs_surfaces_a_real_renderer_failure() -> None:
    """A corrupt program_graph.json must be SURFACED, not silently swallowed.

    Regression for a RedTeam finding against an earlier version of this fix:
    the capture handler was attached to the orchestrator's own module logger,
    but the program-graph renderer logs its "Could not read" warning on a
    SIBLING logger (``cogant.viz.png.program_graph``). Logging propagates a
    record up to ancestors, never to siblings, so the failure was invisible —
    and this very test was vacuous (it only checked ``isinstance(m, str)``,
    which is true of the empty list). The handler now attaches to the
    ``cogant.viz.png`` package logger, so sibling failures are captured. This
    test now asserts a NON-EMPTY, on-topic capture.
    """
    with tempfile.TemporaryDirectory() as d:
        run_dir = Path(d)
        (run_dir / "program_graph.json").write_text("{ this is not valid json ::::")
        failures: list[str] = []
        out = render_all_pngs(run_dir, failures=failures)
    assert isinstance(out, dict)
    assert failures, "a corrupt program_graph.json must surface a failure, not []"
    assert all(isinstance(m, str) for m in failures)
    assert any("program_graph" in m for m in failures), (
        f"expected the program-graph read failure to be surfaced; got {failures}"
    )


def test_clean_run_surfaces_no_spurious_failures() -> None:
    """An empty run dir must NOT report failures (no false positives)."""
    with tempfile.TemporaryDirectory() as d:
        failures: list[str] = []
        render_all_pngs(Path(d), failures=failures)
    assert failures == []


@pytest.fixture
def visualizer():  # type: ignore[no-untyped-def]
    pytest.importorskip("matplotlib")
    from cogant.viz.matrix_view import MatrixVisualizer

    return MatrixVisualizer()


def test_empty_a_matrix_is_labeled_no_data(visualizer) -> None:  # type: ignore[no-untyped-def]
    fig = visualizer.plot_A_matrix([], labels=[])
    assert fig is not None
    assert "no data" in fig.axes[0].get_title().lower()


def test_empty_b_matrix_is_labeled_no_data(visualizer) -> None:  # type: ignore[no-untyped-def]
    fig = visualizer.plot_B_matrix([])
    assert fig is not None
    assert "no data" in fig.axes[0].get_title().lower()


def test_nonempty_a_matrix_keeps_likelihood_title(visualizer) -> None:  # type: ignore[no-untyped-def]
    fig = visualizer.plot_A_matrix([[0.5, 0.5], [0.5, 0.5]], labels=["s0", "s1"])
    assert "likelihood" in fig.axes[0].get_title().lower()
    assert "no data" not in fig.axes[0].get_title().lower()
