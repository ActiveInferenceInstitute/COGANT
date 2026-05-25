# Agents — py/cogant/viz

## Owner
Visualization and User Interface Lead

## What Is the Viz Module

The `viz/` module produces **visual representations** of COGANT artifacts: program graphs, semantic models, analysis results, and metrics. All outputs are matplotlib-based PNG/PDF with optional Mermaid diagram support and self-contained HTML dashboards.

Key principle: **graceful degradation**. If matplotlib is unavailable, visualizations return `None` with a logged warning; the pipeline continues. SVG and DOT export require graphviz (optional).

## Pipeline Integration

```
stage 4: graph/         → ProgramGraph
    ↓
stage 6: translate/     → SemanticMappings
    ↓
stage 7: statespace/    → StateSpaceModel (A/B/C/D matrices)
    ↓
stages 8-10: process, export, validate
    ↓
(post-pipeline) viz/    → PNG, PDF, Mermaid, HTML dashboards
```

Visualization is a **post-pipeline consumer** — it runs after the 10-stage forward pipeline finishes, reading from the bundle produced by `export/` and the validation report from `validate/`. It is not itself a pipeline stage (see `PipelineConfig.stages`).

## Core Components

### Output Format Comparison

| Format | Generator | Use Case | Requires matplotlib | Requires graphviz | Self-contained HTML |
|--------|-----------|----------|---------------------|--------------------|---------------------|
| PNG | png_export.py | Quick review, inline in reports | Yes | No | No |
| PDF | pdf_export.py | Publication, multi-page reports | Yes | No | No |
| Mermaid | mermaid.py | Markdown, GitHub, wiki embedding | No | No | Yes (in HTML) |
| HTML site | bundle_site.py, html_renderer.py | Full bundle browsing | No | No | Yes |
| Interactive graph | cytoscape_view.py, graph_view.py | Web embedding, scalable | No | No | Yes |
| DOT | flow.py | Graphviz processing | No | Optional | No |
| HTML Dashboard | dashboard/ (generator.py, assets.py) | Interactive exploration | Yes (optional) | No | Yes |
| Inspection dashboard | inspection_dashboard.py | Artifact-first run review + graphical abstract | No | Optional for PNG abstract | Yes |
| Batch dashboard | batch_dashboard.py | Cross-target sweep summary (CSV + Markdown + Mermaid) | No | No | No |

### Single-target vs. batch dashboards

- **`DashboardGenerator`** (`dashboard/`) renders one rich, interactive HTML page for **one** translated target when callers already have in-memory graph/state-space objects.
- **`inspection_dashboard.py`** renders `site/inspection_dashboard.html` and `figures/graphical_abstract.*` from a completed run directory, so `cogant viz` and `run_all.py` outputs get a browsable review surface without rebuilding pipeline objects.
- **`BatchDashboardGenerator`** (`batch_dashboard.py`) consolidates **many** targets from a staging-root `run_all` sweep into `output/dashboard/` (Markdown + CSV + JSON + four Mermaid charts). Pure-stdlib; used as the post-batch step by `run_all.py`. See [`docs/reference/batch_dashboard.md`](../../../docs/reference/batch_dashboard.md).

### Visualization Modules (21 public files in `viz/` + `viz/dashboard/`)

The `viz/` package currently ships `ablation_view.py`, `batch_dashboard.py`, `boundary.py`, `bundle_site.py`, `cytoscape_view.py`, `diff_view.py`, `export_view.py`, `flow.py`, `gantt.py`, `graph_view.py`, `html_renderer.py`, `inspection_dashboard.py`, `matrix_view.py`, `mermaid.py`, `network_view.py`, `pdf_export.py`, `pipeline_view.py`, `plots.py`, `png_export.py`, `semantic_view.py`, and `static_analysis_view.py`, plus the `dashboard/` subpackage (`generator.py`, `assets.py`). The headline modules are documented below; see each file's module docstring for the full API surface.

### Headline modules

**png_export.py** — PNG evidence renderers
- Render program graphs, state-space factor views, matrices, and roundtrip panels as matplotlib figures
- Exports PNG files plus `.figure.json` sidecars with source digests, displayed counts, panels, and QA metadata
- Public helpers include `render_program_graph_png()`, `render_state_space_png()`, `render_connections_matrix_png()`, `render_roundtrip_diff_png()`, and `render_all_pngs()`
- Graceful fallback if matplotlib is unavailable

