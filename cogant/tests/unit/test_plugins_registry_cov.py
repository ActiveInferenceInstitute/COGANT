"""Behavioral tests for cogant.plugins.registry.PluginRegistry.

Exercises discovery, load, and lookup APIs using a real importlib.metadata
EntryPoint instance pointed at a throwaway Python module so no third-party
plugin is required.
"""

from __future__ import annotations

import importlib.metadata
import sys
import types

import pytest

from cogant.plugins.registry import PluginInfo, PluginRegistry

# --------------------------- fixtures ----------------------------------- #


def _install_fake_plugin_module(name: str = "_fake_cogant_plugin_mod") -> str:
    """Install a temporary in-process module with a loadable 'Plugin' attr."""
    mod = types.ModuleType(name)
    mod.Plugin = lambda: "plugin-instance"  # type: ignore[attr-defined]
    mod.Broken = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))  # type: ignore[attr-defined]
    sys.modules[name] = mod
    return name


def _fake_entry_point(name: str, value: str) -> importlib.metadata.EntryPoint:
    """Construct a real EntryPoint pointing at an in-memory module."""
    return importlib.metadata.EntryPoint(name=name, value=value, group="cogant.plugins")


def _patch_entry_points(monkeypatch, eps: list):
    """Replace PluginRegistry._get_entry_points with a deterministic stub."""
    monkeypatch.setattr(
        PluginRegistry,
        "_get_entry_points",
        staticmethod(lambda: list(eps)),
    )


# --------------------------- discover / list_plugins ------------------- #


def test_discover_empty_returns_empty_list(monkeypatch):
    """With no entry points, discover() returns an empty list."""
    _patch_entry_points(monkeypatch, [])
    reg = PluginRegistry()
    assert reg.discover() == []
    assert reg.list_plugins() == []


def test_discover_returns_plugin_info_for_each_entry_point(monkeypatch):
    """discover() returns one PluginInfo per entry point."""
    mod = _install_fake_plugin_module()
    ep = _fake_entry_point("fake", f"{mod}:Plugin")
    _patch_entry_points(monkeypatch, [ep])

    reg = PluginRegistry()
    infos = reg.discover()
    assert len(infos) == 1
    assert infos[0].name == "fake"
    assert infos[0].entry_point == f"{mod}:Plugin"
    assert infos[0].loaded is False
    assert infos[0].error is None


def test_list_plugins_triggers_discovery_when_cache_empty(monkeypatch):
    """list_plugins() triggers discover() automatically the first time."""
    mod = _install_fake_plugin_module()
    _patch_entry_points(monkeypatch, [_fake_entry_point("fake", f"{mod}:Plugin")])
    reg = PluginRegistry()
    assert reg.list_plugins() == ["fake"]


# --------------------------- load --------------------------------------- #


def test_load_unknown_plugin_returns_info_with_error(monkeypatch):
    """Loading a name that wasn't discovered returns an error PluginInfo."""
    _patch_entry_points(monkeypatch, [])
    reg = PluginRegistry()
    info = reg.load("nonexistent")
    assert info.loaded is False
    assert info.error is not None
    assert "No entry point" in info.error


def test_load_success_marks_info_loaded_and_caches_object(monkeypatch):
    """A successful load caches the loaded object and flips loaded=True."""
    mod = _install_fake_plugin_module()
    _patch_entry_points(monkeypatch, [_fake_entry_point("fake", f"{mod}:Plugin")])
    reg = PluginRegistry()
    info = reg.load("fake")
    assert info.loaded is True
    assert info.error is None
    obj = reg.get_loaded_object("fake")
    assert obj() == "plugin-instance"


def test_load_already_loaded_is_idempotent(monkeypatch):
    """Calling load() twice returns the same PluginInfo without re-loading."""
    mod = _install_fake_plugin_module()
    _patch_entry_points(monkeypatch, [_fake_entry_point("fake", f"{mod}:Plugin")])
    reg = PluginRegistry()
    first = reg.load("fake")
    second = reg.load("fake")
    assert first is second
    assert second.loaded is True


def test_load_failing_entry_point_captures_error(monkeypatch):
    """Import failures are captured as an error on the PluginInfo."""
    ep = _fake_entry_point("broken", "nonexistent_mod_xyz:Thing")
    _patch_entry_points(monkeypatch, [ep])
    reg = PluginRegistry()
    info = reg.load("broken")
    assert info.loaded is False
    assert info.error is not None
    # Either ModuleNotFoundError or ImportError prefix
    assert "Error" in info.error or "Import" in info.error


# --------------------------- get_plugin_info / get_loaded_object -------- #


def test_get_plugin_info_for_discovered_plugin(monkeypatch):
    """get_plugin_info returns the cached PluginInfo."""
    mod = _install_fake_plugin_module()
    _patch_entry_points(monkeypatch, [_fake_entry_point("fake", f"{mod}:Plugin")])
    reg = PluginRegistry()
    info = reg.get_plugin_info("fake")
    assert isinstance(info, PluginInfo)
    assert info.name == "fake"


def test_get_plugin_info_raises_for_unknown(monkeypatch):
    """get_plugin_info raises KeyError for an unknown plugin."""
    _patch_entry_points(monkeypatch, [])
    reg = PluginRegistry()
    with pytest.raises(KeyError):
        reg.get_plugin_info("ghost")


def test_get_loaded_object_raises_when_not_loaded(monkeypatch):
    """get_loaded_object raises KeyError if load() wasn't called yet."""
    mod = _install_fake_plugin_module()
    _patch_entry_points(monkeypatch, [_fake_entry_point("fake", f"{mod}:Plugin")])
    reg = PluginRegistry()
    reg.discover()
    with pytest.raises(KeyError):
        reg.get_loaded_object("fake")


# --------------------------- internal helpers --------------------------- #


def test_dist_version_returns_unknown_for_bare_entry_point(monkeypatch):
    """EntryPoints without a Distribution yield 'unknown'."""
    ep = _fake_entry_point("fake", "somewhere:Thing")
    # The raw EntryPoint has no .dist linked; _dist_version handles it
    assert PluginRegistry._dist_version(ep) == "unknown"


def test_find_entry_point_returns_none_for_missing(monkeypatch):
    """_find_entry_point returns None when the name doesn't match."""
    _patch_entry_points(monkeypatch, [])
    reg = PluginRegistry()
    assert reg._find_entry_point("nope") is None


def test_get_entry_points_returns_a_list():
    """The real _get_entry_points returns a list (may be empty)."""
    eps = PluginRegistry._get_entry_points()
    assert isinstance(eps, list)
