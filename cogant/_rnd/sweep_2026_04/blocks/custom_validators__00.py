from cogant.plugins import ValidationPlugin, PluginMetadata

class TodoValidator(ValidationPlugin):
    def __init__(self):
        super().__init__(PluginMetadata(name="TodoCheck", version="1.0.0"))

    def initialize(self, config): pass
    def shutdown(self): pass

    def validate(self, bundle):
        issues = []
        graph = bundle.get("program_graph", {})
        for node in graph.get("nodes", []):
            if "TODO" in (node.get("documentation") or ""):
                issues.append({
                    "level": "INFO",
                    "code": "TODO001",
                    "message": f"TODO comment in {node.get('name')}",
                    "node_id": node.get("id"),
                })
        return issues

    def get_check_info(self):
        return {"name": "todo_check", "description": "Detect TODO comments"}
