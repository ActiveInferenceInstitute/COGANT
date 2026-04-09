## Visualization API

### Graph Visualization

```python
from cogant.viz import GraphVisualizer

visualizer = GraphVisualizer()
visualizer.from_program_graph(bundle.program_graph())

# Cluster nodes
visualizer.cluster_by_package()
visualizer.cluster_by_language()
visualizer.cluster_by_service()

# Filter by edge type
visualizer.filter_by_edge_type("calls")

# Render
visualizer.render_html("graph.html")
visualizer.render_svg("graph.svg")

# Export as JSON
d3_data = visualizer.to_d3_json()
```

### Semantic Visualization

```python
from cogant.viz import SemanticVisualizer

sem_viz = SemanticVisualizer()
sem_viz.from_state_space(bundle.state_space_model())
sem_viz.render_html("semantic.html")
```

### Gantt/Timeline Visualization

```python
from cogant.viz import GanttRenderer

gantt = GanttRenderer()
gantt.from_process_model(bundle.process_model())
gantt.render_html("gantt.html")
```

### Difference Visualization

```python
from cogant.viz import DiffVisualizer

diff = DiffVisualizer(bundle1_data, bundle2_data)
diff.render_html("diff.html")
diff_json = diff.render_json()
```

### HTML Site Renderer

```python
from cogant.viz import HTMLSiteRenderer
import json

bundle_data = json.loads(bundle.to_json())
renderer = HTMLSiteRenderer(bundle_data)
index_path = renderer.render("html_site/")
```

