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


@pytest.mark.unit
def test_plot_A_matrix_returns_figure_with_labels() -> None:
    viz = MatrixVisualizer()
    A = np.array([[0.9, 0.1, 0.0, 0.0], [0.1, 0.8, 0.1, 0.0], [0.0, 0.1, 0.9, 0.0]])
    fig = viz.plot_A_matrix(A, labels=["s1", "s2", "s3", "s4"])
    assert fig is not None
    assert hasattr(fig, "savefig")


@pytest.mark.unit
def test_plot_A_matrix_without_labels() -> None:
    viz = MatrixVisualizer()
    A = np.eye(3)
    fig = viz.plot_A_matrix(A, labels=None)
    assert fig is not None


@pytest.mark.unit
def test_plot_B_matrix_2d() -> None:
    viz = MatrixVisualizer()
    B = np.array([[0.8, 0.2], [0.3, 0.7]])
    fig = viz.plot_B_matrix(B)
    assert fig is not None


@pytest.mark.unit
def test_plot_B_matrix_3d() -> None:
    viz = MatrixVisualizer()
    B = np.zeros((2, 3, 3))
    B[0] = np.eye(3)
    B[1] = np.eye(3) * 0.5
    fig = viz.plot_B_matrix(B, action_idx=1)
    assert fig is not None


@pytest.mark.unit
def test_plot_C_vector() -> None:
    viz = MatrixVisualizer()
    C = np.array([0.0, 0.5, -1.0, 2.0, 0.1])
    fig = viz.plot_C_vector(C)
    assert fig is not None


@pytest.mark.unit
def test_plot_D_vector() -> None:
    viz = MatrixVisualizer()
    D = np.array([0.25, 0.25, 0.25, 0.25])
    fig = viz.plot_D_vector(D)
    assert fig is not None


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
    assert fig is not None


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
    assert fig is not None


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
    # Should still produce a Figure with empty subplots
    assert fig is not None


@pytest.mark.unit
def test_to_png_round_trip(tmp_path) -> None:
    viz = MatrixVisualizer()
    fig = viz.plot_C_vector(np.array([0.1, 0.9]))
    out = tmp_path / "fig.png"
    result = viz.to_png(fig, str(out), dpi=80)
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 0


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
