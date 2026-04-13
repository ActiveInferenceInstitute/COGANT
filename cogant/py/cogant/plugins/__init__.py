"""COGANT Plugins: Plugin protocol system for extensibility."""

from cogant.plugins.base import (
    ExportPlugin,
    LanguagePlugin,
    NormalizerPlugin,
    Plugin,
    PluginMetadata,
    ProcessModelPlugin,
    StateSpacePlugin,
    TracePlugin,
    TranslationRulePlugin,
    ValidationPlugin,
    VisualizationPlugin,
)
from cogant.plugins.registry import PluginInfo, PluginRegistry


def discover_plugins() -> list[PluginInfo]:
    """Convenience wrapper: discover all installed COGANT plugins."""
    return PluginRegistry().discover()


__all__ = [
    # Base protocols
    "Plugin",
    "PluginMetadata",
    "LanguagePlugin",
    "TracePlugin",
    "NormalizerPlugin",
    "TranslationRulePlugin",
    "StateSpacePlugin",
    "ProcessModelPlugin",
    "ExportPlugin",
    "ValidationPlugin",
    "VisualizationPlugin",
    # Registry
    "PluginInfo",
    "PluginRegistry",
    "discover_plugins",
]
