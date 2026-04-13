from cogant.plugins import ValidationPlugin, PluginMetadata

class ComplexityValidator(ValidationPlugin):
    """Flags overly complex functions."""
    
    def __init__(self):
        super().__init__(PluginMetadata(name="ComplexityCheck", version="1.0.0"))
        self._max_complexity = 10
    
    def initialize(self, config):
        self._max_complexity = config.get("max_complexity", 10)
    
    def shutdown(self): pass
    
    def validate(self, bundle):
        issues = []
        graph = bundle.get("program_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        
        for node in nodes:
            if node.get("kind") != "FUNCTION":
                continue
            callees = [e for e in edges if e.get("source") == node.get("id")]
            if len(callees) > self._max_complexity:
                issues.append({
                    "level": "WARNING",
                    "code": "COMPLEX001",
                    "message": f"{node.get('name')} has complexity {len(callees)}",
                    "node_id": node.get("id"),
                    "suggested_action": "Consider refactoring",
                })
        return issues
    
    def get_check_info(self):
        return {"name": "complexity", "description": "Function complexity check"}
