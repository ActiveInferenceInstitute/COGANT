from .schema import CogantConfig as CogantConfig, ExportConfig as ExportConfig, ExportFormat as ExportFormat, LanguageConfig as LanguageConfig, LogLevel as LogLevel, PipelineConfig as PipelineConfig, PipelineStage as PipelineStage, ValidationConfig as ValidationConfig, ValidationLevel as ValidationLevel
from _typeshed import Incomplete
from typing import Any

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
