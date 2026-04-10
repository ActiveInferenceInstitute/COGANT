from typing import Any

from _typeshed import Incomplete

from .schema import CogantConfig as CogantConfig
from .schema import ExportConfig as ExportConfig
from .schema import ExportFormat as ExportFormat
from .schema import LanguageConfig as LanguageConfig
from .schema import LogLevel as LogLevel
from .schema import PipelineConfig as PipelineConfig
from .schema import PipelineStage as PipelineStage
from .schema import ValidationConfig as ValidationConfig
from .schema import ValidationLevel as ValidationLevel

def create_minimal_preset() -> dict[str, Any]: ...
def create_standard_preset() -> dict[str, Any]: ...
def create_comprehensive_preset() -> dict[str, Any]: ...
def create_gnn_focused_preset() -> dict[str, Any]: ...
def create_security_preset() -> dict[str, Any]: ...

PRESETS: Incomplete

def get_preset(name: str) -> dict[str, Any]: ...
def list_presets() -> list[str]: ...