**plots.py** — `StaticPlotter`
- Generate charts: histograms, scatter plots, heatmaps, bar charts
- Complexity distribution histograms
- Coupling instability heatmaps
- Dead code Pareto charts
- Methods: `plot_complexity_distribution()`, `plot_coupling_matrix()`, `plot_dead_code_distribution()`

**mermaid.py** — `MermaidGenerator`
- Generate Mermaid diagram syntax (text format)
- Diagrams: flowcharts, class diagrams, sequence diagrams, state diagrams, entity-relationship
- No external dependencies
- Methods: `generate_flowchart()`, `generate_class_diagram()`, `generate_sequence_diagram()`

**boundary.py** — `BoundaryMapper`
- Visualize architectural boundaries (modules, packages, layers)
- Highlights cross-boundary dependencies
- Methods: `map_module_boundaries()`, `highlight_violations()`

**semantic_view.py** — `SemanticVisualizer`
- Visualize state spaces and semantic mappings
- Shows HIDDEN_STATE, OBSERVATION, ACTION, POLICY assignments
- Renders A/B/C/D matrices
- Methods: `visualize_state_space()`, `visualize_semantic_mappings()`

**graph_view.py** — `GraphVisualizer`
- Interactive graph exploration (self-contained HTML with JS)
- Node/edge filtering, search, clustering
- Force-directed layout visualization
- Methods: `generate_interactive_graph()`, `with_search()`, `with_filters()`

**gantt.py** — `GanttRenderer`
- Timeline visualization of process stages
- Pipeline execution timings
- Task dependencies
- Methods: `render_pipeline_timeline()`, `render_task_dependencies()`

### Additional modules

**pdf_export.py** — `PDFExporter`
- Multi-page PDF export via matplotlib
- Renders: full graph layout, semantic mappings, A/B/C/D matrices, Markov blanket partitions
- Publication-quality vector graphics
- Methods: `export_program_graph()`, `export_semantic_model()`, `export_matrices()`, `export_report()`

**matrix_view.py** — `MatrixVisualizer`
- Visualize Active Inference matrices as heatmaps and bar charts
- A: Likelihood matrix (observations vs hidden states)
- B: State transition matrix (per action)
- C: Preference vector (goal prior) — bar chart
- D: Initial state prior — bar chart
- Methods: `plot_A_matrix()`, `plot_B_matrix()`, `plot_C_vector()`, `plot_D_vector()`, `plot_all_matrices()`

**pipeline_view.py** — `PipelineVisualizer`
- Render 10-stage pipeline flowchart
- Shows stage timings and resource usage
- Highlights bottlenecks
- Methods: `render_pipeline_stages()`, `with_timings()`, `with_bottleneck_highlights()`

**static_analysis_view.py** — `StaticAnalysisVisualizer`
- Visualization for complexity, coupling, dead code, metrics results
- Complexity hotspot heatmaps
- Coupling instability scatter plot (abstractness vs instability)
- Dead code distribution pie chart
- Halstead metrics dashboard
- Methods: `visualize_complexity()`, `visualize_coupling()`, `visualize_dead_code()`, `visualize_halstead()`

**network_view.py** — `NetworkVisualizer`
- Network analysis visualization
- Centrality-based node sizing
- Community color-coding
- Cycle highlighting
- Methods: `visualize_centrality()`, `visualize_communities()`, `visualize_cycles()`, `visualize_hotspots()`

### Dashboard Infrastructure

**dashboard/generator.py** — `DashboardGenerator`
- Combines multiple visualization modules into a unified HTML dashboard
- Tabbed interface for different views
- Interactive filtering and search

**inspection_dashboard.py** — artifact-first dashboard and graphical abstract
- Reads completed `cogant/output/<target>/` directories directly
- Writes `site/inspection_dashboard.html`, `figures/graphical_abstract.svg`, and a best-effort PNG abstract
- Summarizes graph counts, semantic roles, matrix shapes, blanket roles, hotspots, figure evidence, artifact presence, and roundtrip status

**dashboard/assets.py** — Inlined CSS/JS assets used by the dashboard for fully self-contained HTML output.

