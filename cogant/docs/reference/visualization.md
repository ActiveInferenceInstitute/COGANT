# Visualization API Reference

## Overview

The visualization module (`cogant.viz`) produces visual representations of COGANT artifacts: program graphs, semantic models, and analysis results. All outputs use matplotlib-based PNG/PDF with optional Mermaid diagram support and self-contained HTML dashboards.

## Visualization Formats

### Format Comparison

| Format | Module | Data Type | Use Case | Dependencies | Output | Size |
|--------|--------|-----------|----------|--------------|--------|------|
| PNG | png_export | Bitmap image | Quick reviews, reports | matplotlib, Pillow | Binary file | 0.5-50 MB |
| PDF | pdf_export | Multi-page document | Publication, formal reports | matplotlib, reportlab | Binary file | 5-200 MB |
| Mermaid | mermaid | Diagram syntax | Markdown, wikis, docs | None | Text file (.mmd) | 0.01-1 MB |
| SVG | svg_export | Vector graphics | Web embedding, scalable | graphviz (optional) | Text file | 1-100 MB |
| HTML | dashboard | Interactive website | Exploration, dashboards | matplotlib (optional) | HTML + CSS + JS | 1-50 MB |
| DOT | mermaid (internal) | Graph syntax | Graphviz processing | graphviz | Text file | 0.1-10 MB |

## Core Visualization Classes

### PNGExporter

Render program graphs and analysis results as PNG (bitmap) images.

```python
class PNGExporter:
    def export_program_graph(
        self,
        graph: ProgramGraph,
        output_path: str | Path
    ) -> str | None:
        """
        Render a program graph as PNG.

        Args:
            graph: ProgramGraph to visualize
            output_path: Path to write PNG file

        Returns:
            Path to exported file, or None if matplotlib unavailable

        Raises:
            OSError: If file write fails
        """

    def export_complexity_analysis(
        self,
        report: ComplexityReport,
        output_path: str | Path
    ) -> str | None:
        """Export complexity hotspot heatmap as PNG."""

    def export_coupling_heatmap(
        self,
        report: CouplingReport,
        output_path: str | Path
    ) -> str | None:
        """Export coupling instability heatmap as PNG."""
```

**Usage:**
```python
from cogant.viz.png_export import PNGExporter

exporter = PNGExporter()
png_path = exporter.export_program_graph(graph, "output/graph.png")
if png_path:
    print(f"Exported: {png_path}")
else:
    print("Matplotlib unavailable")
```

### PDFExporter

Generate multi-page PDF reports with publication-quality vector graphics.

```python
class PDFExporter:
    def export_program_graph(
        self,
        graph: ProgramGraph,
        output_path: str | Path
    ) -> str | None:
        """
        Render a program graph as PDF.

        Args:
            graph: ProgramGraph to visualize
            output_path: Path to write PDF file

        Returns:
            Path to exported file, or None if matplotlib unavailable
        """

    def export_semantic_model(
        self,
        mappings: SemanticMappings,
        output_path: str | Path
    ) -> str | None:
        """Export semantic mappings and roles as PDF."""

    def export_matrices(
        self,
        A: np.ndarray,
        B: list[np.ndarray],
        C: np.ndarray,
        D: np.ndarray,
        output_path: str | Path
    ) -> str | None:
        """Export A/B/C/D matrices as multi-page PDF."""

    def export_report(
        self,
        graph: ProgramGraph,
        mappings: SemanticMappings,
        analysis: dict[str, Any],
        output_path: str | Path
    ) -> str | None:
        """Export comprehensive report with graphs, matrices, and metrics."""
```

**Usage:**
```python
from cogant.viz.pdf_export import PDFExporter
import numpy as np

exporter = PDFExporter()

# Export program graph
graph_pdf = exporter.export_program_graph(graph, "output/graph.pdf")

# Export matrices
A = np.array([[0.8, 0.2], [0.3, 0.7]])
B = [np.array([[1.0, 0.0], [0.0, 1.0]])]
C = np.array([0.7, 0.3])
D = np.array([0.5, 0.5])

matrices_pdf = exporter.export_matrices(A, B, C, D, "output/matrices.pdf")
```

### MatrixVisualizer

Visualize Active Inference A/B/C/D matrices as heatmaps and bar charts.

