"""
Visualization for Active Inference simulations.

Generates SVG plots and HTML reports of simulation traces.
"""

from collections import defaultdict
from typing import Any


class SimulationVisualizer:
    """Generate visualizations of simulation traces."""

    def __init__(self) -> None:
        """Initialize the visualizer."""
        pass

    def plot_free_energy_trajectory(self, trace: list[dict[str, Any]]) -> str:
        """
        Generate SVG plot of free energy over time.

        Args:
            trace: List of simulation steps, each with 'free_energy' key.

        Returns:
            SVG string.
        """
        if not trace:
            return self._empty_svg("No trace data")

        # Extract free energy values
        fe_values = []
        for step in trace:
            fe = step.get("free_energy", 0.0)
            if isinstance(fe, int | float):
                fe_values.append(float(fe))
            else:
                fe_values.append(0.0)

        if not fe_values:
            return self._empty_svg("No free energy data")

        # Compute bounds
        min_fe = min(fe_values)
        max_fe = max(fe_values)
        range_fe = max_fe - min_fe if max_fe != min_fe else 1.0

        # SVG parameters
        width, height = 800, 400
        margin = 60
        plot_width = width - 2 * margin
        plot_height = height - 2 * margin

        # Build SVG
        svg_lines = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<style>',
            "  .axis { stroke: #333; stroke-width: 1; }",
            "  .grid { stroke: #ddd; stroke-width: 0.5; }",
            "  .line { stroke: #0066cc; stroke-width: 2; fill: none; }",
            "  .point { fill: #0066cc; }",
            "  .text { font-family: Arial; font-size: 12px; }",
            "  .title { font-family: Arial; font-size: 16px; font-weight: bold; }",
            "</style>",
            f'<text x="{width/2}" y="25" text-anchor="middle" class="title">Free Energy Trajectory</text>',
        ]

        # Draw axes
        svg_lines.append(
            f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" class="axis"/>'
        )
        svg_lines.append(
            f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" class="axis"/>'
        )

        # Draw grid and labels
        n_steps = len(fe_values)
        for i in range(n_steps + 1):
            x = margin + (i / n_steps) * plot_width
            svg_lines.append(
                f'<line x1="{x}" y1="{height - margin}" x2="{x}" y2="{height - margin + 3}" class="axis"/>'
            )
            if i % max(1, n_steps // 5) == 0:
                svg_lines.append(
                    f'<text x="{x}" y="{height - margin + 20}" text-anchor="middle" class="text">{i}</text>'
                )

        # Draw free energy line
        if len(fe_values) > 1:
            path_parts = []
            for i, fe in enumerate(fe_values):
                x = margin + (i / (n_steps - 1)) * plot_width
                y = height - margin - ((fe - min_fe) / range_fe) * plot_height
                if i == 0:
                    path_parts.append(f"M {x} {y}")
                else:
                    path_parts.append(f"L {x} {y}")
            svg_lines.append(f'<path d="{" ".join(path_parts)}" class="line"/>')

            # Draw points
            for i, fe in enumerate(fe_values):
                x = margin + (i / (n_steps - 1)) * plot_width
                y = height - margin - ((fe - min_fe) / range_fe) * plot_height
                svg_lines.append(
                    f'<circle cx="{x}" cy="{y}" r="3" class="point" opacity="0.6"/>'
                )

        # Draw y-axis labels
        for i in range(5):
            fe_label = min_fe + (i / 4) * range_fe
            y = height - margin - (i / 4) * plot_height
            svg_lines.append(
                f'<text x="{margin - 10}" y="{y + 3}" text-anchor="end" class="text">{fe_label:.2f}</text>'
            )

        svg_lines.append("</svg>")
        return "\n".join(svg_lines)

    def plot_belief_evolution(self, trace: list[dict[str, Any]]) -> str:
        """
        Generate SVG showing belief evolution over time.

        Args:
            trace: List of simulation steps, each with 'beliefs' key (dict of state -> prob).

        Returns:
            SVG string.
        """
        if not trace:
            return self._empty_svg("No trace data")

        # Extract beliefs
        all_states: set[str] = set()
        belief_history = []

        for step in trace:
            beliefs = step.get("beliefs", {})
            if isinstance(beliefs, dict):
                belief_history.append(beliefs)
                all_states.update(beliefs.keys())
            else:
                belief_history.append({})

        if not belief_history or not all_states:
            return self._empty_svg("No belief data")

        states = sorted(all_states)
        colors = self._generate_colors(len(states))

        # SVG parameters
        width, height = 900, 400
        margin = 60
        plot_width = width - 2 * margin
        plot_height = height - 2 * margin

        # Build SVG
        svg_lines = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<style>',
            "  .axis { stroke: #333; stroke-width: 1; }",
            "  .text { font-family: Arial; font-size: 12px; }",
            "  .title { font-family: Arial; font-size: 16px; font-weight: bold; }",
            "  .legend { font-family: Arial; font-size: 11px; }",
            "</style>",
            f'<text x="{width/2}" y="25" text-anchor="middle" class="title">Belief Evolution</text>',
        ]

        # Draw axes
        svg_lines.append(
            f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" class="axis"/>'
        )
        svg_lines.append(
            f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" class="axis"/>'
        )

        # Draw stacked area chart
        n_steps = len(belief_history)
        for state_idx, _state in enumerate(states):
            cumulative = [0.0] * n_steps
            for i in range(n_steps):
                beliefs = belief_history[i]
                cumulative[i] = sum(
                    beliefs.get(s, 0.0) for s in states[:state_idx + 1]
                )

            # Generate path for this state
            path_parts = []
            for i in range(n_steps):
                x = margin + (i / max(1, n_steps - 1)) * plot_width
                y = height - margin - (cumulative[i] * plot_height)
                if i == 0:
                    path_parts.append(f"M {x} {y}")
                else:
                    path_parts.append(f"L {x} {y}")

            # Close path
            for i in range(n_steps - 1, -1, -1):
                x = margin + (i / max(1, n_steps - 1)) * plot_width
                if state_idx == 0:
                    y = height - margin
                else:
                    prev_cumulative = sum(
                        belief_history[i].get(s, 0.0) for s in states[:state_idx]
                    )
                    y = height - margin - (prev_cumulative * plot_height)
                if i == n_steps - 1:
                    path_parts.append(f"L {x} {y}")
                else:
                    path_parts.append(f"L {x} {y}")

            path_parts.append("Z")
            color = colors[state_idx]
            svg_lines.append(
                f'<path d="{" ".join(path_parts)}" fill="{color}" opacity="0.7"/>'
            )

        # Add legend
        legend_x = width - 150
        for state_idx, state in enumerate(states):
            y = margin + 20 + state_idx * 18
            color = colors[state_idx]
            svg_lines.append(f'<rect x="{legend_x}" y="{y - 10}" width="12" height="12" fill="{color}"/>')
            svg_lines.append(
                f'<text x="{legend_x + 18}" y="{y}" class="legend">{state[:15]}</text>'
            )

        # X-axis labels
        for i in range(n_steps):
            if i % max(1, n_steps // 5) == 0:
                x = margin + (i / max(1, n_steps - 1)) * plot_width
                svg_lines.append(
                    f'<text x="{x}" y="{height - margin + 20}" text-anchor="middle" class="text">{i}</text>'
                )

        svg_lines.append("</svg>")
        return "\n".join(svg_lines)

    def plot_action_distribution(self, trace: list[dict[str, Any]]) -> str:
        """
        Generate SVG bar chart of actions taken.

        Args:
            trace: List of simulation steps, each with 'action' key.

        Returns:
            SVG string.
        """
        if not trace:
            return self._empty_svg("No trace data")

        # Count actions
        action_counts: dict[str, int] = defaultdict(int)
        for step in trace:
            action = step.get("action")
            if action:
                action_counts[action] += 1

        if not action_counts:
            return self._empty_svg("No action data")

        actions = sorted(action_counts.keys())
        counts = [action_counts[a] for a in actions]
        max_count = max(counts) if counts else 1

        # SVG parameters
        bar_width = 40
        spacing = 20
        width = len(actions) * (bar_width + spacing) + 100
        height = 400
        margin = 60
        plot_height = height - 2 * margin

        # Build SVG
        svg_lines = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<style>',
            "  .bar { fill: #0066cc; }",
            "  .axis { stroke: #333; stroke-width: 1; }",
            "  .text { font-family: Arial; font-size: 12px; }",
            "  .title { font-family: Arial; font-size: 16px; font-weight: bold; }",
            "</style>",
            f'<text x="{width/2}" y="25" text-anchor="middle" class="title">Action Distribution</text>',
        ]

        # Draw axes
        svg_lines.append(
            f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" class="axis"/>'
        )
        svg_lines.append(
            f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" class="axis"/>'
        )

        # Draw bars
        for i, action in enumerate(actions):
            count = action_counts[action]
            bar_height = (count / max_count) * plot_height if max_count > 0 else 0
            x = margin + i * (bar_width + spacing) + spacing // 2
            y = height - margin - bar_height

            svg_lines.append(
                f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" class="bar"/>'
            )
            svg_lines.append(
                f'<text x="{x + bar_width/2}" y="{height - margin + 20}" text-anchor="middle" class="text">{action[:10]}</text>'
            )
            svg_lines.append(
                f'<text x="{x + bar_width/2}" y="{y - 5}" text-anchor="middle" class="text">{count}</text>'
            )

        svg_lines.append("</svg>")
        return "\n".join(svg_lines)

    def generate_mermaid_trajectory(self, trace: list[dict[str, Any]]) -> str:
        """
        Generate Mermaid sequence diagram of state transitions.

        Args:
            trace: List of simulation steps.

        Returns:
            Mermaid diagram string.
        """
        if not trace or len(trace) < 2:
            return "graph LR\n  A[No transitions]"

        lines = ["sequenceDiagram"]
        lines.append("  participant Agent")
        lines.append("  participant Environment")

        for i in range(len(trace) - 1):
            current = trace[i]
            next_step = trace[i + 1]

            state = current.get("state", f"s{i}")
            action = next_step.get("action", "wait")
            next_state = next_step.get("state", f"s{i+1}")

            # Format state info
            state_str = str(state)[:20]
            action_str = str(action)[:15]
            next_state_str = str(next_state)[:20]

            lines.append(f"  Agent->>Environment: {action_str} @ {state_str}")
            lines.append(f"  Environment->>Agent: → {next_state_str}")

        return "\n".join(lines)

    def generate_html_report(
        self, trace: list[dict[str, Any]], state_space: Any
    ) -> str:
        """
        Generate full HTML report of simulation.

        Args:
            trace: List of simulation steps.
            state_space: The state space model (for metadata).

        Returns:
            HTML string.
        """
        # Generate individual visualizations
        fe_plot = self.plot_free_energy_trajectory(trace)
        belief_plot = self.plot_belief_evolution(trace)
        action_plot = self.plot_action_distribution(trace)
        mermaid_diagram = self.generate_mermaid_trajectory(trace)

        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "  <meta charset='utf-8'>",
            "  <title>Active Inference Simulation Report</title>",
            "  <script src='https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js'></script>",
            "  <style>",
            "    body { font-family: Arial; margin: 20px; background: #f5f5f5; }",
            "    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; }",
            "    h1 { color: #333; }",
            "    .section { margin: 30px 0; }",
            "    .plot { border: 1px solid #ddd; padding: 10px; margin: 10px 0; }",
            "    .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }",
            "    .stat-box { background: #f9f9f9; padding: 15px; border-radius: 5px; }",
            "    .stat-value { font-size: 24px; font-weight: bold; color: #0066cc; }",
            "    .stat-label { color: #666; margin-top: 5px; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <div class='container'>",
            "    <h1>Active Inference Simulation Report</h1>",
            f"    <p>Generated for state space: {state_space.schema_name if hasattr(state_space, 'schema_name') else 'Unknown'}</p>",
        ]

        # Statistics
        html_lines.extend([
            "    <div class='section stats'>",
            f"      <div class='stat-box'><div class='stat-value'>{len(trace)}</div><div class='stat-label'>Steps</div></div>",
            f"      <div class='stat-box'><div class='stat-value'>{len({s.get('action') for s in trace if s.get('action')})}</div><div class='stat-label'>Unique Actions</div></div>",
        ])

        # Add mean free energy if available
        fe_values = [s.get("free_energy", 0) for s in trace if isinstance(s.get("free_energy"), int | float)]
        if fe_values:
            mean_fe = sum(fe_values) / len(fe_values)
            html_lines.append(
                f"      <div class='stat-box'><div class='stat-value'>{mean_fe:.3f}</div><div class='stat-label'>Mean Free Energy</div></div>"
            )

        html_lines.append("    </div>")

        # Plots
        html_lines.extend([
            "    <div class='section'>",
            "      <h2>Free Energy Trajectory</h2>",
            f"      <div class='plot'>{fe_plot}</div>",
            "    </div>",
            "    <div class='section'>",
            "      <h2>Belief Evolution</h2>",
            f"      <div class='plot'>{belief_plot}</div>",
            "    </div>",
            "    <div class='section'>",
            "      <h2>Action Distribution</h2>",
            f"      <div class='plot'>{action_plot}</div>",
            "    </div>",
            "    <div class='section'>",
            "      <h2>State Transition Sequence</h2>",
            f"      <div class='mermaid'>{mermaid_diagram}</div>",
            "    </div>",
            "  </div>",
            "  <script>mermaid.initialize({{ startOnLoad: true }}); mermaid.contentLoaded();</script>",
            "</body>",
            "</html>",
        ])

        return "\n".join(html_lines)

    @staticmethod
    def _empty_svg(message: str) -> str:
        """Generate an empty SVG with a message."""
        return f"""<svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
  <text x="200" y="100" text-anchor="middle" font-size="16" fill="#999">{message}</text>
</svg>"""

    @staticmethod
    def _generate_colors(n: int) -> list[str]:
        """Generate n distinct colors."""
        colors = [
            "#FF6B6B",
            "#4ECDC4",
            "#45B7D1",
            "#FFA07A",
            "#98D8C8",
            "#F7DC6F",
            "#BB8FCE",
            "#85C1E2",
        ]
        if n <= len(colors):
            return colors[:n]

        # Generate additional colors
        result = colors.copy()
        for i in range(n - len(colors)):
            hue = (i * 360) / (n - len(colors))
            # Simple HSL to hex conversion
            result.append(f"hsl({hue}, 70%, 50%)")

        return result
