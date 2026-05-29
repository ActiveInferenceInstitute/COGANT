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

2. **YAML loader schema configs** (used by defaults/loaders/presets):
   :class:`CogantConfig`, :class:`ExportConfig`,
   :class:`ValidationConfig`, :class:`LanguageConfig`, etc. The
   high-level pipeline YAML schema remains
   ``cogant.config.schema.PipelineConfig`` (distinct from the composable
   :class:`~cogant.config.pipeline.PipelineConfig`).
"""

# Composable per-stage pydantic configs (primary export).
# Defaults and presets
from .defaults import (
    COMPREHENSIVE_PIPELINE_CONFIG,
    DEFAULT_COGANT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_JAVA_CONFIG,
    DEFAULT_JAVASCRIPT_CONFIG,
    DEFAULT_PIPELINE_CONFIG,
    DEFAULT_PYTHON_CONFIG,
    DEFAULT_VALIDATION_CONFIG,
    GNN_EXPORT_CONFIG,
    LENIENT_VALIDATION_CONFIG,
    MINIMAL_PIPELINE_CONFIG,
    PRESETS,
    STRICT_VALIDATION_CONFIG,
    get_preset,
)
from .gnn import GNNConfig
from .graph import GraphConfig
from .ingest import IngestConfig

# Configuration loaders
from .loaders import ConfigLoader, ConfigLoadError
from .pipeline import PipelineConfig

# Named presets
from .presets import (
    get_preset as get_named_preset,
)
from .presets import (
    list_presets,
)
from .reverse import ReverseConfig

# YAML loader configuration schemas (see ``config.schema``).
#
# NOTE: ``schema.PipelineConfig`` is intentionally *not* re-exported at
# the top level; the composable ``pipeline.PipelineConfig`` owns the
# ``cogant.config.PipelineConfig`` name. YAML pipeline files use
# ``from cogant.config.schema import PipelineConfig``.
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
from .statespace import StatespaceConfig
from .translate import TranslateConfig

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
