from cogant.plugins import ValidationPlugin, PluginMetadata
from typing import Dict, Any, List

class MyValidationPlugin(ValidationPlugin):
    """Custom validation plugin."""
    
    def __init__(self):
        super().__init__(PluginMetadata(name="MyValidator", version="1.0.0"))
    
    def initialize(self, config: Dict[str, Any]) -> None:
        pass
    
    def shutdown(self) -> None:
        pass
    
    def validate(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate bundle contents.
        
        Args:
            bundle: Analysis bundle dict.
        
        Returns:
            List of issue dicts.
        """
        issues: List[Dict[str, Any]] = []
        # Validation logic...
        return issues
    
    def get_check_info(self) -> Dict[str, Any]:
        return {"name": "custom_check", "description": "Custom validation"}