The Cytoscape-based interactive view lives alongside the other top-level modules at `viz/cytoscape_view.py` (not under `dashboard/`).

## Common Usage Patterns

### Export a Program Graph to PNG

```python
from pathlib import Path
from cogant.viz.png_export import render_program_graph_png

png_path = render_program_graph_png(
    graph_json=Path("output/data/program_graph.json"),
    output_path=Path("output/figures/program_graph.png"),
    source_label="data/program_graph.json",
)
print(f"Graph exported to {png_path}")
```

### Visualize Complexity Analysis

```python
from cogant.viz.static_analysis_view import StaticAnalysisVisualizer
from cogant.static.complexity import ComplexityAnalyzer

# Analyze file
analyzer = ComplexityAnalyzer()
report = analyzer.analyze_file(Path("my_module.py"))

# Visualize
viz = StaticAnalysisVisualizer()
fig = viz.visualize_complexity(report)
if fig:
    fig.savefig("output/complexity.png", dpi=150)
else:
    print("Matplotlib unavailable for visualization")
```

### Generate Coupling Heatmap

```python
from cogant.viz.plots import StaticPlotter
from cogant.static.coupling import CouplingAnalyzer

# Analyze coupling
analyzer = CouplingAnalyzer()
report = analyzer.analyze(import_graph, abstract_classes, concrete_classes)

# Plot
plotter = StaticPlotter()
fig = plotter.plot_coupling_matrix(report)
if fig:
    fig.savefig("output/coupling_heatmap.png")
```

### Create a Mermaid Flowchart (No Dependencies)

```python
from cogant.viz.mermaid import MermaidGenerator

generator = MermaidGenerator()

# Simple flowchart
flowchart_text = generator.generate_flowchart(
    nodes=[
        ("A", "Read file"),
        ("B", "Parse AST"),
        ("C", "Extract symbols"),
        ("D", "Build graph"),
    ],
    edges=[
        ("A", "B"),
        ("B", "C"),
        ("C", "D"),
    ]
)

with open("output/pipeline.mmd", "w") as f:
    f.write(flowchart_text)

# Embed in Markdown
markdown = f"```mermaid\n{flowchart_text}\n```\n"
print(markdown)
```

### Generate Interactive Graph Dashboard

```python
from cogant.viz.dashboard.generator import DashboardGenerator

generator = DashboardGenerator()
html = generator.generate_comprehensive_dashboard(
    graph=program_graph,
    semantic_mappings=mappings,
    complexity_report=complexity_report,
    coupling_report=coupling_report,
)

with open("output/dashboard.html", "w") as f:
    f.write(html)

print("Dashboard: output/dashboard.html")
```

### Generate Artifact-First Inspection Dashboard

```python
from cogant.viz.inspection_dashboard import write_inspection_artifacts

written = write_inspection_artifacts("output/calculator")
print(written["inspection_dashboard_html"])
```

### Export Matrices to PDF

```python
from cogant.viz.pdf_export import PDFExporter
import numpy as np

exporter = PDFExporter()

# A/B/C/D matrices from semantic model
A_matrix = np.array([[0.8, 0.2], [0.3, 0.7]])  # Likelihood
B_matrices = [np.array([[1.0, 0.0], [0.0, 1.0]])]  # State transitions
C_prior = np.array([0.7, 0.3])  # Goal preferences
D_prior = np.array([0.5, 0.5])  # Initial state

pdf_path = exporter.export_matrices(
    A=A_matrix,
    B=B_matrices,
    C=C_prior,
    D=D_prior,
    output_path="output/matrices.pdf"
)
print(f"Matrices exported to {pdf_path}")
```

### Visualize Network Hotspots

```python
from cogant.viz.network_view import NetworkVisualizer
from cogant.graph.analysis import GraphAnalyzer

analyzer = GraphAnalyzer(program_graph)
hotspots = analyzer.find_hotspots()

viz = NetworkVisualizer()
fig = viz.visualize_hotspots(hotspots)
if fig:
    fig.savefig("output/hotspots.png")
```

## Visualization Recipe Book

### "I want to visualize my program graph"
→ Use `png_export.export_program_graph()` or `pdf_export.export_program_graph()` for static images
→ Use `dashboard.generator.DashboardGenerator` for interactive HTML exploration

