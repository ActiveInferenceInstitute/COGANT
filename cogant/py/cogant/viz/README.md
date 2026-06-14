# Viz

Generates interactive HTML visualizations of program graphs, semantic models, process timelines, and validation reports. Supports multiple visualization formats and self-contained HTML with embedded charts and Mermaid diagrams.

## API

GraphVisualizer renders program graphs as interactive D3.js visualizations with node clustering, edge filtering, pan/zoom, and tooltips. Includes methods for D3Node and D3Link representation.

SemanticVisualizer renders semantic state space models showing states, observations, actions, policies, and transitions with styling for inferred vs direct mappings.

GanttRenderer renders process models as timeline/Gantt charts showing pipeline stages, dependencies, expected ordering, critical path, and parallel groups.

DiffVisualizer generates comparisons between bundles with change highlighting and diff view.

MermaidGenerator produces class diagrams, dependency graphs, state diagrams, sequence diagrams, flowcharts, and Active Inference loop diagrams in Mermaid syntax.

StaticPlotter generates bar charts, histograms, and tables using inline SVG for node type distribution, complexity metrics, and other statistics.

HTMLSiteRenderer is the main entry point generating self-contained HTML with tabbed interface, embedded visualizations, and comprehensive data views.

DashboardGenerator produces production-quality interactive HTML dashboards with tabbed navigation, embedded SVG charts, Mermaid diagrams, and comprehensive data views.

Inspection dashboard helpers read a completed `cogant/output/<target>/` directory directly. `write_inspection_artifacts()` emits `site/inspection_dashboard.html`, `figures/graphical_abstract.svg`, and, when matplotlib is available, a native `figures/graphical_abstract.png` from the actual `data/`, `gnn_package/`, `figures/`, `analysis/`, `reports/`, and `roundtrip/` artifacts. This is the fastest human review path after a run because it does not require holding pipeline objects in memory.

`inspection_dashboard.py` is now a compatibility shim. The implementation lives
under `inspection/`: `model.py` builds the artifact-derived inspection model,
`abstract.py` renders the graphical abstract, `details.py` writes companion
figures and sidecars, `html.py` renders the dashboard, and `writer.py`
orchestrates the public `write_inspection_artifacts()` path.

MatrixVisualizer renders Active Inference A/B/C/D matrices and now includes `summarize_matrices()` plus `plot_interpretability_panel()` for one-page diagnostics of likelihoods, transitions, preferences, and priors. The B tensor selector supports both `(state, state, action)` and compatibility `(action, state, state)` conventions and reports which slice convention was used.

NetworkView ranks codebase hotspots with `summarize_hotspots()` and emits Mermaid diagrams that group critical, important, and contextual nodes. This gives large program graphs a compact human inspection path before opening the full D3 or PNG graph.

BoundaryMapper analyzes and visualizes module boundaries, type boundaries, and cross-boundary couplings with Mermaid diagrams.

PNG raster helpers convert charts and graphs to PNG format. `render_all_pngs()` writes sibling PNGs for program graphs, Mermaid, SVG, DOT, state-space factors, A/B/C/D connections, process Gantt charts, Markov blankets, GNN markdown pages plus an all-page mosaic, summary covers, the compact `interpretability_overview.png` dashboard, and the inspection dashboard / graphical abstract companions. Dashboard SVG fallbacks are allowed for exploratory review, but registered manuscript PNGs use native renderers and strict promotion rejects degraded placeholders.

## Usage

```python
from cogant.viz import (
    DashboardGenerator,
    GraphVisualizer,
    MatrixVisualizer,
    MermaidGenerator,
    render_all_pngs,
    write_inspection_artifacts,
)
from cogant.process import TimelineBuilder

# Graph visualization
graph_viz = GraphVisualizer()
graph_viz.from_program_graph(graph_dict)
graph_html = graph_viz.to_html()

# Mermaid diagrams
mermaid_gen = MermaidGenerator()
class_diagram = mermaid_gen.generate_class_diagram(graph)
state_diagram = mermaid_gen.generate_state_diagram(state_space)

# Dashboard
dashboard = DashboardGenerator(
    graph, state_space, process_model,
    mappings, mermaid_diagrams, validation_report,
    repo_name="my_repo"
)
dashboard.generate("output.html")

# Matrix interpretability
matrix_viz = MatrixVisualizer()
diagnostics = matrix_viz.summarize_matrices({"A": A, "B": B, "C": C, "D": D})
panel = matrix_viz.plot_interpretability_panel({"A": A, "B": B, "C": C, "D": D})
matrix_viz.to_png(panel, "generative_model_panel.png")

# One-shot PNG rasterization for a completed run directory
written = render_all_pngs("output/calculator")

# Artifact-first dashboard + graphical abstract for a completed run directory
review = write_inspection_artifacts("output/calculator")
```
