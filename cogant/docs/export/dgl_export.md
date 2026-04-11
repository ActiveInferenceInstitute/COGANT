## DGL Export

### Format

DGL `DGLGraph` with node/edge features:

```python
from dgl import DGLGraph

g = DGLGraph()
g.add_nodes(num_nodes)
g.add_edges(src, dst)

# Node features
g.ndata['kind'] = node_kinds
g.ndata['role'] = node_roles
g.ndata['confidence'] = confidences
g.ndata['features'] = node_features
g.ndata['names'] = node_names

# Edge features
g.edata['kind'] = edge_kinds
g.edata['confidence'] = edge_confidences
g.edata['features'] = edge_features
```

### Export Example

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_project", config)

# Export to DGL (planned)
dgl_graph = bundle.export_dgl()  # planned

print(f"Nodes: {dgl_graph.num_nodes()}")
print(f"Edges: {dgl_graph.num_edges()}")
```

