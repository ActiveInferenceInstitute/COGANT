"""Unit tests for cogant.viz.matrix_view.MatrixVisualizer."""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))

from cogant.viz.matrix_view import MatrixVisualizer  # noqa: E402
from tests.unit._viz_assert import (  # noqa: E402
    assert_figure_nondegenerate,
    assert_png_nondegenerate,
)


@pytest.mark.unit
def test_plot_A_matrix_returns_figure_with_labels() -> None:
    viz = MatrixVisualizer()
    A = np.array([[0.9, 0.1, 0.0, 0.0], [0.1, 0.8, 0.1, 0.0], [0.0, 0.1, 0.9, 0.0]])
    fig = viz.plot_A_matrix(A, labels=["s1", "s2", "s3", "s4"])
    assert_figure_nondegenerate(fig)
    assert hasattr(fig, "savefig")


@pytest.mark.unit
def test_plot_A_matrix_without_labels() -> None:
    viz = MatrixVisualizer()
    A = np.eye(3)
    fig = viz.plot_A_matrix(A, labels=None)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_B_matrix_2d() -> None:
    viz = MatrixVisualizer()
    B = np.array([[0.8, 0.2], [0.3, 0.7]])
    fig = viz.plot_B_matrix(B)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_B_matrix_3d() -> None:
    viz = MatrixVisualizer()
    B = np.zeros((2, 3, 3))
    B[0] = np.eye(3)
    B[1] = np.eye(3) * 0.5
    fig = viz.plot_B_matrix(B, action_idx=1)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_summarize_matrices_handles_b_tensor_conventions() -> None:
    viz = MatrixVisualizer()
    matrices = {
        "A": np.eye(3),
        "B": np.dstack([np.eye(3), np.eye(3)]),
        "C": np.array([0.0, 1.0, -1.0]),
        "D": np.array([0.2, 0.3, 0.5]),
    }
    summary = viz.summarize_matrices(matrices, action_idx=1)
    assert summary["A"]["max_probability_error"] == pytest.approx(0.0)
    assert summary["B"]["slice_convention"] == "state_state_action"
    assert summary["B"]["action_count"] == 2
    assert summary["D"]["max_probability_error"] == pytest.approx(0.0)


@pytest.mark.unit
def test_plot_interpretability_panel_returns_figure() -> None:
    viz = MatrixVisualizer()
    matrices = {
        "A": np.eye(2),
        "B": np.dstack([np.eye(2), np.flipud(np.eye(2))]),
        "C": np.array([0.1, 0.9]),
        "D": np.array([0.5, 0.5]),
    }
    fig = viz.plot_interpretability_panel(
        matrices,
        labels={"states": ["idle", "busy"], "observations": ["quiet", "event"]},
        action_idx=0,
    )
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_C_vector() -> None:
    viz = MatrixVisualizer()
    C = np.array([0.0, 0.5, -1.0, 2.0, 0.1])
    fig = viz.plot_C_vector(C)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_D_vector() -> None:
    viz = MatrixVisualizer()
    D = np.array([0.25, 0.25, 0.25, 0.25])
    fig = viz.plot_D_vector(D)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_all_matrices_full_dict() -> None:
    viz = MatrixVisualizer()
    matrices = {
        "A": np.eye(3),
        "B": np.stack([np.eye(3), np.eye(3) * 0.5]),
        "C": np.array([0.1, 0.2, 0.7]),
        "D": np.array([0.33, 0.33, 0.34]),
    }
    fig = viz.plot_all_matrices(matrices)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_all_matrices_2d_B() -> None:
    viz = MatrixVisualizer()
    matrices = {
        "A": np.eye(2),
        "B": np.eye(2),
        "C": np.array([0.5, 0.5]),
        "D": np.array([0.5, 0.5]),
    }
    fig = viz.plot_all_matrices(matrices)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_all_matrices_empty_values() -> None:
    viz = MatrixVisualizer()
    matrices: dict[str, np.ndarray] = {
        "A": np.array([]),
        "B": np.array([]),
        "C": np.array([]),
        "D": np.array([]),
    }
    fig = viz.plot_all_matrices(matrices)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_to_png_round_trip(tmp_path) -> None:
    viz = MatrixVisualizer()
    fig = viz.plot_C_vector(np.array([0.1, 0.9]))
    out = tmp_path / "fig.png"
    result = viz.to_png(fig, str(out), dpi=80)
    assert result == str(out)
    assert out.exists()
    assert_png_nondegenerate(out)


@pytest.mark.unit
def test_to_pdf_round_trip(tmp_path) -> None:
    viz = MatrixVisualizer()
    fig = viz.plot_D_vector(np.array([0.5, 0.5]))
    out = tmp_path / "fig.pdf"
    result = viz.to_pdf(fig, str(out))
    assert result == str(out)
    assert out.exists()


@pytest.mark.unit
def test_to_png_none_fig_returns_empty_string(tmp_path) -> None:
    viz = MatrixVisualizer()
    result = viz.to_png(None, str(tmp_path / "nope.png"))
    assert result == ""


@pytest.mark.unit
def test_to_pdf_none_fig_returns_empty_string(tmp_path) -> None:
    viz = MatrixVisualizer()
    result = viz.to_pdf(None, str(tmp_path / "nope.pdf"))
    assert result == ""


@pytest.mark.unit
def test_to_png_invalid_path_returns_empty_string() -> None:
    viz = MatrixVisualizer()
    fig = viz.plot_C_vector(np.array([1.0]))
    # Path with non-existent directory should trigger the exception branch
    result = viz.to_png(fig, "/nonexistent_dir_xyz_123/out.png")
    assert result == ""


@pytest.mark.unit
def test_to_pdf_invalid_path_returns_empty_string() -> None:
    viz = MatrixVisualizer()
    fig = viz.plot_D_vector(np.array([1.0]))
    result = viz.to_pdf(fig, "/nonexistent_dir_xyz_123/out.pdf")
    assert result == ""
