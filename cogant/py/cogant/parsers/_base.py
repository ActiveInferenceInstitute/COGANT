"""Shared base class for COGANT language parser plugins.

Eliminates the repeated __init__ / initialize / shutdown boilerplate that is
identical across the regex-based language parsers (Go, Python, Rust,
TypeScript). Subclasses declare four class variables and override only the
language-specific parsing methods.
"""

from __future__ import annotations

from typing import Any, ClassVar

from cogant.plugins.base import LanguagePlugin, PluginMetadata  # noqa: E402


class CogantLanguagePlugin(LanguagePlugin):
    """Base class for COGANT language parser plugins.

    Subclasses must declare:
        PLUGIN_NAME        — stable identifier used in PluginMetadata.name
        PLUGIN_DESCRIPTION — one-line description used in PluginMetadata.description
        SUPPORTED_LANGUAGES — set of language string identifiers
        SUPPORTED_EXTENSIONS — set of file extension strings (e.g. ".py")

    Subclasses may optionally set PLUGIN_VERSION (default "0.1.0") and
    override __init__ to add language-specific parser instances *after*
    calling super().__init__().

    The default lifecycle records initialization state. Parsers that need
    eager warm-up (e.g. tree-sitter grammar loading) may extend it.
    """

    PLUGIN_NAME: ClassVar[str] = ""
    PLUGIN_VERSION: ClassVar[str] = "0.1.0"
    PLUGIN_DESCRIPTION: ClassVar[str] = ""
    SUPPORTED_LANGUAGES: ClassVar[set[str]] = set()
    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = set()

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name=self.PLUGIN_NAME,
                version=self.PLUGIN_VERSION,
                author="COGANT",
                description=self.PLUGIN_DESCRIPTION,
            )
        )
        self.supported_languages: set[str] = set(self.SUPPORTED_LANGUAGES)
        self.supported_extensions: set[str] = set(self.SUPPORTED_EXTENSIONS)
        self._initialized = False

    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the parser with a validated configuration mapping."""
        if not isinstance(config, dict):
            raise TypeError("parser configuration must be a dictionary")
        self._initialized = True

    def shutdown(self) -> None:
        """Release parser-owned state."""
        self._initialized = False
