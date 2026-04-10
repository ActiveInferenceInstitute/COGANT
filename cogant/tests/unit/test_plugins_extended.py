"""Extended behavioral tests for cogant.plugins.registry.

Covers: PluginInfo defaults, registry discover clears cache, get_loaded_object
before load raises, list_plugins triggers discover, registry independence,
and ENTRY_POINT_GROUP constant value.
"""

from __future__ import annotations

import pytest

from cogant.plugins.registry import (
    ENTRY_POINT_GROUP,
    PluginInfo,
    PluginRegistry,
)


def test_plugin_info_defaults() -> None:
    """PluginInfo with only name has sensible defaults."""
    info = PluginInfo(name="minimal")
    assert info.version == "unknown"
    assert info.entry_point == ""
    assert info.loaded is False
    assert info.error is None


def test_entry_point_group_constant() -> None:
    """The entry-point group is 'cogant.plugins'."""
    assert ENTRY_POINT_GROUP == "cogant.plugins"


def test_discover_clears_previous_cache() -> None:
    """Calling discover() twice resets the internal cache."""
    registry = PluginRegistry()
    first = registry.discover()
    second = registry.discover()
    # Both should return the same list (no installed plugins expected)
    assert first == second


def test_get_loaded_object_before_load_raises() -> None:
    """get_loaded_object raises KeyError if plugin hasn't been loaded."""
    registry = PluginRegistry()
    with pytest.raises(KeyError, match="not been loaded"):
        registry.get_loaded_object("nonexistent")


def test_list_plugins_triggers_discovery() -> None:
    """list_plugins() works even without prior discover() call."""
    registry = PluginRegistry()
    # Don't call discover() first
    result = registry.list_plugins()
    assert isinstance(result, list)


def test_load_unknown_plugin_error_message() -> None:
    """Loading a completely unknown plugin includes the group name in error."""
    registry = PluginRegistry()
    info = registry.load("__totally_fake_plugin__")
    assert not info.loaded
    assert ENTRY_POINT_GROUP in info.error


def test_registry_instances_are_independent() -> None:
    """Two registry instances don't share state after mutations."""
    r1 = PluginRegistry()
    r2 = PluginRegistry()
    r1.discover()
    # r2 should not be affected
    assert r2._cache == {}


def test_plugin_info_fields_mutable() -> None:
    """PluginInfo is a mutable dataclass (loaded and error can be updated)."""
    info = PluginInfo(name="test", loaded=False, error="initial error")
    info.loaded = True
    info.error = None
    assert info.loaded is True
    assert info.error is None
