from __future__ import annotations

from collections import defaultdict
from typing import Any


def generate_report(trace: list[dict[str, Any]]) -> str:
    """
    Generate markdown report of Active Inference simulation.

    Args:
        trace: Trace from run_active_inference().

    Returns:
        Markdown string.
    """
    lines = [
        "# Active Inference Simulation Report",
        "",
        "## Summary",
        f"- Total steps: {len(trace)}",
        "- Initial beliefs: declared prior D",
        "",
        "## Free Energy Dynamics",
        "",
    ]

    # Extract free energy trajectory
    fe_values = [step.get("free_energy", 0.0) for step in trace]
    if fe_values:
        mean_fe = sum(fe_values) / len(fe_values)
        min_fe = min(fe_values)
        max_fe = max(fe_values)
        lines.extend(
            [
                f"- Mean VFE: {mean_fe:.4f}",
                f"- Min VFE: {min_fe:.4f}",
                f"- Max VFE: {max_fe:.4f}",
                "",
            ]
        )

    # Action distribution
    lines.append("## Actions Taken")
    action_counts: dict[str, int] = defaultdict(int)
    for step in trace:
        action = step.get("action")
        if action:
            action_counts[action] += 1

    if action_counts:
        lines.append("")
        for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {action}: {count} times")
    else:
        lines.append("- No actions taken")

    lines.append("")

    # Belief trajectory sample
    lines.extend(
        [
            "## Belief Evolution (Sample)",
            "",
        ]
    )

    sample_indices = [
        0,
        len(trace) // 4,
        len(trace) // 2,
        (3 * len(trace)) // 4,
        len(trace) - 1,
    ]
    sample_indices = sorted({i for i in sample_indices if 0 <= i < len(trace)})

    for idx in sample_indices:
        step = trace[idx]
        beliefs = step.get("beliefs", {})
        lines.append(f"### Step {step.get('step', idx)}")
        if beliefs:
            top_beliefs = sorted(beliefs.items(), key=lambda x: x[1], reverse=True)[:3]
            for state, prob in top_beliefs:
                lines.append(f"- {state}: {prob:.4f}")
        lines.append("")

    return "\n".join(lines)
