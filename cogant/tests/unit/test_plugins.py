"""Tests for the entry-point based plugin registry."""

from __future__ import annotations

from cogant.plugins.registry import PluginInfo, PluginRegistry


# ---------------------------------------------------------------------- #
# 1. PluginInfo dataclass has the expected fields
# ---------------------------------------------------------------------- #


def test_plugin_info_dataclass() -> None:
    """PluginInfo exposes name, version, entry_point, loaded, error."""
    info = PluginInfo(
        name="test",
        version="0.1.0",
        entry_point="my_pkg.rule:MyRule",
        loaded=True,
        error=None,
    )
    assert info.name == "test"
    assert info.version == "0.1.0"
    assert info.entry_point == "my_pkg.rule:MyRule"
    assert info.loaded is True
    assert info.error is None


def test_plugin_info_with_error() -> None:
    """PluginInfo can carry an error string."""
    info = PluginInfo(
        name="broken",
        version="unknown",
        entry_point="nope:Nope",
        loaded=False,
        error="ImportError: No module named 'nope'",
    )
    assert info.loaded is False
    assert info.error is not None


# ---------------------------------------------------------------------- #
# 2. PluginRegistry.discover() always returns a list
# ---------------------------------------------------------------------- #


def test_registry_discover_returns_list() -> None:
    """discover() returns a list even when no plugins are installed."""
    registry = PluginRegistry()
    result = registry.discover()
    assert isinstance(result, list)


# ---------------------------------------------------------------------- #
# 3. PluginRegistry.load() handles missing plugins gracefully
# ---------------------------------------------------------------------- #


def test_registry_load_missing_returns_error() -> None:
    """Loading a non-existent plugin returns PluginInfo with error set."""
    registry = PluginRegistry()
    info = registry.load("__nonexistent_plugin_xyz__")
    assert isinstance(info, PluginInfo)
    assert info.loaded is False
    assert info.error is not None
    assert info.name == "__nonexistent_plugin_xyz__"


# ---------------------------------------------------------------------- #
# 4. PluginRegistry.list_plugins() returns a list of strings
# ---------------------------------------------------------------------- #


def test_registry_list_plugins_type() -> None:
    """list_plugins() returns a list of str."""
    registry = PluginRegistry()
    result = registry.list_plugins()
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, str)


# ---------------------------------------------------------------------- #
# 5. discover_plugins() convenience wrapper
# ---------------------------------------------------------------------- #


def test_discover_plugins_helper() -> None:
    """discover_plugins() is a module-level convenience wrapper."""
    from cogant.plugins import discover_plugins

    result = discover_plugins()
    assert isinstance(result, list)


# ---------------------------------------------------------------------- #
# 6. No singleton / global state
# ---------------------------------------------------------------------- #


def test_plugin_registry_singleton_pattern() -> None:
    """Multiple PluginRegistry instances are independent (no global state)."""
    r1 = PluginRegistry()
    r2 = PluginRegistry()
    assert r1 is not r2
    assert r1.list_plugins() == r2.list_plugins()


# ---------------------------------------------------------------------- #
# 7. get_plugin_info for unknown plugin
# ---------------------------------------------------------------------- #


def test_get_plugin_info_unknown() -> None:
    """get_plugin_info raises KeyError for unknown plugins."""
    import pytest

    registry = PluginRegistry()
    with pytest.raises(KeyError):
        registry.get_plugin_info("__does_not_exist__")
