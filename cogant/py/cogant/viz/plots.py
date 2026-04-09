"""
Static plotter for HTML/SVG visualizations of COGANT models.

Generates bar charts, histograms, and tables using inline SVG.
"""

from typing import Dict, List, Optional, Any
from collections import Counter
import logging

from cogant.schemas.core import Node, Edge, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


class StaticPlotter:
    """Generate static HTML/SVG plots for COGANT models."""

    def __init__(self):
        """Initialize the StaticPlotter."""
        pass

    def plot_node_type_distribution(self, graph: ProgramGraph) -> str:
        """
        Generate HTML/SVG bar chart of node types using inline SVG.

        Args:
            graph: ProgramGraph to analyze.

        Returns:
            HTML string containing SVG bar chart.
        """
        # Count nodes by kind
        kind_counts: Dict[str, int] = {}
        for node in graph.nodes.values():
            kind_name = node.kind.value
            kind_counts[kind_name] = kind_counts.get(kind_name, 0) + 1

        sorted_kinds = sorted(kind_counts.items(), key=lambda x: x[1], reverse=True)

        # SVG parameters
        width = 600
        height = 400
        margin = {"top": 20, "right": 20, "bottom": 80, "left": 60}
        plot_width = width - margin["left"] - margin["right"]
        plot_height = height - margin["top"] - margin["bottom"]

        max_count = max((c for _, c in sorted_kinds), default=1)

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<style>',
            ".bar { fill: #4CAF50; }",
            ".axis { font-family: Arial; font-size: 12px; }",
            ".label { font-family: Arial; font-size: 11px; }",
            ".title { font-family: Arial; font-size: 16px; font-weight: bold; }",
            "</style>",
            f'<text x="{width/2}" y="20" class="title" text-anchor="middle">Node Type Distribution</text>',
        ]

        # Draw axes
        lines.append(
            f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"]}" y2="{height - margin["bottom"]}" stroke="black" stroke-width="2"/>'
        )
        lines.append(
            f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{height - margin["bottom"]}" stroke="black" stroke-width="2"/>'
        )

        # Draw bars
        bar_width = plot_width / len(sorted_kinds)
        for idx, (kind, count) in enumerate(sorted_kinds):
            x = margin["left"] + idx * bar_width + bar_width / 4
            bar_height = (count / max_count) * plot_height
            y = height - margin["bottom"] - bar_height

            lines.append(f'<rect x="{x}" y="{y}" width="{bar_width / 2}" height="{bar_height}" class="bar"/>')
            lines.append(
                f'<text x="{x + bar_width / 4}" y="{y - 5}" class="label" text-anchor="middle">{count}</text>'
            )

            # Label on x-axis
            label_x = x + bar_width / 4
            label_y = height - margin["bottom"] + 20
            lines.append(
                f'<text x="{label_x}" y="{label_y}" class="label" text-anchor="middle" transform="rotate(45 {label_x} {label_y})">{kind}</text>'
            )

        lines.append("</svg>")

        return "\n".join(lines)

    def plot_edge_type_distribution(self, graph: ProgramGraph) -> str:
        """
        Generate HTML/SVG bar chart of edge types.

        Args:
            graph: ProgramGraph to analyze.

        Returns:
            HTML string containing SVG bar chart.
        """
        # Count edges by kind
        kind_counts: Dict[str, int] = {}
        for edge in graph.edges.values():
            kind_name = edge.kind.value
            kind_counts[kind_name] = kind_counts.get(kind_name, 0) + 1

        sorted_kinds = sorted(kind_counts.items(), key=lambda x: x[1], reverse=True)

        # SVG parameters
        width = 600
        height = 400
        margin = {"top": 20, "right": 20, "bottom": 80, "left": 60}
        plot_width = width - margin["left"] - margin["right"]
        plot_height = height - margin["top"] - margin["bottom"]

        max_count = max((c for _, c in sorted_kinds), default=1)

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<style>',
            ".bar { fill: #2196F3; }",
            ".axis { font-family: Arial; font-size: 12px; }",
            ".label { font-family: Arial; font-size: 11px; }",
            ".title { font-family: Arial; font-size: 16px; font-weight: bold; }",
            "</style>",
            f'<text x="{width/2}" y="20" class="title" text-anchor="middle">Edge Type Distribution</text>',
        ]

        # Draw axes
        lines.append(
            f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"]}" y2="{height - margin["bottom"]}" stroke="black" stroke-width="2"/>'
        )
        lines.append(
            f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{height - margin["bottom"]}" stroke="black" stroke-width="2"/>'
        )

        # Draw bars
        bar_width = plot_width / len(sorted_kinds)
        for idx, (kind, count) in enumerate(sorted_kinds):
            x = margin["left"] + idx * bar_width + bar_width / 4
            bar_height = (count / max_count) * plot_height
            y = height - margin["bottom"] - bar_height

            lines.append(f'<rect x="{x}" y="{y}" width="{bar_width / 2}" height="{bar_height}" class="bar"/>')
            lines.append(
                f'<text x="{x + bar_width / 4}" y="{y - 5}" class="label" text-anchor="middle">{count}</text>'
            )

            # Label on x-axis
            label_x = x + bar_width / 4
            label_y = height - margin["bottom"] + 20
            lines.append(
                f'<text x="{label_x}" y="{label_y}" class="label" text-anchor="middle" transform="rotate(45 {label_x} {label_y})">{kind}</text>'
            )

        lines.append("</svg>")

        return "\n".join(lines)

    def plot_confidence_distribution(self, mappings: Dict[str, Any]) -> str:
        """
        Generate HTML/SVG histogram of mapping confidence scores.

        Args:
            mappings: Dict of semantic mappings with confidence scores.

        Returns:
            HTML string containing SVG histogram.
        """
        # Extract confidence scores. Accept both dict-shape mappings
        # ({"confidence": float, ...}) and object-shape mappings
        # (SemanticMapping with .confidence_score / .confidence).
        confidences: list = []
        for mapping_data in mappings.values():
            if isinstance(mapping_data, dict):
                if "confidence" in mapping_data:
                    confidences.append(mapping_data["confidence"])
                elif "confidence_score" in mapping_data:
                    confidences.append(mapping_data["confidence_score"])
            else:
                score = getattr(mapping_data, "confidence_score", None)
                if score is None:
                    score = getattr(mapping_data, "confidence", None)
                if isinstance(score, (int, float)):
                    confidences.append(float(score))

        if not confidences:
            # Return empty histogram
            return "<p>No confidence data available</p>"

        # Histogram bins
        bins = 10
        bin_counts = [0] * bins
        for conf in confidences:
            bin_idx = min(int(conf * bins), bins - 1)
            bin_counts[bin_idx] += 1

        # SVG parameters
        width = 600
        height = 400
        margin = {"top": 20, "right": 20, "bottom": 60, "left": 60}
        plot_width = width - margin["left"] - margin["right"]
        plot_height = height - margin["top"] - margin["bottom"]

        max_count = max(bin_counts) if bin_counts else 1

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<style>',
            ".bar { fill: #FF9800; }",
            ".axis { font-family: Arial; font-size: 12px; }",
            ".label { font-family: Arial; font-size: 11px; }",
            ".title { font-family: Arial; font-size: 16px; font-weight: bold; }",
            "</style>",
            f'<text x="{width/2}" y="20" class="title" text-anchor="middle">Confidence Score Distribution</text>',
        ]

        # Draw axes
        lines.append(
            f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"]}" y2="{height - margin["bottom"]}" stroke="black" stroke-width="2"/>'
        )
        lines.append(
            f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{height - margin["bottom"]}" stroke="black" stroke-width="2"/>'
        )

        # Draw bars
        bar_width = plot_width / bins
        for idx, count in enumerate(bin_counts):
            x = margin["left"] + idx * bar_width
            bar_height = (count / max_count) * plot_height if max_count > 0 else 0
            y = height - margin["bottom"] - bar_height

            lines.append(f'<rect x="{x}" y="{y}" width="{bar_width * 0.8}" height="{bar_height}" class="bar"/>')

            # Label on x-axis
            bin_label = f"{idx / bins:.1f}-{(idx + 1) / bins:.1f}"
            label_x = x + bar_width / 2
            label_y = height - margin["bottom"] + 20
            lines.append(
                f'<text x="{label_x}" y="{label_y}" class="label" text-anchor="middle" font-size="10">{bin_label}</text>'
            )

        lines.append("</svg>")

        return "\n".join(lines)

    def plot_state_space_matrix(self, state_space: StateSpaceModel) -> str:
        """
        Generate HTML table showing variable×observation matrix.

        Args:
            state_space: StateSpaceModel to visualize.

        Returns:
            HTML table string.
        """
        variables = list(state_space.variables.values())
        observations = list(state_space.observations.values())

        lines = [
            '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">',
            "<tr>",
            "<th>Variable</th>",
        ]

        # Add observation headers
        for obs in observations:
            lines.append(f"<th>{obs.name}</th>")
        lines.append("</tr>")

        # Add rows for each variable
        for var in variables:
            lines.append("<tr>")
            lines.append(f"<td><strong>{var.name}</strong></td>")

            # Add cells for observations
            for obs in observations:
                # Simple heuristic: if variable name or ID appears in observation, mark as related
                is_related = (
                    var.id in obs.source_node_id or var.name.lower() in obs.name.lower()
                )
                cell_content = "✓" if is_related else "–"
                lines.append(f"<td style='text-align: center;'>{cell_content}</td>")

            lines.append("</tr>")

        lines.append("</table>")

        return "\n".join(lines)

    def plot_state_space_matrix_html(self, state_space: StateSpaceModel, output_path: str) -> None:
        """
        Generate rich HTML page showing variable×observation and variable×action matrices.

        Args:
            state_space: StateSpaceModel to visualize.
            output_path: Path to save the HTML file.
        """
        variables = list(state_space.variables.values())
        observations = list(state_space.observations.values())
        actions = list(state_space.actions.values())

        # Build variable-observation connectivity map with confidence
        var_obs_connectivity: Dict[str, Dict[str, float]] = {}
        for var in variables:
            var_obs_connectivity[var.id] = {}
            for obs in observations:
                # Check if variable is related to observation
                is_related = (
                    var.id in obs.source_node_id or var.name.lower() in obs.name.lower()
                )
                confidence = 0.8 if is_related else 0.2
                var_obs_connectivity[var.id][obs.id] = confidence

        # Build variable-action connectivity map with confidence
        var_action_connectivity: Dict[str, Dict[str, float]] = {}
        for var in variables:
            var_action_connectivity[var.id] = {}
            for action in actions:
                # Check if variable is affected by action (via effects list)
                is_affected = (
                    var.id in action.effects or var.name.lower() in action.name.lower()
                )
                confidence = 0.7 if is_affected else 0.3
                var_action_connectivity[var.id][action.id] = confidence

        # Generate HTML
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            '    <meta charset="utf-8">',
            "    <title>State Space Matrix</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }",
            "        h1 { color: #333; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }",
            "        h2 { color: #555; margin-top: 30px; }",
            "        .matrix-container { background: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
            "        table { width: 100%; border-collapse: collapse; margin: 20px 0; }",
            "        th { background: #0066cc; color: white; padding: 10px; text-align: left; font-weight: bold; }",
            "        td { padding: 8px; border: 1px solid #ddd; }",
            "        tr:nth-child(even) { background: #f9f9f9; }",
            "        tr:hover { background: #f0f0f0; }",
            "        .var-name { font-weight: bold; color: #0066cc; }",
            "        .confidence-cell {",
            "            text-align: center;",
            "            font-weight: bold;",
            "            border-radius: 3px;",
            "        }",
            "        .conf-high { background: #4CAF50; color: white; }",
            "        .conf-medium { background: #FFC107; color: black; }",
            "        .conf-low { background: #999; color: white; }",
            "        .legend { margin: 20px 0; padding: 10px; background: white; border-radius: 5px; }",
            "        .legend-item { display: inline-block; margin: 0 15px; }",
            "        .legend-box { display: inline-block; width: 20px; height: 20px; margin-right: 5px; border-radius: 3px; vertical-align: middle; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>State Space Matrix: {state_space.schema_name}</h1>",
            "    <div class='legend'>",
            "        <strong>Confidence Levels:</strong>",
            "        <div class='legend-item'><div class='legend-box conf-high'></div>High (0.7-1.0)</div>",
            "        <div class='legend-item'><div class='legend-box conf-medium'></div>Medium (0.4-0.7)</div>",
            "        <div class='legend-item'><div class='legend-box conf-low'></div>Low (0.0-0.4)</div>",
            "    </div>",
        ]

        # Variable × Observation Matrix
        html_parts.extend([
            "    <div class='matrix-container'>",
            "        <h2>Variable × Observation Matrix</h2>",
            "        <p>Shows which observations connect to which state variables.</p>",
            "        <table>",
            "            <tr>",
            "                <th>Variable</th>",
        ])

        for obs in observations:
            html_parts.append(f"                <th>{obs.name}</th>")

        html_parts.append("            </tr>")

        for var in variables:
            html_parts.append("            <tr>")
            html_parts.append(f"                <td class='var-name'>{var.name}</td>")

            for obs in observations:
                conf = var_obs_connectivity[var.id][obs.id]
                conf_class = "conf-high" if conf >= 0.7 else ("conf-medium" if conf >= 0.4 else "conf-low")
                html_parts.append(f"                <td class='confidence-cell {conf_class}'>{conf:.2f}</td>")

            html_parts.append("            </tr>")

        html_parts.extend([
            "        </table>",
            "    </div>",
        ])

        # Variable × Action Matrix
        html_parts.extend([
            "    <div class='matrix-container'>",
            "        <h2>Variable × Action Matrix</h2>",
            "        <p>Shows which actions affect which state variables.</p>",
            "        <table>",
            "            <tr>",
            "                <th>Variable</th>",
        ])

        for action in actions:
            html_parts.append(f"                <th>{action.name}</th>")

        html_parts.append("            </tr>")

        for var in variables:
            html_parts.append("            <tr>")
            html_parts.append(f"                <td class='var-name'>{var.name}</td>")

            for action in actions:
                conf = var_action_connectivity[var.id][action.id]
                conf_class = "conf-high" if conf >= 0.7 else ("conf-medium" if conf >= 0.4 else "conf-low")
                html_parts.append(f"                <td class='confidence-cell {conf_class}'>{conf:.2f}</td>")

            html_parts.append("            </tr>")

        html_parts.extend([
            "        </table>",
            "    </div>",
            "</body>",
            "</html>",
        ])

        # Write HTML file
        with open(output_path, "w") as f:
            f.write("\n".join(html_parts))

    def plot_factor_graph(self, state_space: StateSpaceModel, output_path: str) -> None:
        """
        Generate SVG showing the factor graph structure.

        Args:
            state_space: StateSpaceModel to visualize.
            output_path: Path to save the SVG file.
        """
        variables = list(state_space.variables.values())
        observations = list(state_space.observations.values())
        actions = list(state_space.actions.values())

        # SVG parameters
        width = 1200
        height = 800
        margin = 60
        grid_width = (width - 2 * margin) / 4
        grid_height = (height - 2 * margin) / 3

        # Position nodes
        var_positions = {}
        for i, var in enumerate(variables):
            row = i // 3
            col = i % 3
            x = margin + col * grid_width + grid_width / 2
            y = margin + row * grid_height + grid_height / 2
            var_positions[var.id] = (x, y)

        obs_positions = {}
        for i, obs in enumerate(observations):
            x = margin + 3 * grid_width + grid_width / 2
            y = margin + (i % 3) * grid_height + grid_height / 2
            obs_positions[obs.id] = (x, y)

        action_positions = {}
        for i, action in enumerate(actions):
            row = i // 2
            col = i % 2
            x = margin + (0.5 + col) * grid_width
            y = margin + 2.5 * grid_height + row * 80
            action_positions[action.id] = (x, y)

        # Generate SVG
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<defs>',
            "    <style>",
            "        .var-circle { fill: #90CAF9; stroke: #0066cc; stroke-width: 2; }",
            "        .obs-rect { fill: #A5D6A7; stroke: #2E7D32; stroke-width: 2; }",
            "        .action-diamond { fill: #FFB74D; stroke: #F57C00; stroke-width: 2; }",
            "        .label { font-family: Arial; font-size: 11px; text-anchor: middle; }",
            "        .title { font-family: Arial; font-size: 18px; font-weight: bold; }",
            "        .edge { stroke: #333; stroke-width: 1; fill: none; }",
            "        .factor { fill: black; }",
            "    </style>",
            "</defs>",
            f'<text x="{width/2}" y="30" class="title" text-anchor="middle">Factor Graph Structure</text>',
        ]

        # Draw edges (factors)
        for var_id, var in state_space.variables.items():
            if var_id not in var_positions:
                continue
            var_x, var_y = var_positions[var_id]

            # Edges to observations
            for obs_id in obs_positions:
                obs_x, obs_y = obs_positions[obs_id]
                # Draw edge
                lines.append(
                    f'<line x1="{var_x}" y1="{var_y}" x2="{obs_x}" y2="{obs_y}" class="edge" stroke-dasharray="2,2"/>'
                )
                # Draw factor node (black dot at midpoint)
                mid_x = (var_x + obs_x) / 2
                mid_y = (var_y + obs_y) / 2
                lines.append(f'<circle cx="{mid_x}" cy="{mid_y}" r="3" class="factor"/>')

            # Edges to actions
            for action_id in action_positions:
                action_x, action_y = action_positions[action_id]
                lines.append(
                    f'<line x1="{var_x}" y1="{var_y}" x2="{action_x}" y2="{action_y}" class="edge"/>'
                )

        # Draw state variable nodes (circles)
        for var in variables:
            if var.id not in var_positions:
                continue
            x, y = var_positions[var.id]
            lines.append(f'<circle cx="{x}" cy="{y}" r="25" class="var-circle"/>')
            label = var.name[:15]
            lines.append(f'<text x="{x}" y="{y}" class="label" dy="0.3em">{label}</text>')

        # Draw observation nodes (squares)
        for obs in observations:
            if obs.id not in obs_positions:
                continue
            x, y = obs_positions[obs.id]
            lines.append(f'<rect x="{x-20}" y="{y-20}" width="40" height="40" class="obs-rect"/>')
            label = obs.name[:15]
            lines.append(f'<text x="{x}" y="{y}" class="label" dy="0.3em">{label}</text>')

        # Draw action nodes (diamonds)
        for action in actions:
            if action.id not in action_positions:
                continue
            x, y = action_positions[action.id]
            diamond_points = f"{x},{ y-20} {x+20},{y} {x},{y+20} {x-20},{y}"
            lines.append(f'<polygon points="{diamond_points}" class="action-diamond"/>')
            label = action.name[:12]
            lines.append(f'<text x="{x}" y="{y}" class="label" dy="0.3em">{label}</text>')

        # Add legend
        legend_y = height - 80
        lines.extend([
            f'<g id="legend">',
            f'  <text x="80" y="{legend_y}" class="label" text-anchor="start" font-size="12" font-weight="bold">Legend:</text>',
            f'  <circle cx="80" cy="{legend_y + 20}" r="12" class="var-circle"/>',
            f'  <text x="100" y="{legend_y + 25}" class="label" text-anchor="start" font-size="10">State Variable</text>',
            f'  <rect x="235" y="{legend_y + 8}" width="24" height="24" class="obs-rect"/>',
            f'  <text x="270" y="{legend_y + 25}" class="label" text-anchor="start" font-size="10">Observation</text>',
            f'  <polygon points="420,{legend_y + 20} 432,{legend_y + 32} 420,{legend_y + 44} 408,{legend_y + 32}" class="action-diamond"/>',
            f'  <text x="450" y="{legend_y + 25}" class="label" text-anchor="start" font-size="10">Action</text>',
            f'</g>',
        ])

        lines.append("</svg>")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

    def plot_ontology_sunburst(self, graph: ProgramGraph, mappings: Dict[str, Any], output_path: str) -> None:
        """
        Generate SVG sunburst diagram showing ontology structure.

        Args:
            graph: ProgramGraph to analyze.
            mappings: Semantic mappings.
            output_path: Path to save the SVG file.
        """
        # Count nodes by kind
        kind_counts: Dict[str, int] = {}
        for node in graph.nodes.values():
            kind_str = str(node.kind).replace("NodeKind.", "")
            kind_counts[kind_str] = kind_counts.get(kind_str, 0) + 1

        # Count semantic roles
        role_counts: Dict[str, int] = {}
        for mapping_id, mapping in mappings.items():
            role = getattr(mapping, 'kind', type(mapping).__name__)
            if hasattr(role, 'value'):
                role = role.value
            role_str = str(role).replace("SemanticMappingKind.", "")
            role_counts[role_str] = role_counts.get(role_str, 0) + 1

        # SVG parameters
        width = 800
        height = 800
        center_x = width / 2
        center_y = height / 2
        inner_radius = 60
        middle_radius = 150
        outer_radius = 280

        # Get repository name from metadata or graph
        repo_name = "Repository"
        if hasattr(graph, 'metadata') and hasattr(graph.metadata, 'repo_name'):
            repo_name = graph.metadata.repo_name[:20]

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<defs>',
            "    <style>",
            "        .center-text { font-family: Arial; font-size: 14px; font-weight: bold; text-anchor: middle; }",
            "        .ring-label { font-family: Arial; font-size: 10px; text-anchor: middle; }",
            "        .ring1-segment { fill: #FF6B6B; stroke: white; stroke-width: 2; }",
            "        .ring2-segment { fill: #4ECDC4; stroke: white; stroke-width: 2; }",
            "        .ring1-segment:hover { fill: #FF5252; }",
            "        .ring2-segment:hover { fill: #2DB8A6; }",
            "    </style>",
            "</defs>",
            f'<circle cx="{center_x}" cy="{center_y}" r="{inner_radius}" fill="#FFE66D" stroke="#F4A460" stroke-width="2"/>',
            f'<text x="{center_x}" y="{center_y}" class="center-text" dy="0.3em">{repo_name}</text>',
        ]

        # Draw first ring (node kinds) with colors
        kind_colors = {
            "CLASS": "#E74C3C", "FUNCTION": "#3498DB", "METHOD": "#2ECC71",
            "MODULE": "#F39C12", "VARIABLE": "#9B59B6", "PARAMETER": "#1ABC9C"
        }

        total_kinds = sum(kind_counts.values())
        angle_start: float = 0.0
        for kind_name, count in sorted(kind_counts.items(), key=lambda x: x[1], reverse=True):
            angle_size = (count / total_kinds) * 360 if total_kinds > 0 else 0
            angle_mid = angle_start + angle_size / 2
            angle_end = angle_start + angle_size

            # Convert to radians
            start_rad = (angle_start - 90) * 3.14159 / 180
            end_rad = (angle_end - 90) * 3.14159 / 180
            mid_rad = (angle_mid - 90) * 3.14159 / 180

            # Draw segment
            x1 = center_x + inner_radius * (angle_start - 90)**0 * 0 + inner_radius * 0.707
            y1 = center_y + inner_radius * (angle_start - 90)**0 * 0 + inner_radius * 0.707

            # SVG arc path
            large_arc = 1 if angle_size > 180 else 0
            path = (f"M {center_x},{center_y} "
                   f"L {center_x + middle_radius * __import__('math').cos(start_rad):.1f},"
                   f"{center_y + middle_radius * __import__('math').sin(start_rad):.1f} "
                   f"A {middle_radius},{middle_radius} 0 {large_arc},1 "
                   f"{center_x + middle_radius * __import__('math').cos(end_rad):.1f},"
                   f"{center_y + middle_radius * __import__('math').sin(end_rad):.1f} Z")

            color = kind_colors.get(kind_name, "#95A5A6")
            lines.append(f'<path d="{path}" class="ring1-segment" fill="{color}"/>')

            # Add label
            label_r = inner_radius + 40
            label_x = center_x + label_r * __import__('math').cos(mid_rad)
            label_y = center_y + label_r * __import__('math').sin(mid_rad)
            lines.append(f'<text x="{label_x:.1f}" y="{label_y:.1f}" class="ring-label">{kind_name} ({count})</text>')

            angle_start = angle_end

        # Draw second ring (semantic roles)
        total_roles = sum(role_counts.values())
        angle_start = 0
        for role_name, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True):
            angle_size = (count / total_roles) * 360 if total_roles > 0 else 0
            angle_mid = angle_start + angle_size / 2
            angle_end = angle_start + angle_size

            # Convert to radians
            start_rad = (angle_start - 90) * 3.14159 / 180
            end_rad = (angle_end - 90) * 3.14159 / 180
            mid_rad = (angle_mid - 90) * 3.14159 / 180

            # SVG arc path
            large_arc = 1 if angle_size > 180 else 0
            path = (f"M {center_x + middle_radius * __import__('math').cos(start_rad):.1f},"
                   f"{center_y + middle_radius * __import__('math').sin(start_rad):.1f} "
                   f"L {center_x + outer_radius * __import__('math').cos(start_rad):.1f},"
                   f"{center_y + outer_radius * __import__('math').sin(start_rad):.1f} "
                   f"A {outer_radius},{outer_radius} 0 {large_arc},1 "
                   f"{center_x + outer_radius * __import__('math').cos(end_rad):.1f},"
                   f"{center_y + outer_radius * __import__('math').sin(end_rad):.1f} "
                   f"L {center_x + middle_radius * __import__('math').cos(end_rad):.1f},"
                   f"{center_y + middle_radius * __import__('math').sin(end_rad):.1f} Z")

            lines.append(f'<path d="{path}" class="ring2-segment"/>')

            # Add label
            label_r = (middle_radius + outer_radius) / 2
            label_x = center_x + label_r * __import__('math').cos(mid_rad)
            label_y = center_y + label_r * __import__('math').sin(mid_rad)
            lines.append(f'<text x="{label_x:.1f}" y="{label_y:.1f}" class="ring-label">{role_name} ({count})</text>')

            angle_start = angle_end

        lines.append("</svg>")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

    def plot_confidence_radar(self, mappings: Dict[str, Any], output_path: str) -> None:
        """
        Generate SVG radar/spider chart showing confidence by mapping kind.

        Args:
            mappings: Semantic mappings with confidence scores.
            output_path: Path to save the SVG file.
        """
        import math

        # Group mappings by kind and calculate mean confidence
        kind_confidence: Dict[str, List[float]] = {}
        for mapping_id, mapping in mappings.items():
            kind = getattr(mapping, 'kind', type(mapping).__name__)
            if hasattr(kind, 'value'):
                kind = kind.value
            kind_str = str(kind).replace("SemanticMappingKind.", "")

            confidence = 0.5
            if hasattr(mapping, 'confidence'):
                confidence = mapping.confidence
            elif isinstance(mapping, dict) and 'confidence' in mapping:
                confidence = mapping['confidence']

            if kind_str not in kind_confidence:
                kind_confidence[kind_str] = []
            kind_confidence[kind_str].append(confidence)

        # Calculate means
        kind_means = {k: sum(v) / len(v) for k, v in kind_confidence.items()}
        if not kind_means:
            kind_means = {"unknown": 0.5}

        # SVG parameters
        width = 600
        height = 600
        center_x = width / 2
        center_y = height / 2
        max_radius = 200
        num_axes = len(kind_means)

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<defs>',
            "    <style>",
            "        .axis-line { stroke: #999; stroke-width: 1; }",
            "        .grid-circle { stroke: #ddd; stroke-width: 1; fill: none; }",
            "        .radar-polygon { fill: #4CAF50; fill-opacity: 0.3; stroke: #2E7D32; stroke-width: 2; }",
            "        .axis-label { font-family: Arial; font-size: 11px; text-anchor: middle; }",
            "        .grid-label { font-family: Arial; font-size: 9px; fill: #999; }",
            "        .title { font-family: Arial; font-size: 16px; font-weight: bold; text-anchor: middle; }",
            "    </style>",
            "</defs>",
            f'<text x="{center_x}" y="20" class="title">Confidence Radar</text>',
        ]

        # Draw grid circles (0.0, 0.25, 0.5, 0.75, 1.0)
        for conf_level in [0.25, 0.5, 0.75, 1.0]:
            radius = max_radius * conf_level
            lines.append(
                f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" class="grid-circle"/>'
            )
            lines.append(
                f'<text x="{center_x + radius}" y="{center_y - 5}" class="grid-label">{conf_level:.2f}</text>'
            )

        # Draw axes and labels
        axis_points = []
        for i, kind_name in enumerate(sorted(kind_means.keys())):
            angle = (i / num_axes) * 2 * math.pi - math.pi / 2
            x_end = center_x + max_radius * math.cos(angle)
            y_end = center_y + max_radius * math.sin(angle)

            lines.append(
                f'<line x1="{center_x}" y1="{center_y}" x2="{x_end}" y2="{y_end}" class="axis-line"/>'
            )

            # Label
            label_r = max_radius + 30
            label_x = center_x + label_r * math.cos(angle)
            label_y = center_y + label_r * math.sin(angle)
            lines.append(
                f'<text x="{label_x:.1f}" y="{label_y:.1f}" class="axis-label">{kind_name}</text>'
            )

            axis_points.append((angle, kind_means[kind_name]))

        # Draw radar polygon
        polygon_points = []
        for angle, confidence in axis_points:
            radius = max_radius * min(confidence, 1.0)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            polygon_points.append(f"{x:.1f},{y:.1f}")

        if polygon_points:
            polygon_str = " ".join(polygon_points)
            lines.append(f'<polygon points="{polygon_str}" class="radar-polygon"/>')

        # Draw data points
        for angle, confidence in axis_points:
            radius = max_radius * min(confidence, 1.0)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#2E7D32"/>')

        lines.append("</svg>")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))
