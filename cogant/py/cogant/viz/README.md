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

BoundaryMapper analyzes and visualizes module boundaries, type boundaries, and cross-boundary couplings with Mermaid diagrams.

PNGExporter converts charts and graphs to PNG format.

## Usage

```python
from cogant.viz import GraphVisualizer, MermaidGenerator, DashboardGenerator
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
```
