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


class MatrixVisualizer:
    """Visualize Active Inference A/B/C/D matrices."""

    def __init__(self) -> None:
        """Initialize the MatrixVisualizer."""
        pass

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
            im = ax.imshow(A_array, cmap="YlOrRd", aspect="auto", origin="lower")

            ax.set_xlabel("Hidden States")
            ax.set_ylabel("Observations")
            ax.set_title("A Matrix: Likelihood (Observation Model)")

            plt.colorbar(im, ax=ax, label="Probability")

            if labels:
                ax.set_xticks(range(min(len(labels), A_array.shape[1])))
                ax.set_xticklabels(labels[: A_array.shape[1]], rotation=45, ha="right")

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

            # Handle both 2D and 3D cases
            if B_array.ndim == 3:
                B_slice = B_array[action_idx]
            else:
                B_slice = B_array

            im = ax.imshow(B_slice, cmap="Blues", aspect="auto", origin="lower")

            ax.set_xlabel("Current State")
            ax.set_ylabel("Next State")
            ax.set_title(f"B Matrix: State Transition (Action {action_idx})")

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

            ax.bar(range(len(C_array)), C_array, color="green", alpha=0.7)
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

            ax.bar(range(len(D_array)), D_array, color="purple", alpha=0.7)
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
                im_a = axes[0, 0].imshow(A, cmap="YlOrRd", aspect="auto", origin="lower")
                axes[0, 0].set_title("A Matrix: Likelihood")
                axes[0, 0].set_xlabel("Hidden States")
                axes[0, 0].set_ylabel("Observations")
                plt.colorbar(im_a, ax=axes[0, 0])

            # B matrix
            B = np.asarray(matrices.get("B", []), dtype=float)
            if B.size > 0:
                B_slice = B[0] if B.ndim == 3 else B
                im_b = axes[0, 1].imshow(B_slice, cmap="Blues", aspect="auto", origin="lower")
                axes[0, 1].set_title("B Matrix: Transition")
                axes[0, 1].set_xlabel("Current State")
                axes[0, 1].set_ylabel("Next State")
                plt.colorbar(im_b, ax=axes[0, 1])

            # C vector
            C = np.asarray(matrices.get("C", []), dtype=float).flatten()
            if C.size > 0:
                axes[1, 0].bar(range(len(C)), C, color="green", alpha=0.7)
                axes[1, 0].set_title("C Vector: Goal Prior")
                axes[1, 0].set_xlabel("Observation")
                axes[1, 0].set_ylabel("Preference")

            # D vector
            D = np.asarray(matrices.get("D", []), dtype=float).flatten()
            if D.size > 0:
                axes[1, 1].bar(range(len(D)), D, color="purple", alpha=0.7)
                axes[1, 1].set_title("D Vector: Initial State Prior")
                axes[1, 1].set_xlabel("Hidden State")
                axes[1, 1].set_ylabel("Prior Probability")

            fig.suptitle("Active Inference Matrices (A/B/C/D)", fontsize=16, weight="bold")
            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting matrices: {e}")
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

        try:
            if fig is None:
                logger.warning("Figure is None; skipping PNG save")
                return ""

            fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Saved figure to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving PNG: {e}")
            return ""

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

        try:
            if fig is None:
                logger.warning("Figure is None; skipping PDF save")
                return ""

            fig.savefig(output_path, format="pdf", bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Saved figure to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving PDF: {e}")
            return ""
