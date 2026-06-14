"""
Matrix visualization for Active Inference models.

Visualizes A/B/C/D matrices as heatmaps and bar charts:
- A: Likelihood (observation model) heatmap
- B: State transition heatmap (per action)
- C: Preference vector (goal prior) bar chart
- D: Initial state prior distribution bar chart
- Combined 2x2 grid view of all matrices
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _clip_labels(labels: list[str] | None, n: int) -> list[str] | None:
    """Return labels clipped to ``n`` entries."""
    if not labels:
        return None
    return [str(label) for label in labels[:n]]


class MatrixVisualizer:
    """Visualize Active Inference A/B/C/D matrices."""

    def __init__(self) -> None:
        """Initialize the MatrixVisualizer."""
        pass

    def _select_B_slice(self, B_array: Any, action_idx: int = 0) -> tuple[Any, str]:
        """Select a transition matrix from either common B tensor convention.

        COGANT mostly emits Active-Inference-style ``(state, state, action)``
        tensors, while some older tests and examples use
        ``(action, state, state)``. This helper makes the visualizer honest
        about which convention it selected.
        """
        import numpy as np

        if B_array.ndim != 3:
            return B_array, "2D"

        if B_array.shape[0] == B_array.shape[1] and action_idx < B_array.shape[2]:
            return B_array[:, :, action_idx], "state_state_action"
        if action_idx < B_array.shape[0]:
            return B_array[action_idx, :, :], "action_state_state"

        clipped = max(0, min(action_idx, B_array.shape[-1] - 1))
        return np.asarray(B_array[:, :, clipped]), "state_state_action_clipped"

    def summarize_matrices(self, matrices: dict[str, Any], action_idx: int = 0) -> dict[str, Any]:
        """Return shape and probability diagnostics for A/B/C/D matrices.

        The summary is designed for human interpretability and manuscript
        captions rather than for numerical validation gates. For probability
        matrices it reports the maximum column-sum error from 1.0; for vectors
        it reports total mass and extrema.
        """
        try:
            import numpy as np
        except ImportError:
            logger.warning("numpy not available; skipping matrix diagnostics")
            return {}

        summary: dict[str, Any] = {}

        def _matrix_stats(name: str, value: Any) -> None:
            arr = np.asarray(value, dtype=float)
            if arr.size == 0:
                summary[name] = {"shape": tuple(arr.shape), "empty": True}
                return
            if arr.ndim == 1:
                total = float(arr.sum())
                summary[name] = {
                    "shape": tuple(arr.shape),
                    "sum": total,
                    "min": float(arr.min()),
                    "max": float(arr.max()),
                    "max_probability_error": abs(total - 1.0),
                }
                return
            col_sums = arr.sum(axis=0)
            summary[name] = {
                "shape": tuple(arr.shape),
                "min": float(arr.min()),
                "max": float(arr.max()),
                "column_sum_min": float(col_sums.min()),
                "column_sum_max": float(col_sums.max()),
                "max_probability_error": float(np.max(np.abs(col_sums - 1.0))),
            }

        if "A" in matrices:
            _matrix_stats("A", matrices["A"])
        if "B" in matrices:
            B_array = np.asarray(matrices["B"], dtype=float)
            B_slice, convention = self._select_B_slice(B_array, action_idx)
            _matrix_stats("B", B_slice)
            summary.setdefault("B", {})["tensor_shape"] = tuple(B_array.shape)
            summary["B"]["slice_convention"] = convention
            if B_array.ndim == 3:
                summary["B"]["action_count"] = (
                    B_array.shape[2]
                    if convention.startswith("state_state_action")
                    else B_array.shape[0]
                )
        if "C" in matrices:
            _matrix_stats("C", matrices["C"])
        if "D" in matrices:
            _matrix_stats("D", matrices["D"])

        return summary

    def plot_A_matrix(self, A: Any, labels: list[str] | None = None) -> Any:
        """
        Plot the likelihood matrix (A) as a heatmap.

        A represents the probability of observations given hidden states.
        Shape typically: (num_observations, num_hidden_states).

        Args:
            A: Likelihood matrix (2D array-like).
            labels: Optional observation/state labels.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping A matrix plot")
            return None

        try:
            fig, ax = plt.subplots(figsize=(10, 8))

            A_array = np.asarray(A, dtype=float)
            empty = A_array.size == 0
            if empty:
                A_array = np.zeros((1, 1), dtype=float)
            im = ax.imshow(A_array, cmap="YlGnBu", aspect="auto", origin="lower", vmin=0.0)

            ax.set_xlabel("Hidden States")
            ax.set_ylabel("Observations")
            # On empty data, label the no-data case explicitly rather than
            # drawing a single blue cell under the normal title (which reads as
            # a legitimate 1-state model). Matches plot_C_vector/plot_D_vector.
            if empty:
                ax.set_title("A Matrix: no data")
                ax.text(
                    0.5, 0.5, "no A-matrix data",
                    ha="center", va="center", transform=ax.transAxes,
                )
            else:
                ax.set_title("A Matrix: Likelihood (Observation Model)")

            plt.colorbar(im, ax=ax, label="Probability")

            clipped = _clip_labels(labels, A_array.shape[1])
            if clipped:
                ax.set_xticks(range(len(clipped)))
                ax.set_xticklabels(clipped, rotation=45, ha="right")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting A matrix: {e}")
            return None

    def plot_B_matrix(self, B: Any, action_idx: int = 0) -> Any:
        """
        Plot a state transition matrix (B) slice as a heatmap.

        B represents the probability of next state given current state and action.
        For simplicity, visualize one action's transition matrix.

        Args:
            B: Transition matrix (3D array-like for multiple actions or 2D for single).
            action_idx: Index of action to visualize (ignored if B is 2D).

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping B matrix plot")
            return None

        try:
            fig, ax = plt.subplots(figsize=(10, 8))

            B_array = np.asarray(B, dtype=float)
            empty = B_array.size == 0
            if empty:
                B_array = np.zeros((1, 1), dtype=float)

            B_slice, convention = self._select_B_slice(B_array, action_idx)

            im = ax.imshow(B_slice, cmap="PuBuGn", aspect="auto", origin="lower", vmin=0.0)

            ax.set_xlabel("Current State")
            ax.set_ylabel("Next State")
            # Label the no-data case rather than drawing a blank cell under the
            # normal title (consistent with plot_A_matrix / plot_C_vector).
            if empty:
                ax.set_title("B Matrix: no data")
                ax.text(
                    0.5, 0.5, "no B-matrix data",
                    ha="center", va="center", transform=ax.transAxes,
                )
            else:
                ax.set_title(f"B Matrix: State Transition (Action {action_idx}, {convention})")

            plt.colorbar(im, ax=ax, label="Probability")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting B matrix: {e}")
            return None

    def plot_C_vector(self, C: Any) -> Any:
        """
        Plot the preference vector (C) as a bar chart.

        C represents the agent's goals (preferred observations).

        Args:
            C: Preference vector (1D array-like).

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping C vector plot")
            return None

        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            C_array = np.asarray(C, dtype=float).flatten()
            if C_array.size == 0:
                C_array = np.array([0.0])
                ax.text(0, 0, "No C data", ha="center", va="bottom", color="#666666")

            ax.bar(range(len(C_array)), C_array, color="#2ca25f", alpha=0.85)
            ax.set_xlabel("Observation")
            ax.set_ylabel("Preference (Log Probability)")
            ax.set_title("C Vector: Goal Prior")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting C vector: {e}")
            return None

    def plot_D_vector(self, D: Any) -> Any:
        """
        Plot the initial state prior (D) as a bar chart.

        D represents the agent's prior belief about the initial hidden state.

        Args:
            D: Initial state distribution (1D array-like).

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping D vector plot")
            return None

        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            D_array = np.asarray(D, dtype=float).flatten()
            if D_array.size == 0:
                D_array = np.array([0.0])
                ax.text(0, 0, "No D data", ha="center", va="bottom", color="#666666")

            ax.bar(range(len(D_array)), D_array, color="#756bb1", alpha=0.85)
            ax.set_xlabel("Hidden State")
            ax.set_ylabel("Prior Probability")
            ax.set_title("D Vector: Initial State Prior")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting D vector: {e}")
            return None

    def plot_all_matrices(self, matrices: dict[str, Any]) -> Any:
        """
        Plot all four matrices in a 2x2 grid.

        Args:
            matrices: Dict with keys 'A', 'B', 'C', 'D' and numeric arrays as values.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping matrices plot")
            return None

        try:
            fig, axes = plt.subplots(2, 2, figsize=(14, 12))

            # A matrix
            A = np.asarray(matrices.get("A", []), dtype=float)
            if A.size > 0:
                im_a = axes[0, 0].imshow(A, cmap="YlGnBu", aspect="auto", origin="lower", vmin=0.0)
                axes[0, 0].set_title("A Matrix: Likelihood")
                axes[0, 0].set_xlabel("Hidden States")
                axes[0, 0].set_ylabel("Observations")
                plt.colorbar(im_a, ax=axes[0, 0])
            else:
                axes[0, 0].imshow(np.zeros((1, 1)), cmap="YlGnBu", aspect="auto", vmin=0.0)
                axes[0, 0].set_title("A Matrix: no data")
                axes[0, 0].set_xticks([])
                axes[0, 0].set_yticks([])

            # B matrix
            B = np.asarray(matrices.get("B", []), dtype=float)
            if B.size > 0:
                B_slice, convention = self._select_B_slice(B, 0)
                im_b = axes[0, 1].imshow(
                    B_slice, cmap="PuBuGn", aspect="auto", origin="lower", vmin=0.0
                )
                axes[0, 1].set_title(f"B Matrix: Transition ({convention})")
                axes[0, 1].set_xlabel("Current State")
                axes[0, 1].set_ylabel("Next State")
                plt.colorbar(im_b, ax=axes[0, 1])
            else:
                axes[0, 1].imshow(np.zeros((1, 1)), cmap="PuBuGn", aspect="auto", vmin=0.0)
                axes[0, 1].set_title("B Matrix: no data")
                axes[0, 1].set_xticks([])
                axes[0, 1].set_yticks([])

            # C vector
            C = np.asarray(matrices.get("C", []), dtype=float).flatten()
            if C.size > 0:
                axes[1, 0].bar(range(len(C)), C, color="#2ca25f", alpha=0.85)
                axes[1, 0].set_title("C Vector: Goal Prior")
                axes[1, 0].set_xlabel("Observation")
                axes[1, 0].set_ylabel("Preference")
            else:
                axes[1, 0].bar([0], [0], color="#2ca25f", alpha=0.2)
                axes[1, 0].text(0, 0, "No C data", ha="center", va="bottom", color="#666666")
                axes[1, 0].set_title("C Vector: no data")

            # D vector
            D = np.asarray(matrices.get("D", []), dtype=float).flatten()
            if D.size > 0:
                axes[1, 1].bar(range(len(D)), D, color="#756bb1", alpha=0.85)
                axes[1, 1].set_title("D Vector: Initial State Prior")
                axes[1, 1].set_xlabel("Hidden State")
                axes[1, 1].set_ylabel("Prior Probability")
            else:
                axes[1, 1].bar([0], [0], color="#756bb1", alpha=0.2)
                axes[1, 1].text(0, 0, "No D data", ha="center", va="bottom", color="#666666")
                axes[1, 1].set_title("D Vector: no data")

            fig.suptitle("Active Inference Matrices (A/B/C/D)", fontsize=16, weight="bold")
            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting matrices: {e}")
            return None

    def plot_interpretability_panel(
        self,
        matrices: dict[str, Any],
        *,
        labels: dict[str, list[str]] | None = None,
        action_idx: int = 0,
    ) -> Any:
        """Render a one-page visual + diagnostic panel for a generative model."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping interpretability panel")
            return None

        try:
            summary = self.summarize_matrices(matrices, action_idx=action_idx)
            fig = plt.figure(figsize=(16, 10))
            gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35)

            ax_a = fig.add_subplot(gs[0, 0])
            A = np.asarray(matrices.get("A", []), dtype=float)
            if A.size:
                im = ax_a.imshow(A, cmap="YlGnBu", aspect="auto", origin="lower", vmin=0.0)
                fig.colorbar(im, ax=ax_a, fraction=0.046, pad=0.04)
                ax_a.set_title("A: observations given state")
                ax_a.set_xlabel("hidden state")
                ax_a.set_ylabel("observation")
                obs_labels = _clip_labels((labels or {}).get("observations"), A.shape[0])
                state_labels = _clip_labels((labels or {}).get("states"), A.shape[1])
                if obs_labels:
                    ax_a.set_yticks(range(len(obs_labels)))
                    ax_a.set_yticklabels(obs_labels)
                if state_labels:
                    ax_a.set_xticks(range(len(state_labels)))
                    ax_a.set_xticklabels(state_labels, rotation=45, ha="right")
            else:
                ax_a.text(0.5, 0.5, "No A matrix", ha="center", va="center")
                ax_a.set_axis_off()

            ax_b = fig.add_subplot(gs[0, 1])
            B = np.asarray(matrices.get("B", []), dtype=float)
            if B.size:
                B_slice, convention = self._select_B_slice(B, action_idx)
                im = ax_b.imshow(B_slice, cmap="PuBuGn", aspect="auto", origin="lower", vmin=0.0)
                fig.colorbar(im, ax=ax_b, fraction=0.046, pad=0.04)
                ax_b.set_title(f"B: transitions ({convention})")
                ax_b.set_xlabel("current state")
                ax_b.set_ylabel("next state")
            else:
                ax_b.text(0.5, 0.5, "No B matrix", ha="center", va="center")
                ax_b.set_axis_off()

            ax_c = fig.add_subplot(gs[0, 2])
            C = np.asarray(matrices.get("C", []), dtype=float).flatten()
            if C.size:
                ax_c.bar(range(len(C)), C, color="#2ca25f", alpha=0.85)
                ax_c.axhline(0, color="#333333", linewidth=0.8)
                ax_c.set_title("C: preferences")
                ax_c.set_xlabel("observation")
            else:
                ax_c.text(0.5, 0.5, "No C vector", ha="center", va="center")
                ax_c.set_axis_off()

            ax_d = fig.add_subplot(gs[1, 0])
            D = np.asarray(matrices.get("D", []), dtype=float).flatten()
            if D.size:
                ax_d.bar(range(len(D)), D, color="#756bb1", alpha=0.85)
                ax_d.set_title("D: initial belief")
                ax_d.set_xlabel("hidden state")
                ax_d.set_ylabel("probability")
            else:
                ax_d.text(0.5, 0.5, "No D vector", ha="center", va="center")
                ax_d.set_axis_off()

            ax_diag = fig.add_subplot(gs[1, 1:])
            ax_diag.set_axis_off()
            lines = ["Matrix diagnostics"]
            for key in ("A", "B", "C", "D"):
                stats = summary.get(key, {})
                if not stats:
                    continue
                shape = stats.get("shape")
                err = stats.get("max_probability_error")
                if err is not None:
                    lines.append(f"{key}: shape={shape}, max probability error={err:.3g}")
                else:
                    lines.append(
                        f"{key}: shape={shape}, min={stats.get('min')}, max={stats.get('max')}"
                    )
                if key == "B" and stats.get("action_count") is not None:
                    lines.append(
                        f"   B tensor={stats.get('tensor_shape')}, actions={stats.get('action_count')}, "
                        f"slice={stats.get('slice_convention')}"
                    )
            ax_diag.text(
                0.02,
                0.96,
                "\n".join(lines),
                ha="left",
                va="top",
                family="monospace",
                fontsize=11,
                bbox={"boxstyle": "round,pad=0.6", "facecolor": "#f7f8fb", "edgecolor": "#dfe2e8"},
            )

            fig.suptitle("Generative Model Interpretability Panel", fontsize=16, weight="bold")
            fig.subplots_adjust(top=0.90)
            return fig

        except Exception as e:
            logger.error(f"Error plotting interpretability panel: {e}")
            return None

    def to_png(self, fig: Any, output_path: str, dpi: int = 150) -> str:
        """
        Save a matplotlib figure to PNG.

        Args:
            fig: Matplotlib Figure object.
            output_path: Path to write PNG file.
            dpi: Resolution in dots per inch.

        Returns:
            Path to rendered file, or empty string if save fails.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping PNG save")
            return ""

        if fig is None:
            logger.warning("Figure is None; skipping PNG save")
            return ""

        try:
            fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
            logger.info(f"Saved figure to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving PNG: {e}")
            return ""
        finally:
            plt.close(fig)

    def to_pdf(self, fig: Any, output_path: str) -> str:
        """
        Save a matplotlib figure to PDF.

        Args:
            fig: Matplotlib Figure object.
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if save fails.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping PDF save")
            return ""

        if fig is None:
            logger.warning("Figure is None; skipping PDF save")
            return ""

        try:
            fig.savefig(output_path, format="pdf", bbox_inches="tight")
            logger.info(f"Saved figure to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving PDF: {e}")
            return ""
        finally:
            plt.close(fig)
