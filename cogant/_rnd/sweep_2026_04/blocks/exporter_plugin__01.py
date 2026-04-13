import json
from cogant.plugins import ExportPlugin, PluginMetadata

class CustomJsonExporter(ExportPlugin):
    """Custom JSON format."""
    
    def __init__(self):
        super().__init__(PluginMetadata(name="CustomJSON", version="1.0.0"))
        self.supported_formats = {"custom_json"}
    
    def initialize(self, config): pass
    def shutdown(self): pass
    
    def export(self, bundle, output_path, fmt):
        graph = bundle.get("program_graph", {})
        data = {
            "format": "custom_json",
            "version": "1.0.0",
            "nodes": [
                {
                    "id": n.get("id"),
                    "name": n.get("name"),
                    "kind": n.get("kind"),
                }
                for n in graph.get("nodes", [])
            ],
            "edges": [
                {
                    "from": e.get("source"),
                    "to": e.get("target"),
                    "kind": e.get("kind"),
                }
                for e in graph.get("edges", [])
            ],
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def get_format_info(self, fmt):
        return {"name": "custom_json", "extension": ".cjson"}
