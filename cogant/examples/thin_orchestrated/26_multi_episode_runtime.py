#!/usr/bin/env python3
"""Thin example: Multi-episode Active Inference runtime with VFE tracking.

This script demonstrates:

  1. Build minimal POMDP matrices dict (3 hidden states, 2 observations, 2 actions).
  2. Create ``AgentRuntime.from_matrices_dict(...)`` with the matrices.
  3. Run 5 episodes of 4 steps each using ``run_multi_episode(...)``.
  4. After each episode, extract and print the VFE (variational free energy).
  5. Show matrix updates (D prior and A likelihood) as learning occurs.
  6. Print an ASCII-style VFE trajectory.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/26_multi_episode_runtime.py \\
        --output-dir output/thin/multi_episode_runtime
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, parse_args  # noqa: E402

from cogant.runtime.loop import AgentRuntime  # noqa: E402


def _print_matrix_summary(label: str, matrix, max_cols: int = 8) -> None:
    """Pretty-print a matrix with row/col summaries."""
    if not matrix:
        print(f"    {label}: (empty)")
        return
    print(f"    {label}:")
    for i, row in enumerate(matrix[:3]):  # Show first 3 rows
        if isinstance(row, (list, tuple)):
            vals_str = " ".join(f"{v:.3f}" for v in row[:max_cols])
            print(f"      row {i}: [{vals_str}]")
        else:
            print(f"      row {i}: {row:.3f}")
    if len(matrix) > 3:
        print(f"      ... ({len(matrix)} rows total)")


def _plot_ascii_trajectory(vfe_trajectory: list[float]) -> None:
    """Print an ASCII-style plot of VFE over episodes."""
    if not vfe_trajectory:
        print("    (empty trajectory)")
        return

    min_vfe = min(vfe_trajectory)
    max_vfe = max(vfe_trajectory)
    range_vfe = max_vfe - min_vfe if max_vfe > min_vfe else 1.0

    print("    VFE trajectory (ASCII plot):")
    width = 50
    for i, vfe in enumerate(vfe_trajectory):
        if range_vfe > 0:
            norm = (vfe - min_vfe) / range_vfe
        else:
            norm = 0.5
        pos = int(norm * (width - 1))
        bar = " " * pos + "*" + " " * (width - pos - 1)
        print(f"      ep {i}: |{bar}| {vfe:.4f}")

    print(f"    min={min_vfe:.4f}  max={max_vfe:.4f}  delta={max_vfe - min_vfe:.4f}")


def main() -> int:
    """Entry point for the multi-episode runtime demo."""
    args = parse_args("multi_episode_runtime")
    configure_logging()
    banner("Stage 26: Multi-episode Active Inference runtime")

    # 1. Build minimal POMDP matrices
    # 3 hidden states, 2 observations, 2 actions
    n_states = 3
    n_obs = 2
    n_actions = 2

    A = [
        [0.9, 0.1, 0.2],  # obs 0: likely in state 0
        [0.1, 0.9, 0.8],  # obs 1: likely in states 1 or 2
    ]

    B = [
        # B[i][j][a] = p(state_i | state_j, action_a)
        [
            [1.0, 0.0, 0.5],  # action 0: transition to state 0
            [0.0, 1.0, 0.5],  # action 1: transition to state 1
        ],
        [
            [1.0, 0.0, 0.5],
            [0.0, 1.0, 0.5],
        ],
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ],
    ]

    C = [0.0, 1.0]  # Preference: prefer obs 1 (reward)

    D = [0.5, 0.3, 0.2]  # Prior belief: mostly state 0, less state 2

    matrices_dict = {
        "A": A,
        "B": B,
        "C": C,
        "D": D,
    }

    print("  matrices:")
    print(f"    n_states={n_states}  n_obs={n_obs}  n_actions={n_actions}")

    # 2. Create runtime
    print("\n  creating AgentRuntime...")
    rt = AgentRuntime.from_matrices_dict(matrices_dict)
    print("    ✓ runtime initialized")
    print(f"    internal state: {len(rt.D)} states, {len(rt.A)} observations")

    # 3. Run multi-episode with learning
    n_episodes = 5
    steps_per_episode = 4
    learning_rate = 0.1

    print(f"\n  running {n_episodes} episodes × {steps_per_episode} steps:")
    print(f"    learning_rate={learning_rate}")
    print("    " + "-" * 50)

    result = rt.run_multi_episode(
        n_episodes=n_episodes,
        steps_per_episode=steps_per_episode,
        learning_rate=learning_rate,
    )

    # 4. Print per-episode summary
    print("\n  episode results:")
    for i, episode in enumerate(result.episodes):
        mean_vfe = episode.mean_free_energy
        final_vfe = episode.final_free_energy
        print(
            f"    episode {i}: steps={len(episode.steps):2d}  "
            f"mean_vfe={mean_vfe:+.4f}  final_vfe={final_vfe:+.4f}"
        )

    # 5. Show D prior trajectory (learning)
    print("\n  D prior trajectory (learning over episodes):")
    for i, D_snap in enumerate(result.D_trajectory):
        D_str = " ".join(f"{d:.3f}" for d in D_snap)
        print(f"    after ep {i}: D = [{D_str}]")

    # 6. Show A likelihood trajectory (sample first row)
    print("\n  A matrix trajectory (first row only):")
    print(f"    initial:  {rt.A[0]}")
    # Note: A updates happen in-place during run_multi_episode, so
    # the current rt.A reflects the final learned state
    print(f"    final:    {rt.A[0]}")

    # 7. Print VFE trajectory and ASCII plot
    print("\n  variational free energy trajectory:")
    _plot_ascii_trajectory(result.vfe_trajectory)

    # 8. Summary stats
    if result.vfe_trajectory:
        vfe_delta = result.vfe_trajectory[-1] - result.vfe_trajectory[0]
        print("\n  learning summary:")
        print(f"    vfe_delta (final - initial): {vfe_delta:+.4f}")
        print(f"    episode_count: {len(result.episodes)}")
        print(f"    learning_rate: {result.learning_rate}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  output dir: {args.output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