```python
class MatrixVisualizer:
    def plot_A_matrix(
        self,
        A: np.ndarray,
        labels: list[str] | None = None
    ) -> Any:
        """
        Plot the likelihood matrix (A) as a heatmap.

        A represents P(observation | hidden_state).
        Shape: (num_observations, num_hidden_states)

        Args:
            A: Likelihood matrix (2D array-like)
            labels: Optional observation/state labels

        Returns:
            Matplotlib Figure or None if unavailable
        """

    def plot_B_matrix(
        self,
        B: np.ndarray,
        action_label: str = "Action",
        labels: list[str] | None = None
    ) -> Any:
        """
        Plot the state transition matrix (B) as a heatmap.

        B represents P(next_state | state, action).
        Shape: (num_states, num_states)
        """

    def plot_C_vector(
        self,
        C: np.ndarray,
        labels: list[str] | None = None
    ) -> Any:
        """
        Plot the preference vector (C) as a bar chart.

        C represents goal/preference prior over observations.
        Shape: (num_observations,)
        """

    def plot_D_vector(
        self,
        D: np.ndarray,
        labels: list[str] | None = None
    ) -> Any:
        """
        Plot the initial state distribution (D) as a bar chart.

        D represents prior belief about initial hidden state.
        Shape: (num_hidden_states,)
        """

    def plot_all_matrices(
        self,
        A: np.ndarray,
        B: np.ndarray,
        C: np.ndarray,
        D: np.ndarray,
        labels: dict[str, list[str]] | None = None
    ) -> Any:
        """
        Plot all matrices in a 2x2 grid.

        Returns:
            Matplotlib Figure with subplots (2x2)
        """
```

**Usage:**
```python
from cogant.viz.matrix_view import MatrixVisualizer
import numpy as np

viz = MatrixVisualizer()

A = np.array([[0.8, 0.2], [0.3, 0.7]])
B = np.array([[1.0, 0.0], [0.0, 1.0]])
C = np.array([0.7, 0.3])
D = np.array([0.5, 0.5])

fig = viz.plot_all_matrices(A, B, C, D)
if fig:
    fig.savefig("matrices.png")
```

### MermaidGenerator

Generate Mermaid diagram syntax (no external dependencies).

```python
class MermaidGenerator:
    def generate_flowchart(
        self,
        nodes: list[tuple[str, str]],
        edges: list[tuple[str, str]],
        direction: str = "TD"
    ) -> str:
        """
        Generate a Mermaid flowchart.

        Args:
            nodes: List of (node_id, label) tuples
            edges: List of (source_id, target_id) tuples
            direction: 'TD' (top-down), 'LR' (left-right), 'BT', 'RL'

        Returns:
            Mermaid diagram syntax (string)

        Example:
            >>> gen = MermaidGenerator()
            >>> mermaid = gen.generate_flowchart(
            ...     nodes=[("A", "Start"), ("B", "Process"), ("C", "End")],
            ...     edges=[("A", "B"), ("B", "C")],
            ...     direction="TD"
            ... )
            >>> # Output can be embedded in Markdown
        """

    def generate_class_diagram(
        self,
        classes: list[dict[str, Any]]
    ) -> str:
        """
        Generate a Mermaid class diagram.

        Args:
            classes: List of class dicts with 'name', 'methods', 'attributes'

        Returns:
            Mermaid class diagram syntax
        """

    def generate_sequence_diagram(
        self,
        participants: list[str],
        interactions: list[dict[str, str]]
    ) -> str:
        """
        Generate a Mermaid sequence diagram.

        Args:
            participants: List of participant names
            interactions: List of interaction dicts with 'from', 'to', 'message'

        Returns:
            Mermaid sequence diagram syntax
        """

    def generate_state_diagram(
        self,
        states: list[str],
        transitions: list[tuple[str, str, str | None]]
    ) -> str:
        """
        Generate a Mermaid state diagram.

        Args:
            states: List of state names
            transitions: List of (from_state, to_state, label) tuples

        Returns:
            Mermaid state diagram syntax
        """
```

**Usage:**
```python
from cogant.viz.mermaid import MermaidGenerator

gen = MermaidGenerator()

# Generate flowchart
mermaid = gen.generate_flowchart(
    nodes=[
        ("A", "Read file"),
        ("B", "Parse AST"),
        ("C", "Build graph"),
        ("D", "Translate"),
    ],
    edges=[("A", "B"), ("B", "C"), ("C", "D")],
)

# Embed in Markdown
with open("pipeline.md", "w") as f:
    f.write(f"# Pipeline\n\n```mermaid\n{mermaid}\n```")
```

### StaticPlotter

Generate charts for analysis results.

```python
class StaticPlotter:
    def plot_complexity_distribution(
        self,
        report: ComplexityReport,
        bins: int = 10
    ) -> Any:
        """
        Plot histogram of cyclomatic complexity distribution.

        Args:
            report: ComplexityReport from analyzer
            bins: Number of histogram bins

        Returns:
            Matplotlib Figure or None
        """

    def plot_coupling_matrix(
        self,
        report: CouplingReport
    ) -> Any:
        """
        Plot coupling instability heatmap.

        Axes: module names
        Color: instability [0, 1] (red = high instability)
        """

    def plot_dead_code_distribution(
        self,
        report: DeadCodeReport
    ) -> Any:
        """
        Plot pie chart of dead code by kind.

        Kinds: UNUSED_IMPORT, UNUSED_FUNCTION, etc.
        """

    def plot_halstead_metrics(
        self,
        metrics: HalsteadMetrics
    ) -> Any:
        """Plot Halstead metrics (volume, difficulty, effort) as bar chart."""
```

### DashboardGenerator

Generate interactive self-contained HTML dashboards.