### "I want to show complexity hotspots"
→ Use `static_analysis_view.visualize_complexity()` for heatmap
→ Use `plots.plot_complexity_distribution()` for histogram of all functions

### "I want a Mermaid diagram for my documentation"
→ Use `mermaid.MermaidGenerator.generate_flowchart()` or `.generate_class_diagram()`
→ Output is plain text; embed in Markdown with triple backticks

### "I want to embed a graph in a web app"
→ Use `graph_view.GraphVisualizer` or `cytoscape_view.CytoscapeVisualizer` for interactive JS-based visualization
→ Use `bundle_site` / `html_renderer` for full self-contained HTML bundles

### "I want to publish a report with graph visualizations"
→ Use `pdf_export.PDFExporter` to render multi-page PDF with all graphs, matrices, and metadata
→ Or use `png_export` + matplotlib's figure/subplot layout for custom report generation

### "I want to identify architectural violations"
→ Use `boundary.BoundaryMapper.highlight_violations()` to show cross-boundary calls
→ Or use network analysis (`GraphAnalyzer`) to compute clustering and compare against expected boundaries

## Responsibilities & Coordination

### Core Responsibilities
- Render program graphs as PNG/PDF (vector or bitmap)
- Generate Mermaid diagram syntax (no dependencies)
- Create interactive HTML dashboards with search/filter
- Visualize analysis results: complexity, coupling, dead code, metrics
- Render semantic mappings and A/B/C/D matrices
- Support architectural boundary visualization
- Graceful degradation if matplotlib/graphviz unavailable

### Input Sources
- **graph/** — ProgramGraph for visualization
- **static/** — ComplexityReport, CouplingReport, DeadCodeReport, CodeMetrics
- **translate/** — SemanticMappings (HIDDEN_STATE, OBSERVATION, ACTION, etc.)
- **statespace/** — StateSpaceModel (A/B/C/D matrices)
- **validate/** — ValidationReport for quality metrics

### Output Sinks
- **export/** — stores PNG/PDF/SVG/HTML files in output bundle
- **Users/browsers** — HTML dashboards for interactive exploration
- **Documentation** — Mermaid diagrams embeddable in Markdown/Confluence

### Guarantees
- **No external deps** for Mermaid generation
- **Graceful fallback** if matplotlib unavailable
- **Self-contained HTML** for dashboards (no external CDNs)
- **Publication-quality PDF** for reports
- **Responsive design** for HTML dashboards

## How to Extend

### Add a New Chart Type
1. Add method to `StaticPlotter` (e.g., `plot_my_metric()`)
2. Implement using matplotlib (numpy for data processing)
3. Return matplotlib Figure or None
4. Add tests with sample data

### Add a New Mermaid Diagram Type
1. Add method to `MermaidGenerator` (e.g., `generate_my_diagram()`)
2. Implement Mermaid syntax generation (string building)
3. Document Mermaid syntax expected
4. Test by embedding in HTML/Markdown

### Add a New Interactive Dashboard View
1. Add view class to `dashboard/` (e.g., `my_view.py`)
2. Implement to generate HTML/CSS/JS (or use Cytoscape, D3, Plotly)
3. Wire into `DashboardGenerator.generate_comprehensive_dashboard()`
4. Test with sample data

### Add SVG Export for a New Artifact
1. Extend `graph_view.py` or `cytoscape_view.py` for interactive SVG output, or add a matplotlib-based module alongside `pdf_export.py`
2. Document any optional graphviz dependency
3. Provide pure-SVG fallback where possible

## Performance Notes

- **PNG/PDF rendering**: ~100-500ms per graph (size-dependent)
- **Interactive dashboard**: ~1-2s to generate, ~instant to load in browser
- **Mermaid generation**: ~10-50ms (minimal)
- **Large graphs**: Consider `network_view` or `cytoscape` instead of png_export for > 1000 nodes

## See Also

- `py/cogant/viz/README.md` — module overview
- `py/cogant/export/` — saves visualization outputs to disk
- `py/cogant/static/` — produces analysis results to visualize
- `py/cogant/graph/` — provides program graphs to visualize
- `py/cogant/statespace/` — provides matrices to visualize
