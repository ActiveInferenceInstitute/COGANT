"""Tests for cogant.plugins.base.

The base plugin module defines abstract base classes for the plugin system.
No concrete plugin is shipped in-tree yet (PythonASTParser in cogant.static
does not extend LanguagePlugin), so these tests verify:

1. The ABCs are properly abstract (cannot be instantiated without overrides).
2. PluginMetadata is a real dataclass with the expected fields.
3. A minimal concrete subclass can be created and its lifecycle hooks work.
4. All nine specialized plugin ABCs in the module are importable and ABC-typed.

This guards the plugin-protocol surface so that when concrete plugins are
added they integrate against a stable contract.
"""

from __future__ import annotations

import pytest

from cogant.plugins import (
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


# ----------------------------- PluginMetadata ----------------------------- #


def test_plugin_metadata_required_fields():
    """PluginMetadata holds name and version, with author/description optional."""
    md = PluginMetadata(name="rust-lang", version="1.2.3")
    assert md.name == "rust-lang"
    assert md.version == "1.2.3"
    assert md.author == ""
    assert md.description == ""


def test_plugin_metadata_full_fields():
    """PluginMetadata accepts all metadata fields."""
    md = PluginMetadata(
        name="test-plugin",
        version="0.1.0",
        author="Test Author",
        description="A test plugin",
    )
    assert md.author == "Test Author"
    assert md.description == "A test plugin"


# --------------------------- Abstractness checks -------------------------- #


def test_plugin_base_cannot_be_instantiated():
    """The base Plugin class is abstract (initialize/shutdown required)."""
    md = PluginMetadata(name="x", version="1")
    with pytest.raises(TypeError):
        Plugin(md)  # type: ignore[abstract]


@pytest.mark.parametrize(
    "cls",
    [
        LanguagePlugin,
        TracePlugin,
        NormalizerPlugin,
        TranslationRulePlugin,
        StateSpacePlugin,
        ProcessModelPlugin,
        ExportPlugin,
        ValidationPlugin,
        VisualizationPlugin,
    ],
)
def test_specialized_plugin_classes_are_abstract(cls):
    """Every specialized plugin ABC refuses direct instantiation."""
    md = PluginMetadata(name="x", version="1")
    with pytest.raises(TypeError):
        cls(md)  # type: ignore[abstract]


def test_specialized_plugin_classes_inherit_from_plugin():
    """All specialized plugins subclass the base Plugin class."""
    for cls in (
        LanguagePlugin,
        TracePlugin,
        NormalizerPlugin,
        TranslationRulePlugin,
        StateSpacePlugin,
        ProcessModelPlugin,
        ExportPlugin,
        ValidationPlugin,
        VisualizationPlugin,
    ):
        assert issubclass(cls, Plugin), f"{cls.__name__} must subclass Plugin"


# ---------------------- Concrete subclass (smoke) ------------------------- #


class _FakeLanguagePlugin(LanguagePlugin):
    """Minimal LanguagePlugin implementation for lifecycle testing."""

    supported_languages = {"fake"}

    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.initialized = False
        self.shut_down = False
        self.last_config: dict | None = None

    def initialize(self, config):
        self.initialized = True
        self.last_config = config

    def shutdown(self):
        self.shut_down = True

    def parse(self, source_code: str):
        return {"body": source_code}

    def extract_symbols(self, ast):
        return [{"name": "sym1"}]

    def extract_types(self, ast):
        return {"int": 1}

    def resolve_imports(self, ast):
        return ["fake_dep"]


def test_concrete_language_plugin_lifecycle():
    """A concrete LanguagePlugin can initialize, run, and shut down."""
    md = PluginMetadata(name="fake", version="0.0.1", author="tests")
    plugin = _FakeLanguagePlugin(md)

    assert plugin.metadata is md
    assert plugin.initialized is False
    assert plugin.shut_down is False

    plugin.initialize({"verbosity": 2})
    assert plugin.initialized is True
    assert plugin.last_config == {"verbosity": 2}

    assert plugin.parse("x = 1") == {"body": "x = 1"}
    assert plugin.extract_symbols({}) == [{"name": "sym1"}]
    assert plugin.extract_types({}) == {"int": 1}
    assert plugin.resolve_imports({}) == ["fake_dep"]

    plugin.shutdown()
    assert plugin.shut_down is True


def test_language_plugin_supported_languages_class_attr():
    """supported_languages is a class-level set that concrete plugins override."""
    assert isinstance(_FakeLanguagePlugin.supported_languages, set)
    assert "fake" in _FakeLanguagePlugin.supported_languages
    # Base class default is an empty set.
    assert LanguagePlugin.supported_languages == set()


def test_language_plugin_missing_abstract_method_stays_abstract():
    """Partially-implemented subclasses are still abstract."""

    class _Incomplete(LanguagePlugin):
        def initialize(self, config):
            pass

        def shutdown(self):
            pass

        def parse(self, source_code):
            return {}

        # Intentionally missing extract_symbols / extract_types / resolve_imports.

    md = PluginMetadata(name="x", version="1")
    with pytest.raises(TypeError):
        _Incomplete(md)  # type: ignore[abstract]
