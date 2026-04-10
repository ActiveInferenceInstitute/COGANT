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

DEFAULT_COGANT_CONFIG: Incomplete
DEFAULT_PYTHON_CONFIG: Incomplete
DEFAULT_JAVASCRIPT_CONFIG: Incomplete
DEFAULT_JAVA_CONFIG: Incomplete
DEFAULT_LANGUAGE_CONFIGS: Incomplete
DEFAULT_STAGES: Incomplete
DEFAULT_PIPELINE_CONFIG: Incomplete
MINIMAL_PIPELINE_CONFIG: Incomplete
COMPREHENSIVE_PIPELINE_CONFIG: Incomplete
DEFAULT_EXPORT_CONFIG: Incomplete
MINIMAL_EXPORT_CONFIG: Incomplete
GNN_EXPORT_CONFIG: Incomplete
DEFAULT_VALIDATION_CONFIG: Incomplete
STRICT_VALIDATION_CONFIG: Incomplete
LENIENT_VALIDATION_CONFIG: Incomplete
PRESETS: Incomplete

def get_preset(name: str) -> dict[str, Any]: ...
