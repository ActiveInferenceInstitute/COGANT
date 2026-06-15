## Feature engineering

Default and optional **tensor** features for PyTorch Geometric / DGL-style consumers are described here. The shipped `ExportConfig.gnn_*` fields (`py/cogant/config/schema.py`) align with this policy; native `Data` / `DGLGraph` helpers remain on the [roadmap](../roadmap/README.md) where examples say “planned”.

### Default features

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

### Custom features

Implement an [`ExportPlugin`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/py/cogant/plugins/base.py) (see [Plugins](../plugins/README.md)):

```python
from cogant.plugins import ExportPlugin, PluginMetadata

class MyFeatureExporter(ExportPlugin):
    """Custom exporter with custom feature extraction."""

    def __init__(self) -> None:
        super().__init__(PluginMetadata(name="CustomFeatures", version="1.0.0", author="you"))
        self.supported_formats = {"custom_features"}

    def initialize(self, config): ...
    def shutdown(self) -> None: ...

    def export(self, bundle, output_path: str, format: str) -> None:
        # Implement: read bundle["program_graph"], compute features, write under output_path.
        pass

    def get_format_info(self, format: str):
        return {"name": "custom_features", "extension": ".pt"}
```

### See also

- [PyTorch Geometric export](pytorch_geometric_export.md) · [DGL export](dgl_export.md)
- [Plugins](../plugins/README.md)
