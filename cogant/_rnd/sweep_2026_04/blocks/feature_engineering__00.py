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
