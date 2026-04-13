"""Example plugin rule that classifies nodes as 'hello'."""

from __future__ import annotations

from typing import Any, Dict


class HelloRule:
    """A trivial classification rule for demonstration purposes.

    When registered as a COGANT plugin, it can be discovered and loaded
    by the :class:`cogant.plugins.registry.PluginRegistry`.
    """

    name = "hello"
    version = "0.1.0"

    def classify(self, node: Dict[str, Any]) -> str:
        """Classify a graph node -- always returns ``'hello'``."""
        return "hello"
