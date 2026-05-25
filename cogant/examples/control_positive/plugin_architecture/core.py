"""Plugin registry fixture for COGANT extension-point analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Plugin(Protocol):
    name: str

    def handle(self, payload: str) -> str:
        """Transform a payload."""


@dataclass
class UppercasePlugin:
    name: str = "uppercase"

    def handle(self, payload: str) -> str:
        return payload.upper()


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.name] = plugin

    def dispatch(self, name: str, payload: str) -> str:
        if name not in self._plugins:
            raise KeyError(name)
        return self._plugins[name].handle(payload)


def build_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(UppercasePlugin())
    return registry
