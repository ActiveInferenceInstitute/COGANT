## Feature Engineering

### Default Features

**Node Features**:
1. One-hot NodeKind (13 dims)
2. One-hot SemanticRole (30 dims)
3. Confidence score (1 dim)
4. In/out degree (2 dims)
5. Type presence (1 dim)
6. Documentation presence (1 dim)
7. Attributes count (1 dim)

**Edge Features**:
1. One-hot EdgeKind (18 dims)
2. Confidence score (1 dim)
3. Label presence (1 dim)

### Optional Features

**Name Embedding**:
- Pre-trained language model (BERT, CodeBERT)
- 768 dimensions
- Optional, large memory overhead

**Documentation Embedding**:
- Docstring embedding via language model
- 768 dimensions
- Only if documentation present

**Subgraph Patterns**:
- Local neighborhood structure
- Motif counts (triangles, common patterns)
- Expensive to compute

### Custom Features

Users can define custom features:

```python
from cogant.plugins import ExportPlugin, PluginMetadata

class MyFeatureExporter(ExportPlugin):
    """Custom exporter with custom feature extraction."""
    
    def __init__(self):
        super().__init__(PluginMetadata(name="CustomFeatures", version="1.0.0"))
        self.supported_formats = {"custom_features"}

    def initialize(self, config): pass
    def shutdown(self): pass

    def export(self, bundle, output_path, fmt):
        graph = bundle.get("program_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        # Extract custom feature vectors per node
        node_features = [
            [len(n.get("name", "")), n.get("confidence", 0.0)]
            for n in nodes
        ]
        edge_features = [
            [e.get("confidence", 0.0), 1.0 if e.get("label") else 0.0]
            for e in edges
        ]
        # ... write to output_path ...

    def get_format_info(self, fmt):
        return {"name": "custom_features", "extension": ".pt"}
```

