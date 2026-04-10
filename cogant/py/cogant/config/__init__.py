"""
COGANT Configuration Module

Comprehensive configuration system for the COGANT framework.

Two layers coexist here:

1. **Composable per-stage pydantic configs** (preferred for new code):
   :class:`PipelineConfig` plus its sub-configs (:class:`IngestConfig`,
   :class:`GraphConfig`, :class:`TranslateConfig`, :class:`StatespaceConfig`,
   :class:`GNNConfig`, :class:`ReverseConfig`). Every stage and method
   should take one of these — no global flags, no singletons. Configs
   are frozen; use :meth:`PipelineConfig.override` to derive variants.

2. **Legacy schema configs** (still used by the defaults/loaders/presets
   subsystem): :class:`CogantConfig`, :class:`ExportConfig`,
   :class:`ValidationConfig`, :class:`LanguageConfig`, etc. The legacy
   high-level pipeline schema is still available as
   ``cogant.config.schema.PipelineConfig`` for code that needs it.
"""

# Composable per-stage pydantic configs (primary export).
from .gnn import GNNConfig
from .graph import GraphConfig
from .ingest import IngestConfig
from .pipeline import PipelineConfig
from .reverse import ReverseConfig
from .statespace import StatespaceConfig
from .translate import TranslateConfig

# Legacy high-level configuration schemas.
#
# NOTE: the legacy ``schema.PipelineConfig`` is intentionally *not*
# re-exported at the top level; the composable ``pipeline.PipelineConfig``
# owns the ``cogant.config.PipelineConfig`` name. External callers that
# want the legacy schema should import it as
# ``from cogant.config.schema import PipelineConfig as LegacyPipelineSchema``.
from .schema import (
    CogantBaseConfig,
    CogantConfig,
    ExportConfig,
    ExportFormat,
    LanguageConfig,
    LogLevel,
    PipelineStage,
    ValidationConfig,
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
    # Composable per-stage configs (new)
    "PipelineConfig",
    "IngestConfig",
    "GraphConfig",
    "TranslateConfig",
    "StatespaceConfig",
    "GNNConfig",
    "ReverseConfig",
    # Legacy schemas
    "CogantBaseConfig",
    "CogantConfig",
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
