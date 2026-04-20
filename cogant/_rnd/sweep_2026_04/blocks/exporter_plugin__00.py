from cogant.plugins import ExportPlugin, PluginMetadata
from typing import Dict, Any

class MyExportPlugin(ExportPlugin):
    """Custom GNN exporter."""
    
    def __init__(self):
        super().__init__(PluginMetadata(name="MyFormat", version="1.0.0"))
        self.supported_formats = {"myformat"}
    
    def initialize(self, config: Dict[str, Any]) -> None:
        pass
    
    def shutdown(self) -> None:
        pass
    
    def export(self, bundle: Dict[str, Any], output_path: str, fmt: str) -> None:
        """Export bundle to custom format.
        
        Args:
            bundle: Analysis bundle dict.
            output_path: Destination path.
            fmt: Format name.
        """
        # ... export logic ...
        pass
    
    def get_format_info(self, fmt: str) -> Dict[str, Any]:
        """Return format info."""
        return {"name": "myformat", "extension": ".myformat"}
