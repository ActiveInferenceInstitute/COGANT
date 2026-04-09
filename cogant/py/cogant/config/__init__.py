"""
COGANT Configuration Module

Comprehensive configuration system for the COGANT framework, including:
- System-wide settings (CogantConfig)
- Pipeline execution configuration (PipelineConfig)
- Export/output configuration (ExportConfig)
- Validation configuration (ValidationConfig)
- Configuration loading from YAML/JSON
- Sensible defaults and preset configurations
"""

# Configuration schemas
from .schema import (
    CogantBaseConfig,
    CogantConfig,
    PipelineConfig,
    ExportConfig,
    ValidationConfig,
    LanguageConfig,
    PipelineStage,
    LogLevel,
    ExportFormat,
    ValidationLevel,
)

# Configuration loaders
from .loaders import ConfigLoader, ConfigLoadError

# Defaults and presets
from .defaults import (
    DEFAULT_COGANT_CONFIG,
    DEFAULT_PIPELINE_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_VALIDATION_CONFIG,
    MINIMAL_PIPELINE_CONFIG,
    COMPREHENSIVE_PIPELINE_CONFIG,
    GNN_EXPORT_CONFIG,
    STRICT_VALIDATION_CONFIG,
    LENIENT_VALIDATION_CONFIG,
    DEFAULT_PYTHON_CONFIG,
    DEFAULT_JAVASCRIPT_CONFIG,
    DEFAULT_JAVA_CONFIG,
    PRESETS,
    get_preset,
)

# Named presets
from .presets import (
    get_preset as get_named_preset,
    list_presets,
)

__all__ = [
    # Schemas
    "CogantBaseConfig",
    "CogantConfig",
    "PipelineConfig",
    "ExportConfig",
    "ValidationConfig",
    "LanguageConfig",
    "PipelineStage",
    "LogLevel",
    "ExportFormat",
    "ValidationLevel",
    # Loaders
    "ConfigLoader",
    "ConfigLoadError",
    # Defaults
    "DEFAULT_COGANT_CONFIG",
    "DEFAULT_PIPELINE_CONFIG",
    "DEFAULT_EXPORT_CONFIG",
    "DEFAULT_VALIDATION_CONFIG",
    "MINIMAL_PIPELINE_CONFIG",
    "COMPREHENSIVE_PIPELINE_CONFIG",
    "GNN_EXPORT_CONFIG",
    "STRICT_VALIDATION_CONFIG",
    "LENIENT_VALIDATION_CONFIG",
    "DEFAULT_PYTHON_CONFIG",
    "DEFAULT_JAVASCRIPT_CONFIG",
    "DEFAULT_JAVA_CONFIG",
    "PRESETS",
    "get_preset",
    # Named presets
    "get_named_preset",
    "list_presets",
]
