"""
DashboardGenerator: Production-quality interactive HTML dashboard.

Generates a single self-contained HTML file with tabbed navigation,
embedded SVG charts, Mermaid diagrams, and comprehensive data views.
"""

import html
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import defaultdict
from pathlib import Path
import logging

from cogant.schemas.core import Node, Edge, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import SemanticMapping, MappingKind
from cogant.statespace.compiler import StateSpaceModel
from cogant.process.extractor import ProcessModel
from cogant.validate.report import ValidationReport

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """
    Generates a production-quality, self-contained HTML dashboard
    with tabbed interface, embedded charts, and comprehensive visualizations.
    """

    def __init__(
        self,
        graph: ProgramGraph,
        state_space: StateSpaceModel,
        process_model: ProcessModel,
        semantic_mappings: Dict[str, SemanticMapping],
        mermaid_diagrams: Dict[str, str],
        validation_report: ValidationReport,
        repo_name: str,
        output_dir: Optional[Path] = None,
        trace_data: Optional[Dict[str, Any]] = None,
        gnn_validation: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize dashboard generator.

        Args:
            graph: Program graph
            state_space: State space model
            process_model: Process model
            semantic_mappings: Dict of mapping_id -> SemanticMapping
            mermaid_diagrams: Dict of diagram_name -> diagram_content
            validation_report: Validation report
            repo_name: Repository name for header
            output_dir: Optional path to output directory for loading trace/validation data
            trace_data: Optional active inference trace data
            gnn_validation: Optional GNN validation report data
        """
        self.graph = graph
        self.state_space = state_space
        self.process_model = process_model
        self.semantic_mappings = semantic_mappings or {}
        self.mermaid_diagrams = mermaid_diagrams or {}
        self.validation_report = validation_report
        self.repo_name = repo_name
        self.output_dir = output_dir
        self.trace_data = trace_data
        self.gnn_validation = gnn_validation

        # Load trace and validation data if available
        self._load_optional_data()

    def generate(self) -> str:
        """
        Generate complete self-contained HTML dashboard.

        Returns:
            Complete HTML string ready for output
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        version = getattr(self.validation_report, "schema_name", "v0.1.0")

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>COGANT Dashboard - {html.escape(self.repo_name)}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
{self._generate_css()}
    </style>
</head>
<body>
    <div class="dashboard">
{self._generate_header(timestamp, version)}
{self._generate_summary_cards()}
{self._generate_tab_navigation()}
{self._generate_tab_content()}
    </div>
    <script>
{self._generate_javascript()}
    </script>
</body>
</html>
"""
        return html_doc

    def _generate_css(self) -> str:
        """Return inline CSS (externalised in :mod:`cogant.viz.dashboard.assets`)."""
        from cogant.viz.dashboard.assets import DASHBOARD_CSS
        return DASHBOARD_CSS

    def _generate_header(self, timestamp: str, version: str) -> str:
        """Generate header section."""
        return f"""
    <header>
        <h1>COGANT Dashboard</h1>
        <div class="header-meta">
            <span><strong>Repository:</strong> {html.escape(self.repo_name)}</span>
            <span><strong>Generated:</strong> {timestamp}</span>
            <span><strong>Version:</strong> {version}</span>
        </div>
    </header>
"""

    def _generate_summary_cards(self) -> str:
        """Generate summary metrics cards."""
        num_nodes = len(self.graph.nodes)
        num_edges = len(self.graph.edges)
        num_state_vars = len(self.state_space.variables) if self.state_space else 0
        num_observations = len(self.state_space.observations) if self.state_space else 0
        num_actions = len(self.state_space.actions) if self.state_space else 0
        num_mappings = len(self.semantic_mappings)

        confidence = getattr(self.validation_report, "confidence_score", 0.0)
        is_valid = getattr(self.validation_report, "is_valid", False)

        return f"""
    <div class="container">
        <div class="summary-cards">
            <div class="card">
                <h3>Nodes</h3>
                <div class="card-value">{num_nodes}</div>
            </div>
            <div class="card">
                <h3>Edges</h3>
                <div class="card-value">{num_edges}</div>
            </div>
            <div class="card">
                <h3>State Variables</h3>
                <div class="card-value">{num_state_vars}</div>
            </div>
            <div class="card">
                <h3>Observations</h3>
                <div class="card-value">{num_observations}</div>
            </div>
            <div class="card">
                <h3>Actions</h3>
                <div class="card-value">{num_actions}</div>
            </div>
            <div class="card">
                <h3>Semantic Mappings</h3>
                <div class="card-value">{num_mappings}</div>
            </div>
            <div class="card">
                <h3>Confidence Score</h3>
                <div class="card-value">{confidence*100:.1f}%</div>
                <div class="card-subtext">
                    <span class="badge {'badge-pass' if is_valid else 'badge-fail'}">
                        {'✓ Valid' if is_valid else '✗ Issues'}
                    </span>
                </div>
            </div>
        </div>
    </div>
"""

    def _generate_tab_navigation(self) -> str:
        """Generate tab navigation buttons."""
        tabs = [
            "Overview",
            "Graph",
            "State Space",
            "Process Flow",
            "Factor Graph",
            "Active Inference",
            "GNN Package",
            "Semantic Mappings",
            "Validation",
        ]
        buttons = "".join(
            f'<button class="tab-button {"active" if i == 0 else ""}" onclick="switchTab(event, \'{tab.lower().replace(" ", "-")}\')">{tab}</button>'
            for i, tab in enumerate(tabs)
        )
        return f'    <div class="tabs">{buttons}</div>'

    def _generate_tab_content(self) -> str:
        """Generate all tab content sections."""
        return f"""
{self._generate_overview_tab()}
{self._generate_graph_tab()}
{self._generate_state_space_tab()}
{self._generate_process_flow_tab()}
{self._generate_factor_graph_tab()}
{self._generate_active_inference_tab()}
{self._generate_gnn_package_tab()}
{self._generate_semantic_mappings_tab()}
{self._generate_validation_tab()}
"""

    def _load_optional_data(self) -> None:
        """Load optional trace and validation data from output directory."""
        if not self.output_dir:
            return

        output_path = Path(self.output_dir) if not isinstance(self.output_dir, Path) else self.output_dir

        # Load active inference trace
        if not self.trace_data:
            trace_file = output_path / "active_inference_trace.json"
            if not trace_file.exists():
                trace_file = output_path / "simulation_trace.json"
            if trace_file.exists():
                try:
                    with open(trace_file, "r") as f:
                        self.trace_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load trace data: {e}")

        # Load GNN validation report
        if not self.gnn_validation:
            gnn_file = output_path / "gnn_validation_report.json"
            if gnn_file.exists():
                try:
                    with open(gnn_file, "r") as f:
                        self.gnn_validation = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load GNN validation: {e}")

    def _generate_overview_tab(self) -> str:
        """Generate Overview tab with charts and findings."""
        chart_svg = self._generate_node_distribution_chart()
        edge_chart_svg = self._generate_edge_distribution_chart()
        mapping_chart_svg = self._generate_mapping_kind_pie_chart()

        findings = self._generate_key_findings()

        return f"""
    <div id="overview" class="tab-content active">
        <div class="container">
            <h2>Overview</h2>

            <div class="grid-2">
                <div class="chart-container">
                    <div class="chart-title">Node Distribution</div>
                    {chart_svg}
                </div>
                <div class="chart-container">
                    <div class="chart-title">Edge Distribution</div>
                    {edge_chart_svg}
                </div>
            </div>

            <div class="chart-container">
                <div class="chart-title">Mapping Kind Distribution</div>
                {mapping_chart_svg}
            </div>

            <div class="chart-container">
                <div class="chart-title">Key Findings</div>
                {findings}
            </div>
        </div>
    </div>
"""

    def _generate_node_distribution_chart(self) -> str:
        """Generate node distribution bar chart as inline SVG."""
        if not self.graph.nodes:
            return "<p>No nodes to display</p>"

        # Count nodes by kind
        kind_counts: Dict[str, int] = defaultdict(int)
        for node in self.graph.nodes.values():
            kind_counts[node.kind.value] += 1

        kinds = sorted(kind_counts.keys())
        counts = [kind_counts[k] for k in kinds]
        max_count = max(counts) if counts else 1

        # Generate SVG
        width, height = 800, 250
        bar_width = width / len(kinds) if kinds else width
        chart_html = self._create_bar_chart(kinds, counts, max_count, width, height)
        return chart_html

    def _generate_edge_distribution_chart(self) -> str:
        """Generate edge distribution bar chart as inline SVG."""
        if not self.graph.edges:
            return "<p>No edges to display</p>"

        # Count edges by kind
        kind_counts: Dict[str, int] = defaultdict(int)
        for edge in self.graph.edges.values():
            kind_counts[edge.kind.value] += 1

        kinds = sorted(kind_counts.keys())
        counts = [kind_counts[k] for k in kinds]
        max_count = max(counts) if counts else 1

        chart_html = self._create_bar_chart(kinds, counts, max_count, 800, 250)
        return chart_html

    def _create_bar_chart(self, labels: List[str], values: List[int], max_val: int, width: int, height: int) -> str:
        """Create a simple SVG bar chart."""
        if not labels or not values:
            return '<p>No data to display</p>'

        padding = 40
        chart_width = width - 2 * padding
        chart_height = height - 2 * padding

        svg_parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">']

        # Background
        svg_parts.append(f'<rect width="{width}" height="{height}" fill="rgba(20,20,30,0.8)" rx="4"/>')

        # Bars
        bar_width = chart_width / len(labels)
        for i, (label, value) in enumerate(zip(labels, values)):
            x = padding + i * bar_width
            bar_height = (value / max_val) * chart_height if max_val > 0 else 0
            y = padding + chart_height - bar_height

            # Bar
            svg_parts.append(
                f'<rect x="{x+5}" y="{y}" width="{bar_width-10}" height="{bar_height}" '
                f'fill="url(#gradient)" rx="4"/>'
            )

            # Label
            svg_parts.append(
                f'<text x="{x+bar_width/2}" y="{height-10}" text-anchor="middle" '
                f'font-size="11" fill="#b0b0b0" transform="rotate(-15 {x+bar_width/2} {height-10})">'
                f'{label[:10]}</text>'
            )

            # Value
            svg_parts.append(
                f'<text x="{x+bar_width/2}" y="{y-5}" text-anchor="middle" '
                f'font-size="12" font-weight="bold" fill="#667eea">{value}</text>'
            )

        # Gradient
        svg_parts.append(
            '<defs>'
            '<linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">'
            '<stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />'
            '<stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />'
            '</linearGradient>'
            '</defs>'
        )

        svg_parts.append('</svg>')
        return "".join(svg_parts)

    def _generate_mapping_kind_pie_chart(self) -> str:
        """Generate mapping kind distribution pie chart."""
        if not self.semantic_mappings:
            return "<p>No semantic mappings to display</p>"

        # Count mappings by kind
        kind_counts: Dict[str, int] = defaultdict(int)
        for mapping in self.semantic_mappings.values():
            kind = getattr(mapping, "kind", "unknown")
            if hasattr(kind, "value"):
                kind_counts[kind.value] += 1
            else:
                kind_counts[str(kind)] += 1

        kinds = list(kind_counts.keys())
        counts = [kind_counts[k] for k in kinds]
        total = sum(counts)

        # Simple pie chart using SVG
        size = 300
        cx, cy = size / 2, size / 2
        radius = size / 2 - 30

        colors = ["#667eea", "#764ba2", "#f093fb", "#4facfe", "#43e97b", "#fa709a", "#fee140", "#30b0fe"]
        svg_parts = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">']

        angle = 0
        for i, (kind, count) in enumerate(zip(kinds, counts)):
            slice_angle = (count / total) * 360
            color = colors[i % len(colors)]

            # Calculate path
            start_angle = angle * (3.14159 / 180)
            end_angle = (angle + slice_angle) * (3.14159 / 180)

            x1 = cx + radius * (3.14159 / 180) * (angle + slice_angle / 2)
            y1 = cy + radius * (3.14159 / 180) * (angle + slice_angle / 2)

            large_arc = 1 if slice_angle > 180 else 0

            # Simplified: just use circles colored by angle
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
                f'stroke="{color}" stroke-width="30" '
                f'stroke-dasharray="{radius * slice_angle * 3.14159 / 180} {radius * 2 * 3.14159}" '
                f'stroke-dashoffset="{-radius * angle * 3.14159 / 180}" opacity="0.8"/>'
            )

            # Label
            label_angle = angle + slice_angle / 2
            label_rad = label_angle * (3.14159 / 180)
            label_x = cx + (radius - 20) * (3.14159 / 180) * slice_angle / 2
            label_y = cy

            angle += slice_angle

        # Legend
        svg_parts.append(f'<text x="20" y="20" font-size="12" font-weight="bold" fill="#667eea">Mapping Kinds</text>')
        for i, (kind, count) in enumerate(zip(kinds, counts)):
            color = colors[i % len(colors)]
            y = 40 + i * 20
            svg_parts.append(f'<rect x="20" y="{y-8}" width="12" height="12" fill="{color}" rx="2"/>')
            svg_parts.append(f'<text x="40" y="{y}" font-size="11" fill="#e0e0e0">{kind} ({count})</text>')

        svg_parts.append('</svg>')
        return "".join(svg_parts)

    def _generate_key_findings(self) -> str:
        """Generate list of key findings."""
        findings = []

        # From graph
        findings.append(f"<li>Total nodes: {len(self.graph.nodes)}</li>")
        findings.append(f"<li>Total edges: {len(self.graph.edges)}</li>")

        # From state space
        if self.state_space:
            findings.append(f"<li>State variables: {len(self.state_space.variables)}</li>")
            findings.append(f"<li>Observation modalities: {len(self.state_space.observations)}</li>")
            findings.append(f"<li>Actions: {len(self.state_space.actions)}</li>")

        # From validation
        if self.validation_report:
            coverage = getattr(self.validation_report, "coverage_score", 0.0)
            confidence = getattr(self.validation_report, "confidence_score", 0.0)
            findings.append(f"<li>Coverage score: {coverage*100:.1f}%</li>")
            findings.append(f"<li>Confidence score: {confidence*100:.1f}%</li>")

        return f"<ul style='list-style-position: inside;'>{''.join(findings)}</ul>"

    def _generate_graph_tab(self) -> str:
        """Generate Graph tab with Mermaid diagrams."""
        diagrams_html = ""

        # Add all mermaid diagrams
        for name, content in self.mermaid_diagrams.items():
            clean_name = name.replace("_", " ").title()
            diagrams_html += f"""
            <div class="chart-container">
                <div class="chart-title">{clean_name}</div>
                <pre class="mermaid">
{html.escape(content)}
                </pre>
            </div>
"""

        return f"""
    <div id="graph" class="tab-content">
        <div class="container">
            <h2>Program Graph Visualizations</h2>
            {diagrams_html}
        </div>
    </div>
"""

    def _generate_state_space_tab(self) -> str:
        """Generate State Space tab with tables."""
        if not self.state_space:
            return """
    <div id="state-space" class="tab-content">
        <div class="container">
            <h2>State Space</h2>
            <p>No state space model available</p>
        </div>
    </div>
"""

        vars_html = self._generate_state_variables_table()
        obs_html = self._generate_observations_table()
        actions_html = self._generate_actions_table()
        trans_html = self._generate_transitions_table()

        return f"""
    <div id="state-space" class="tab-content">
        <div class="container">
            <h2>State Space Model</h2>

            <h3>State Variables</h3>
            {vars_html}

            <h3>Observations</h3>
            {obs_html}

            <h3>Actions</h3>
            {actions_html}

            <h3>Transitions</h3>
            {trans_html}
        </div>
    </div>
"""

    def _generate_state_variables_table(self) -> str:
        """Generate state variables table."""
        if not self.state_space.variables:
            return "<p>No state variables</p>"

        rows = ""
        for var_id, var in list(self.state_space.variables.items())[:50]:
            var_name = getattr(var, "name", var_id)
            var_type = getattr(var, "domain_type", "unknown")
            rows += f"""
            <tr>
                <td><code>{html.escape(var_id[:30])}</code></td>
                <td>{html.escape(str(var_name))}</td>
                <td>{html.escape(str(var_type))}</td>
            </tr>
"""

        return f"""
<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Type</th>
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>
"""

    def _generate_observations_table(self) -> str:
        """Generate observations table."""
        if not self.state_space.observations:
            return "<p>No observations</p>"

        rows = ""
        for obs_id, obs in list(self.state_space.observations.items())[:50]:
            obs_name = getattr(obs, "name", obs_id)
            modality_type = getattr(obs, "modality_type", "unknown")
            rows += f"""
            <tr>
                <td><code>{html.escape(obs_id[:30])}</code></td>
                <td>{html.escape(str(obs_name))}</td>
                <td>{html.escape(str(modality_type))}</td>
            </tr>
"""

        return f"""
<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Modality Type</th>
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>
"""

    def _generate_actions_table(self) -> str:
        """Generate actions table."""
        if not self.state_space.actions:
            return "<p>No actions</p>"

        rows = ""
        for action_id, action in list(self.state_space.actions.items())[:50]:
            action_name = getattr(action, "name", action_id)
            num_params = len(getattr(action, "parameters", {}))
            rows += f"""
            <tr>
                <td><code>{html.escape(action_id[:30])}</code></td>
                <td>{html.escape(str(action_name))}</td>
                <td>{num_params}</td>
            </tr>
"""

        return f"""
<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Parameters</th>
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>
"""

    def _generate_transitions_table(self) -> str:
        """Generate transitions table."""
        if not self.state_space.transitions:
            return "<p>No transitions</p>"

        rows = ""
        for trans_id, trans in list(self.state_space.transitions.items())[:50]:
            action_id = getattr(trans, "action_id", "N/A")
            prob = getattr(trans, "probability", None)
            rows += f"""
            <tr>
                <td><code>{html.escape(trans_id[:30])}</code></td>
                <td><code>{html.escape(str(action_id)[:30])}</code></td>
                <td>{f"{prob:.2f}" if prob is not None else "N/A"}</td>
            </tr>
"""

        return f"""
<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Action</th>
            <th>Probability</th>
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>
"""

    def _generate_process_flow_tab(self) -> str:
        """Generate Process Flow tab with stages table and Gantt-style timeline."""
        if not self.process_model or not self.process_model.stages:
            return """
    <div id="process-flow" class="tab-content">
        <div class="container">
            <h2>Process Flow</h2>
            <p>No process model available</p>
        </div>
    </div>
"""

        # Build stages table
        stages_rows = ""
        for stage_id, stage in self.process_model.stages.items():
            preds = ", ".join(self.process_model.stages[p].name for p in stage.entry_points if p in self.process_model.stages) if stage.entry_points else "-"
            succs = ", ".join(self.process_model.stages[s].name for s in stage.exit_points if s in self.process_model.stages) if stage.exit_points else "-"

            stages_rows += f"""
            <tr>
                <td><code>{html.escape(stage.name[:20])}</code></td>
                <td>{html.escape(stage.description or '-')[:40]}</td>
                <td>{len(stage.node_ids)}</td>
                <td>{preds[:30]}</td>
                <td>{succs[:30]}</td>
                <td>{stage.pattern_type or '-'}</td>
                <td><span class="badge badge-info">{stage.confidence*100:.0f}%</span></td>
            </tr>
"""

        stages_table = f"""
<table>
    <thead>
        <tr>
            <th>Stage</th>
            <th>Description</th>
            <th>Nodes</th>
            <th>Predecessors</th>
            <th>Successors</th>
            <th>Pattern</th>
            <th>Confidence</th>
        </tr>
    </thead>
    <tbody>
        {stages_rows}
    </tbody>
</table>
"""

        # Create simple Gantt-style timeline using CSS
        gantt_html = self._generate_gantt_timeline()

        return f"""
    <div id="process-flow" class="tab-content">
        <div class="container">
            <h2>Process Flow & Workflow Stages</h2>

            <h3>Workflow Stages</h3>
            {stages_table}

            <h3>Process Timeline</h3>
            {gantt_html}
        </div>
    </div>
"""

    def _generate_gantt_timeline(self) -> str:
        """Generate a CSS-based Gantt-style timeline."""
        if not self.process_model or not self.process_model.stages:
            return "<p>No stages to display</p>"

        stages = list(self.process_model.stages.values())
        total_stages = len(stages)

        gantt_html = '<div class="gantt-container">'
        gantt_html += '<div class="gantt-header">Timeline</div>'

        for i, stage in enumerate(stages):
            width_pct = 95 / total_stages if total_stages > 0 else 0
            left_pct = (5 + i * width_pct)
            color = ["#667eea", "#764ba2", "#f093fb", "#4facfe"][i % 4]

            gantt_html += f'''
            <div class="gantt-bar" style="left: {left_pct}%; width: {width_pct}%; background: {color};">
                <span class="gantt-label">{html.escape(stage.name[:15])}</span>
            </div>
'''

        gantt_html += '</div>'

        gantt_css = """
        <style>
            .gantt-container {
                position: relative;
                height: 120px;
                background: rgba(20, 20, 30, 0.8);
                border: 1px solid rgba(102, 126, 234, 0.2);
                border-radius: 8px;
                margin: 20px 0;
                padding: 20px 10px;
            }

            .gantt-header {
                position: absolute;
                left: 10px;
                top: 5px;
                font-size: 0.9em;
                color: #667eea;
                font-weight: bold;
            }

            .gantt-bar {
                position: absolute;
                top: 50px;
                height: 40px;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0.8;
                transition: opacity 0.2s ease;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            .gantt-bar:hover {
                opacity: 1;
                box-shadow: 0 0 10px rgba(102, 126, 234, 0.4);
            }

            .gantt-label {
                color: white;
                font-size: 0.85em;
                font-weight: bold;
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
            }
        </style>
"""
        return gantt_css + gantt_html

    def _generate_factor_graph_tab(self) -> str:
        """Generate Factor Graph tab showing state variables, observations, and actions."""
        if not self.state_space:
            return """
    <div id="factor-graph" class="tab-content">
        <div class="container">
            <h2>Factor Graph</h2>
            <p>No state space model available</p>
        </div>
    </div>
"""

        # Create a simple SVG visualization of state vars, observations, and actions
        svg_graph = self._generate_factor_graph_svg()

        return f"""
    <div id="factor-graph" class="tab-content">
        <div class="container">
            <h2>Factor Graph</h2>
            <div class="chart-container">
                <div class="chart-title">State Variables, Observations & Actions</div>
                {svg_graph}
            </div>
        </div>
    </div>
"""

    def _generate_factor_graph_svg(self) -> str:
        """Generate SVG factor graph visualization."""
        if not self.state_space:
            return "<p>No data</p>"

        # Count entities
        num_vars = len(self.state_space.variables) if self.state_space.variables else 0
        num_obs = len(self.state_space.observations) if self.state_space.observations else 0
        num_actions = len(self.state_space.actions) if self.state_space.actions else 0

        width, height = 800, 400
        svg_parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">']

        # Background
        svg_parts.append(f'<rect width="{width}" height="{height}" fill="rgba(20,20,30,0.5)" rx="4"/>')

        # Draw three columns: States (left), Observations (middle), Actions (right)
        col_width = width / 3

        # Column headers
        svg_parts.append(f'<text x="{col_width/2}" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="#667eea">State Variables</text>')
        svg_parts.append(f'<text x="{col_width + col_width/2}" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="#764ba2">Observations</text>')
        svg_parts.append(f'<text x="{col_width*2 + col_width/2}" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="#f093fb">Actions</text>')

        # Draw state variables as circles
        var_y_start = 80
        var_spacing = (height - 100) / max(num_vars, 1)
        for i in range(min(num_vars, 8)):
            y = var_y_start + i * var_spacing
            svg_parts.append(f'<circle cx="60" cy="{y}" r="30" fill="rgba(102, 126, 234, 0.3)" stroke="#667eea" stroke-width="2"/>')
            svg_parts.append(f'<text x="60" y="{y+5}" text-anchor="middle" font-size="12" fill="#e0e0e0">Var {i+1}</text>')

        # Draw observations as squares
        obs_y_start = 80
        obs_spacing = (height - 100) / max(num_obs, 1)
        for i in range(min(num_obs, 8)):
            y = obs_y_start + i * obs_spacing
            svg_parts.append(f'<rect x="{col_width + 30}" y="{y - 25}" width="60" height="50" fill="rgba(118, 75, 162, 0.3)" stroke="#764ba2" stroke-width="2" rx="4"/>')
            svg_parts.append(f'<text x="{col_width + 60}" y="{y+5}" text-anchor="middle" font-size="12" fill="#e0e0e0">Obs {i+1}</text>')

        # Draw actions as diamonds (rectangles rotated)
        act_y_start = 80
        act_spacing = (height - 100) / max(num_actions, 1)
        for i in range(min(num_actions, 8)):
            y = act_y_start + i * act_spacing
            svg_parts.append(f'<polygon points="{col_width*2 + 60},{y} {col_width*2 + 90},{y + 25} {col_width*2 + 60},{y + 50} {col_width*2 + 30},{y + 25}" fill="rgba(240, 147, 251, 0.3)" stroke="#f093fb" stroke-width="2"/>')
            svg_parts.append(f'<text x="{col_width*2 + 60}" y="{y+18}" text-anchor="middle" font-size="11" fill="#e0e0e0">Act {i+1}</text>')

        # Draw connections
        for i in range(min(num_vars, 3)):
            for j in range(min(num_obs, 3)):
                var_y = var_y_start + i * var_spacing
                obs_y = obs_y_start + j * obs_spacing
                svg_parts.append(f'<line x1="90" y1="{var_y}" x2="{col_width + 30}" y2="{obs_y}" stroke="rgba(102, 126, 234, 0.3)" stroke-width="1" stroke-dasharray="5,5"/>')

        for j in range(min(num_obs, 3)):
            for k in range(min(num_actions, 3)):
                obs_y = obs_y_start + j * obs_spacing
                act_y = act_y_start + k * act_spacing
                svg_parts.append(f'<line x1="{col_width + 90}" y1="{obs_y}" x2="{col_width*2 + 30}" y2="{act_y}" stroke="rgba(118, 75, 162, 0.3)" stroke-width="1" stroke-dasharray="5,5"/>')

        svg_parts.append('</svg>')
        return "".join(svg_parts)

    def _generate_active_inference_tab(self) -> str:
        """Generate Active Inference tab with free energy trajectory and belief evolution."""
        if not self.trace_data:
            return """
    <div id="active-inference" class="tab-content">
        <div class="container">
            <h2>Active Inference Simulation</h2>
            <p>No active inference trace data available</p>
        </div>
    </div>
"""

        # Parse trace data
        trace_list: List[Any] = self.trace_data if isinstance(self.trace_data, list) else []

        # Generate free energy chart
        fe_svg = self._generate_free_energy_chart(trace_list)

        # Generate belief evolution table
        beliefs_table = self._generate_belief_evolution_table(trace_list)

        return f"""
    <div id="active-inference" class="tab-content">
        <div class="container">
            <h2>Active Inference Simulation</h2>

            <h3>Free Energy Trajectory</h3>
            <div class="chart-container">
                {fe_svg}
            </div>

            <h3>Belief Evolution</h3>
            {beliefs_table}
        </div>
    </div>
"""

    def _generate_free_energy_chart(self, trace_list: List[Dict]) -> str:
        """Generate free energy trajectory line chart."""
        if not trace_list:
            return "<p>No trace data</p>"

        steps = [t.get("step", i) for i, t in enumerate(trace_list[:100])]
        free_energies = [t.get("free_energy", 0.0) for t in trace_list[:100]]

        if not free_energies:
            return "<p>No free energy data</p>"

        max_fe = max(free_energies) if free_energies else 1.0
        min_fe = min(free_energies) if free_energies else 0.0
        fe_range = max_fe - min_fe if max_fe > min_fe else 1.0

        width, height = 800, 300
        padding = 50
        chart_width = width - 2 * padding
        chart_height = height - 2 * padding

        svg_parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
        svg_parts.append(f'<rect width="{width}" height="{height}" fill="rgba(20,20,30,0.8)" rx="4"/>')

        # Axes
        svg_parts.append(f'<line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" stroke="#667eea" stroke-width="2"/>')
        svg_parts.append(f'<line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" stroke="#667eea" stroke-width="2"/>')

        # Plot line
        if len(free_energies) > 1:
            points = []
            for i, fe in enumerate(free_energies):
                x = padding + (i / (len(free_energies) - 1)) * chart_width if len(free_energies) > 1 else padding
                y = height - padding - ((fe - min_fe) / fe_range) * chart_height if fe_range > 0 else height - padding
                points.append(f"{x},{y}")

            svg_parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#667eea" stroke-width="2" stroke-linejoin="round"/>')

            # Add points
            for i, fe in enumerate(free_energies):
                x = padding + (i / (len(free_energies) - 1)) * chart_width if len(free_energies) > 1 else padding
                y = height - padding - ((fe - min_fe) / fe_range) * chart_height if fe_range > 0 else height - padding
                svg_parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#764ba2" opacity="0.6"/>')

        # Labels
        svg_parts.append(f'<text x="{width/2}" y="{height - 10}" text-anchor="middle" font-size="12" fill="#b0b0b0">Simulation Steps</text>')
        svg_parts.append(f'<text x="20" y="{height/2}" text-anchor="middle" font-size="12" fill="#b0b0b0" transform="rotate(-90 20 {height/2})">Free Energy</text>')

        svg_parts.append('</svg>')
        return "".join(svg_parts)

    def _generate_belief_evolution_table(self, trace_list: List[Dict]) -> str:
        """Generate belief evolution table."""
        if not trace_list:
            return "<p>No trace data</p>"

        rows = ""
        for trace in trace_list[:20]:
            step = trace.get("step", "?")
            action = trace.get("action", "None")
            observation = trace.get("observation", "None")
            free_energy = trace.get("free_energy", 0.0)
            beliefs = trace.get("beliefs", {})
            belief_summary = ", ".join(f"{k[:10]}: {v:.2f}" for k, v in list(beliefs.items())[:3])

            rows += f"""
            <tr>
                <td>{step}</td>
                <td><code>{html.escape(str(observation)[:15])}</code></td>
                <td><code>{html.escape(str(action)[:15])}</code></td>
                <td>{free_energy:.4f}</td>
                <td><small>{belief_summary}</small></td>
            </tr>
"""

        return f"""
<table>
    <thead>
        <tr>
            <th>Step</th>
            <th>Observation</th>
            <th>Action</th>
            <th>Free Energy</th>
            <th>Beliefs</th>
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>
"""

    def _generate_gnn_package_tab(self) -> str:
        """Generate GNN Package tab showing validation results and files."""
        if not self.gnn_validation:
            return """
    <div id="gnn-package" class="tab-content">
        <div class="container">
            <h2>GNN Package</h2>
            <p>No GNN validation report available</p>
        </div>
    </div>
"""

        # Extract validation data
        valid = self.gnn_validation.get("valid", False)
        score = self.gnn_validation.get("score", 0.0)
        errors = self.gnn_validation.get("errors", [])
        warnings = self.gnn_validation.get("warnings", [])
        details = self.gnn_validation.get("details", {})
        manifest = details.get("manifest", {})
        checksums = manifest.get("checksums", {})
        files = manifest.get("files", [])
        stats = manifest.get("graph_stats", {})

        # Build validation status
        status_badge = f'<span class="badge {"badge-pass" if valid else "badge-fail"}">{"✓ Valid" if valid else "✗ Invalid"}</span>'

        # Files table
        files_rows = ""
        for filename in files[:20]:
            checksum = checksums.get(filename, "N/A")[:16] + "..."
            files_rows += f"""
            <tr>
                <td><code>{html.escape(filename)}</code></td>
                <td><code style="font-size: 0.85em;">{checksum}</code></td>
            </tr>
"""

        files_table = f"""
<table>
    <thead>
        <tr>
            <th>File</th>
            <th>Checksum (SHA256)</th>
        </tr>
    </thead>
    <tbody>
        {files_rows}
    </tbody>
</table>
"""

        # Errors/Warnings
        error_html = ""
        if errors:
            error_rows = "".join(f'<tr><td><span class="badge badge-fail">ERROR</span></td><td>{html.escape(str(e)[:80])}</td></tr>' for e in errors[:10])
            error_html = f"""
            <h3>Errors</h3>
            <table>
                <thead>
                    <tr><th>Type</th><th>Message</th></tr>
                </thead>
                <tbody>{error_rows}</tbody>
            </table>
"""

        warning_html = ""
        if warnings:
            warning_rows = "".join(f'<tr><td><span class="badge" style="background: rgba(255, 193, 7, 0.2); color: #ffc107; border: 1px solid rgba(255, 193, 7, 0.3);">WARN</span></td><td>{html.escape(str(w)[:80])}</td></tr>' for w in warnings[:10])
            warning_html = f"""
            <h3>Warnings</h3>
            <table>
                <thead>
                    <tr><th>Type</th><th>Message</th></tr>
                </thead>
                <tbody>{warning_rows}</tbody>
            </table>
"""

        return f"""
    <div id="gnn-package" class="tab-content">
        <div class="container">
            <h2>GNN Package Validation</h2>

            <div class="validation-check">
                <div class="validation-icon">📦</div>
                <div>
                    <strong>Package Status</strong>
                    {status_badge}
                    <p>Validation Score: {score:.1f}%</p>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div class="validation-check">
                    <div class="validation-icon">📊</div>
                    <div>
                        <strong>Graph Stats</strong>
                        <p>Nodes: {stats.get("nodes", 0)}</p>
                        <p>Edges: {stats.get("edges", 0)}</p>
                    </div>
                </div>
                <div class="validation-check">
                    <div class="validation-icon">⚙️</div>
                    <div>
                        <strong>State Space</strong>
                        <p>Variables: {details.get("state_space_stats", {}).get("variables", 0)}</p>
                        <p>Observations: {details.get("state_space_stats", {}).get("observations", 0)}</p>
                    </div>
                </div>
            </div>

            <h3>Package Files ({len(files)})</h3>
            {files_table}

            {error_html}
            {warning_html}
        </div>
    </div>
"""

    def _generate_semantic_mappings_tab(self) -> str:
        """Generate Semantic Mappings tab with searchable table."""
        if not self.semantic_mappings:
            return """
    <div id="semantic-mappings" class="tab-content">
        <div class="container">
            <h2>Semantic Mappings</h2>
            <p>No semantic mappings available</p>
        </div>
    </div>
"""

        rows = ""
        for mapping_id, mapping in list(self.semantic_mappings.items())[:100]:
            kind = getattr(mapping, "kind", "unknown")
            if hasattr(kind, "value"):
                kind = kind.value
            label = getattr(mapping, "label", "")
            confidence = getattr(mapping, "confidence", 0.0)
            if hasattr(confidence, "value"):
                confidence = confidence.value

            # Count source/target nodes
            source_nodes = getattr(mapping, "source_nodes", [])
            num_nodes = len(source_nodes) if source_nodes else 0

            description = getattr(mapping, "description", "")

            rows += f"""
            <tr>
                <td><code>{html.escape(mapping_id[:20])}</code></td>
                <td>{html.escape(str(kind))}</td>
                <td>{html.escape(str(label)[:30])}</td>
                <td><span class="badge badge-info">{confidence*100:.0f}%</span></td>
                <td>{num_nodes}</td>
                <td>{html.escape(str(description)[:50])}</td>
            </tr>
"""

        return f"""
    <div id="semantic-mappings" class="tab-content">
        <div class="container">
            <h2>Semantic Mappings</h2>
            <input type="text" class="search-box" placeholder="Search mappings..."
                   onkeyup="filterTable(this, 'mappings-table')">
            <table id="mappings-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Kind</th>
                        <th>Label</th>
                        <th>Confidence</th>
                        <th>Nodes</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </div>
"""

    def _generate_mermaid_tab(self) -> str:
        """Generate Mermaid Diagrams tab with all diagrams."""
        diagrams_html = ""

        for name, content in self.mermaid_diagrams.items():
            clean_name = name.replace("_", " ").title()
            diagrams_html += f"""
            <h3>{clean_name}</h3>
            <pre class="mermaid">
{html.escape(content)}
            </pre>
"""

        return f"""
    <div id="mermaid-diagrams" class="tab-content">
        <div class="container">
            <h2>Mermaid Diagrams</h2>
            {diagrams_html if diagrams_html else "<p>No diagrams available</p>"}
        </div>
    </div>
"""

    def _generate_validation_tab(self) -> str:
        """Generate Validation tab with check results."""
        is_valid = getattr(self.validation_report, "is_valid", False)
        coverage = getattr(self.validation_report, "coverage_score", 0.0)
        confidence = getattr(self.validation_report, "confidence_score", 0.0)
        summary = getattr(self.validation_report, "summary", "")
        issues = getattr(self.validation_report, "issues", [])

        checks_html = ""
        checks_html += f"""
            <div class="validation-check">
                <div class="validation-icon">{'✓' if is_valid else '✗'}</div>
                <div>
                    <strong>Overall Status: {'VALID' if is_valid else 'ISSUES FOUND'}</strong>
                    <p>{len(issues)} issue(s) found</p>
                </div>
            </div>
"""

        checks_html += f"""
            <div class="validation-check">
                <div class="validation-icon">📊</div>
                <div>
                    <strong>Coverage Score</strong>
                    <p>{coverage*100:.1f}%</p>
                    <div class="confidence-bar" style="width: {coverage*100}%;"></div>
                </div>
            </div>
"""

        checks_html += f"""
            <div class="validation-check">
                <div class="validation-icon">🎯</div>
                <div>
                    <strong>Confidence Score</strong>
                    <p>{confidence*100:.1f}%</p>
                    <div class="confidence-bar" style="width: {confidence*100}%;"></div>
                </div>
            </div>
"""

        # Issues table
        issues_html = ""
        if issues:
            for issue in issues[:50]:
                severity = getattr(issue, "severity", "unknown")
                message = getattr(issue, "message", "")
                issues_html += f"""
            <tr>
                <td><span class="badge badge-fail">{severity}</span></td>
                <td>{html.escape(str(message)[:100])}</td>
            </tr>
"""
            issues_html = f"""
            <h3>Issues Found</h3>
            <table>
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
                    {issues_html}
                </tbody>
            </table>
"""

        return f"""
    <div id="validation" class="tab-content">
        <div class="container">
            <h2>Validation Report</h2>
            {checks_html}
            {issues_html}
            <h3>Summary</h3>
            <p>{html.escape(summary)}</p>
        </div>
    </div>
"""

    def _generate_javascript(self) -> str:
        """Return inline JavaScript (externalised in :mod:`cogant.viz.dashboard.assets`)."""
        from cogant.viz.dashboard.assets import DASHBOARD_JS
        return DASHBOARD_JS

