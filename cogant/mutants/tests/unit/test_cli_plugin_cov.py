"""Behavioral tests for cogant.cli.plugin CLI commands.

Uses Typer CliRunner and a real in-process fake plugin module so no
third-party plugin is needed.  No mocks — only real importlib.metadata
EntryPoint instances backed by in-memory modules.
"""

from __future__ import annotations

import importlib.metadata
import sys
import types

from typer.testing import CliRunner

from cogant.cli.plugin import plugin_app
from cogant.plugins.registry import PluginRegistry

runner = CliRunner()


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _install_fake_module(mod_name: str = "_fake_plugin_mod_cli") -> str:
    """Install a temporary in-process module that exposes a Plugin class."""
    mod = types.ModuleType(mod_name)
    mod.Plugin = type("Plugin", (), {"version": "1.2.3"})  # type: ignore[attr-defined]
    sys.modules[mod_name] = mod
    return mod_name


def _make_ep(name: str, value: str) -> importlib.metadata.EntryPoint:
    return importlib.metadata.EntryPoint(
        name=name, value=value, group="cogant.plugins"
    )


def _inject_eps(monkeypatch, eps: list) -> None:
    """Replace PluginRegistry._get_entry_points for the duration of a test."""
    monkeypatch.setattr(
        PluginRegistry,
        "_get_entry_points",
        staticmethod(lambda: eps),
    )


# ------------------------------------------------------------------ #
# plugin list tests
# ------------------------------------------------------------------ #


def test_plugin_list_no_plugins(monkeypatch) -> None:
    """``cogant plugin list`` prints a 'No plugins' message when none found."""
    _inject_eps(monkeypatch, [])
    result = runner.invoke(plugin_app, ["list"])
    assert result.exit_code == 0
    assert "No plugins" in result.output


def test_plugin_list_shows_discovered_plugin(monkeypatch) -> None:
    """``cogant plugin list`` renders a table row for a discovered plugin."""
    mod_name = _install_fake_module()
    ep = _make_ep("fake_plugin", f"{mod_name}:Plugin")
    _inject_eps(monkeypatch, [ep])

    result = runner.invoke(plugin_app, ["list"])
    assert result.exit_code == 0
    # Plugin name should appear somewhere in output
    assert "fake_plugin" in result.output


def test_plugin_list_shows_discovered_status(monkeypatch) -> None:
    """``cogant plugin list`` shows 'discovered' status for a valid plugin."""
    mod_name = _install_fake_module("_fake_good_plugin")
    ep = _make_ep("good_plugin", f"{mod_name}:Plugin")
    _inject_eps(monkeypatch, [ep])

    result = runner.invoke(plugin_app, ["list"])
    assert result.exit_code == 0
    # Status column should show 'discovered' for a plugin with no error
    assert "discovered" in result.output


# ------------------------------------------------------------------ #
# plugin info tests
# ------------------------------------------------------------------ #


def test_plugin_info_not_found_exits_1(monkeypatch) -> None:
    """``cogant plugin info`` exits with code 1 when plugin doesn't exist."""
    _inject_eps(monkeypatch, [])
    result = runner.invoke(plugin_app, ["info", "nonexistent_plugin"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_plugin_info_shows_name_and_version(monkeypatch) -> None:
    """``cogant plugin info`` prints name and entry point for a known plugin."""
    mod_name = _install_fake_module("_fake_info_plugin")
    ep = _make_ep("info_plugin", f"{mod_name}:Plugin")
    _inject_eps(monkeypatch, [ep])

    result = runner.invoke(plugin_app, ["info", "info_plugin"])
    assert result.exit_code == 0
    assert "info_plugin" in result.output
    assert mod_name in result.output


def test_plugin_info_shows_loaded_true(monkeypatch) -> None:
    """``cogant plugin info`` shows Loaded: True for a successfully loaded plugin."""
    mod_name = _install_fake_module("_fake_loaded_plugin")
    ep = _make_ep("loaded_plugin", f"{mod_name}:Plugin")
    _inject_eps(monkeypatch, [ep])

    result = runner.invoke(plugin_app, ["info", "loaded_plugin"])
    assert result.exit_code == 0
    assert "True" in result.output