```python
class DashboardGenerator:
    def generate_comprehensive_dashboard(
        self,
        graph: ProgramGraph,
        semantic_mappings: SemanticMappings | None = None,
        complexity_report: ComplexityReport | None = None,
        coupling_report: CouplingReport | None = None,
    ) -> str:
        """
        Generate complete interactive dashboard.

        Args:
            graph: ProgramGraph to visualize
            semantic_mappings: Optional semantic mappings
            complexity_report: Optional complexity analysis
            coupling_report: Optional coupling analysis

        Returns:
            HTML string (self-contained, no external resources)
        """
```

**Usage:**
```python
from cogant.viz.dashboard.generator import DashboardGenerator

gen = DashboardGenerator()
html = gen.generate_comprehensive_dashboard(
    graph=program_graph,
    complexity_report=complexity_report,
    coupling_report=coupling_report,
)

with open("dashboard.html", "w") as f:
    f.write(html)

# Open in browser: dashboard.html
```

## Visualization Recipes

### Recipe: Generate Graph PNG + Complexity Heatmap

```python
from cogant.viz.png_export import PNGExporter
from cogant.viz.plots import StaticPlotter
from cogant.static.complexity import ComplexityAnalyzer

# Analyze complexity
analyzer = ComplexityAnalyzer()
complexity_report = analyzer.analyze_file(Path("my_module.py"))

# Visualize
exporter = PNGExporter()
graph_png = exporter.export_program_graph(graph, "output/graph.png")
complexity_png = exporter.export_complexity_analysis(complexity_report, "output/complexity.png")

print(f"Graph: {graph_png}")
print(f"Complexity: {complexity_png}")
```

### Recipe: Generate Mermaid for Markdown Documentation

```python
from cogant.viz.mermaid import MermaidGenerator
from cogant.graph.query import GraphQuery

query = GraphQuery(program_graph)

# Get function nodes
functions = query.find_by_kind("FUNCTION")
function_names = [n.name for n in functions[:10]]

# Generate class diagram
gen = MermaidGenerator()
diagram = gen.generate_class_diagram([
    {
        "name": f.name,
        "methods": ["__init__", "run", "process"],
        "attributes": ["status", "result"]
    }
    for f in functions[:5]
])

# Save to markdown
with open("API.md", "w") as f:
    f.write("# API Reference\n\n```mermaid\n")
    f.write(diagram)
    f.write("\n```\n")
```

### Recipe: Export Interactive Dashboard + PNG Report

```python
from cogant.viz.dashboard.generator import DashboardGenerator
from cogant.viz.png_export import PNGExporter

# Generate dashboard (interactive)
dash_gen = DashboardGenerator()
html = dash_gen.generate_comprehensive_dashboard(
    graph=program_graph,
    complexity_report=complexity_report,
)
with open("output/dashboard.html", "w") as f:
    f.write(html)

# Generate PNG report (static)
png_exp = PNGExporter()
png_path = png_exp.export_program_graph(program_graph, "output/graph.png")

print(f"Dashboard: output/dashboard.html (open in browser)")
print(f"PNG Report: {png_path}")
```

### Recipe: Generate PDF Report with Matrices + Graph

```python
from cogant.viz.pdf_export import PDFExporter
import numpy as np

exporter = PDFExporter()

# Prepare matrices (from semantic model)
A = np.array([[0.8, 0.2], [0.3, 0.7]])
B = [np.array([[1.0, 0.0], [0.0, 1.0]])]
C = np.array([0.7, 0.3])
D = np.array([0.5, 0.5])

# Export comprehensive report
pdf_path = exporter.export_report(
    graph=program_graph,
    mappings=semantic_mappings,
    analysis={"complexity": complexity_report, "coupling": coupling_report},
    output_path="output/report.pdf"
)

print(f"Report: {pdf_path}")
```

## Graceful Degradation

All visualization modules handle missing dependencies gracefully:

```python
from cogant.viz.png_export import PNGExporter
import logging

logger = logging.getLogger(__name__)

exporter = PNGExporter()
result = exporter.export_program_graph(graph, "output/graph.png")

if result is None:
    logger.warning("Matplotlib unavailable; PNG export skipped")
    # Pipeline continues; PNG just not generated
else:
    logger.info(f"PNG exported: {result}")
```

## Performance Notes

| Operation | Time | Notes |
|-----------|------|-------|
| PNG export (small graph <100 nodes) | 0.5-2s | matplotlib rendering |
| PDF export (medium graph 100-1000 nodes) | 2-10s | PDF generation + layout |
| Mermaid generation | 0.01-1s | Pure text generation |
| Dashboard generation | 1-5s | HTML assembly, optional matplotlib |
| Matrix visualization | 0.1-2s | matplotlib heatmap rendering |

## See Also

- `py/cogant/viz/AGENTS.md` — Agent guide with patterns
- `py/cogant/viz/README.md` — Module overview
- `py/cogant/export/` — Saves visualizations to disk
- `py/cogant/static/` — Produces analysis results to visualize
