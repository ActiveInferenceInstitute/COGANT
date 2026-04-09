"""GraphVisualizer: Render program graph with D3.js."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Any, Optional
import json
import logging

if TYPE_CHECKING:
    from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


@dataclass
class D3Node:
    """D3.js node representation."""

    id: str
    label: str
    group: str
    size: int = 10
    color: Optional[str] = None
    language: Optional[str] = None
    kind: Optional[str] = None
    path: Optional[str] = None
    qualified_name: Optional[str] = None


@dataclass
class D3Link:
    """D3.js link (edge) representation."""

    source: str
    target: str
    label: str
    weight: float = 1.0


class GraphVisualizer:
    """
    Render program graphs as interactive D3.js visualizations.

    Features:
      - Node clustering by package/language/kind/service
      - Edge type filtering
      - Interactive pan/zoom
      - Hover tooltips
      - HTML/SVG export
    """

    def __init__(self):
        """Initialize visualizer."""
        self.nodes: List[D3Node] = []
        self.links: List[D3Link] = []
        self.metadata: Dict[str, Any] = {}

    def from_program_graph(self, graph: Dict[str, Any]) -> "GraphVisualizer":
        """
        Load program graph data from a plain dict.

        Args:
            graph: Program graph dict with nodes/edges.

        Returns:
            self (for chaining).
        """
        logger.info("Loading program graph for visualization")

        self.nodes = []
        self.links = []

        # Convert graph nodes
        for node in graph.get("nodes", []):
            self.nodes.append(
                D3Node(
                    id=node.get("id", ""),
                    label=node.get("name", ""),
                    group=node.get("type", "unknown"),
                    language=node.get("language"),
                    kind=node.get("type"),
                    path=node.get("path"),
                    qualified_name=node.get("qualified_name"),
                )
            )

        # Convert graph edges
        for edge in graph.get("edges", []):
            self.links.append(
                D3Link(
                    source=edge.get("source", ""),
                    target=edge.get("target", ""),
                    label=edge.get("type", ""),
                    weight=edge.get("weight", 1.0),
                )
            )

        self.metadata = graph.get("metadata", {})
        return self

    def from_typed_graph(self, graph: ProgramGraph) -> "GraphVisualizer":
        """
        Load from a typed ProgramGraph object.

        Args:
            graph: ProgramGraph instance with typed Node/Edge objects.

        Returns:
            self (for chaining).
        """
        logger.info("Loading typed ProgramGraph for visualization")

        self.nodes = []
        self.links = []

        for node in graph.nodes.values():
            self.nodes.append(
                D3Node(
                    id=node.id,
                    label=node.name,
                    group=node.kind.value,
                    language=node.language,
                    kind=node.kind.value,
                    path=node.path,
                    qualified_name=node.qualified_name,
                )
            )

        for edge in graph.edges.values():
            self.links.append(
                D3Link(
                    source=edge.source_id,
                    target=edge.target_id,
                    label=edge.kind.value,
                    weight=edge.weight,
                )
            )

        self.metadata = {
            "repo_uri": graph.metadata.repo_uri,
            "languages": list(graph.metadata.languages),
            "version": graph.metadata.version,
        }
        return self

    def cluster_by_package(self) -> "GraphVisualizer":
        """
        Cluster nodes by package/namespace.

        Groups nodes by their module path prefix. Uses ``path`` when available
        (first component), otherwise falls back to splitting the label on ``'.'``
        and using all but the last component.

        Returns:
            self (for chaining).
        """
        logger.debug("Clustering by package")
        for node in self.nodes:
            if node.path:
                # Use the first path component as the package name
                parts = node.path.replace("\\", "/").split("/")
                node.group = parts[0] if parts else "root"
            elif node.qualified_name:
                parts = node.qualified_name.split(".")
                node.group = ".".join(parts[:-1]) if len(parts) > 1 else "root"
            else:
                parts = node.label.split(".")
                node.group = ".".join(parts[:-1]) if len(parts) > 1 else "root"
        return self

    def cluster_by_language(self) -> "GraphVisualizer":
        """
        Cluster nodes by programming language.

        Uses the ``language`` field populated during graph loading.  Nodes
        without a language value are grouped under ``"unknown_lang"``.

        Returns:
            self (for chaining).
        """
        logger.debug("Clustering by language")
        for node in self.nodes:
            if node.language:
                node.group = node.language
            else:
                node.group = "unknown_lang"
        return self

    def cluster_by_kind(self) -> "GraphVisualizer":
        """
        Cluster nodes by their kind (NodeKind value).

        Groups nodes by the ``kind`` field (e.g. ``"function"``,
        ``"class"``, ``"module"``).  Nodes without a kind are grouped
        under ``"unknown_kind"``.

        Returns:
            self (for chaining).
        """
        logger.debug("Clustering by kind")
        for node in self.nodes:
            if node.kind:
                node.group = node.kind
            else:
                node.group = "unknown_kind"
        return self

    def cluster_by_service(self) -> "GraphVisualizer":
        """
        Cluster nodes by logical service/module.

        Groups nodes by their top-level module/package name.

        Returns:
            self (for chaining).
        """
        logger.debug("Clustering by service")
        # Extract top-level module/service name
        for node in self.nodes:
            # Get the first component of the qualified name
            parts = node.label.split(".")
            if parts:
                node.group = parts[0]  # Top-level module name
            else:
                node.group = "unknown_service"
        return self

    def get_clusters(self) -> Dict[str, List[str]]:
        """
        Return current cluster mapping (group name -> list of node IDs).

        Computed from each node's current ``group`` assignment.

        Returns:
            Dict mapping cluster/group names to lists of node IDs.
        """
        clusters: Dict[str, List[str]] = {}
        for node in self.nodes:
            clusters.setdefault(node.group, []).append(node.id)
        return clusters

    def filter_by_edge_type(self, edge_type: str) -> "GraphVisualizer":
        """
        Filter to show only specific edge types.

        Args:
            edge_type: Type of edges to show (e.g., 'calls', 'imports').

        Returns:
            self (for chaining).
        """
        logger.debug(f"Filtering by edge type: {edge_type}")
        self.links = [l for l in self.links if l.label == edge_type]
        return self

    def render_html(self, output_path: str) -> str:
        """
        Render as interactive HTML with D3.js.

        Args:
            output_path: Path to write HTML file.

        Returns:
            Path to rendered file.
        """
        logger.info(f"Rendering D3 visualization to {output_path}")

        html = self._generate_html()
        with open(output_path, "w") as f:
            f.write(html)

        return output_path

    def render_svg(self, output_path: str) -> str:
        """
        Render as static SVG.

        Args:
            output_path: Path to write SVG file.

        Returns:
            Path to rendered file.
        """
        logger.info(f"Rendering SVG to {output_path}")

        svg = self._generate_svg()
        with open(output_path, "w") as f:
            f.write(svg)

        return output_path

    def to_d3_json(self) -> Dict[str, Any]:
        """
        Export as D3.js-compatible JSON.

        Includes a ``clusters`` key mapping each group name to its member
        node IDs so that consumers can render convex-hull overlays or
        grouped layouts.

        Returns:
            JSON object with nodes, links, and clusters.
        """
        clusters = self.get_clusters()
        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "group": n.group,
                    "size": n.size,
                    "kind": n.kind,
                    "language": n.language,
                }
                for n in self.nodes
            ],
            "links": [
                {"source": l.source, "target": l.target, "label": l.label, "weight": l.weight}
                for l in self.links
            ],
            "clusters": clusters,
        }

    def _generate_html(self) -> str:
        """Generate HTML with embedded D3.js visualization."""
        d3_data = self.to_d3_json()
        d3_json = json.dumps(d3_data)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Program Graph Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }}
        #graph {{
            width: 100%;
            height: 100vh;
            background: white;
        }}
        .node {{
            cursor: pointer;
            stroke: #555;
            stroke-width: 1.5px;
        }}
        .node:hover {{
            stroke: #000;
            stroke-width: 2px;
        }}
        .link {{
            stroke: #999;
            stroke-opacity: 0.6;
        }}
        .cluster-hull {{
            fill-opacity: 0.08;
            stroke-width: 1.5px;
            stroke-dasharray: 4 2;
        }}
        .tooltip {{
            position: absolute;
            padding: 8px;
            background: rgba(0,0,0,0.7);
            color: white;
            border-radius: 4px;
            pointer-events: none;
            font-size: 12px;
            display: none;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div id="graph"></div>
    <div class="tooltip"></div>

    <script>
        const data = {d3_json};

        const width = window.innerWidth;
        const height = window.innerHeight;

        const color = d3.scaleOrdinal(d3.schemeCategory10);

        const svg = d3.select('#graph')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g');

        // Create simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));

        // Cluster hulls layer (drawn behind nodes)
        const hullLayer = g.append('g').attr('class', 'hulls');

        // Create links
        const link = g.append('g')
            .selectAll('line')
            .data(data.links)
            .enter()
            .append('line')
            .attr('class', 'link');

        // Create nodes
        const node = g.append('g')
            .selectAll('circle')
            .data(data.nodes)
            .enter()
            .append('circle')
            .attr('class', 'node')
            .attr('r', d => d.size || 10)
            .attr('fill', d => color(d.group))
            .call(drag(simulation));

        // Draw cluster convex hulls
        function updateHulls() {{
            const groups = {{}};
            data.nodes.forEach(d => {{
                if (!groups[d.group]) groups[d.group] = [];
                groups[d.group].push([d.x, d.y]);
            }});

            const hullData = Object.entries(groups)
                .filter(([, pts]) => pts.length >= 3)
                .map(([name, pts]) => ({{ name, hull: d3.polygonHull(pts) }}))
                .filter(d => d.hull);

            const hulls = hullLayer.selectAll('path').data(hullData, d => d.name);
            hulls.enter().append('path')
                .attr('class', 'cluster-hull')
                .style('fill', d => color(d.name))
                .style('stroke', d => color(d.name))
                .merge(hulls)
                .attr('d', d => 'M' + d.hull.join('L') + 'Z');
            hulls.exit().remove();
        }}

        // Update positions on tick
        simulation.on('tick', () => {{
            link.attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node.attr('cx', d => d.x)
                .attr('cy', d => d.y);

            updateHulls();
        }});

        // Zoom behavior
        svg.call(d3.zoom().on('zoom', (event) => {{
            g.attr('transform', event.transform);
        }}));

        // Tooltip
        const tooltip = d3.select('.tooltip');
        node.on('mouseover', (event, d) => {{
            tooltip.style('display', 'block')
                .html(`<strong>${{d.label}}</strong><br>Group: ${{d.group}}<br>Kind: ${{d.kind || '-'}}<br>Lang: ${{d.language || '-'}}`)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px');
        }})
        .on('mouseout', () => {{
            tooltip.style('display', 'none');
        }});

        // Drag behavior
        function drag(simulation) {{
            function dragstarted(event, d) {{
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }}

            function dragged(event, d) {{
                d.fx = event.x;
                d.fy = event.y;
            }}

            function dragended(event, d) {{
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }}

            return d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended);
        }}
    </script>
</body>
</html>
"""

    def _generate_svg(self) -> str:
        """Generate static SVG representation."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800">
    <defs>
        <style>
            .node {{ fill: #69c; stroke: #333; stroke-width: 2; }}
            .link {{ stroke: #999; stroke-width: 1; }}
            .label {{ font-size: 12px; font-family: sans-serif; }}
        </style>
    </defs>

    <!-- Links -->
    <g class="links">
        {''.join(f'<line class="link" x1="0" y1="0" x2="100" y2="100" />' for _ in self.links[:10])}
    </g>

    <!-- Nodes -->
    <g class="nodes">
        {''.join(f'<circle class="node" cx="{i*100}" cy="50" r="15" /><text class="label" x="{i*100}" y="80">{n.label}</text>' for i, n in enumerate(self.nodes[:10]))}
    </g>
</svg>
"""
