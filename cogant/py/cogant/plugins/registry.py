"""Entry-point based plugin registry for COGANT.

Discovers and manages plugins registered under the ``cogant.plugins``
entry-point group.  Uses only :mod:`importlib.metadata` from the
standard library -- no extra dependencies.

Example ``pyproject.toml`` for a third-party plugin::

    [project.entry-points."cogant.plugins"]
    my_rule = "my_package.rule:MyRule"
"""

from __future__ import annotations

import importlib.metadata
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "cogant.plugins"


@dataclass
class PluginInfo:
    """Metadata about a discovered plugin.

    Attributes:
        name: Entry-point name (e.g. ``my_rule``).
        version: Version of the distribution that provides the plugin,
            or ``"unknown"`` when it cannot be determined.
        entry_point: The raw entry-point value (``module:attr``).
        loaded: Whether the plugin object has been successfully loaded.
        error: Human-readable error string if loading failed, else *None*.
    """

    name: str
    version: str = "unknown"
    entry_point: str = ""
    loaded: bool = False
    error: str | None = None


class PluginRegistry:
    """Discovers and manages COGANT plugins via entry points.

    Each instance maintains its own cache so that multiple registries
    can coexist without sharing global state.
    """

    def __init__(self) -> None:
        self._cache: dict[str, PluginInfo] = {}
        self._loaded_objects: dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def discover(self) -> list[PluginInfo]:
        """Discover all installed plugins under *cogant.plugins*.

        Returns an empty list when no plugins are registered -- never
        raises.
        """
        self._cache.clear()
        self._loaded_objects.clear()
        infos: list[PluginInfo] = []

        eps = self._get_entry_points()
        for ep in eps:
            version = self._dist_version(ep)
            info = PluginInfo(
                name=ep.name,
                version=version,
                entry_point=ep.value,
                loaded=False,
                error=None,
            )
            self._cache[ep.name] = info
            infos.append(info)
            logger.debug("Discovered plugin: %s (%s)", ep.name, ep.value)

        return infos

    def load(self, name: str) -> PluginInfo:
        """Load a single plugin by *name*.

        If the plugin is not found among the registered entry points, or
        if importing it fails, the returned :class:`PluginInfo` will
        have ``loaded=False`` and ``error`` set.
        """
        # Make sure we have a fresh discovery
        if not self._cache:
            self.discover()

        # Check if the plugin was discovered
        if name not in self._cache:
            return PluginInfo(
                name=name,
                version="unknown",
                entry_point="",
                loaded=False,
                error=f"No entry point named '{name}' in group '{ENTRY_POINT_GROUP}'",
            )

        info = self._cache[name]

        # Already loaded?
        if info.loaded:
            return info

        # Attempt to load
        ep = self._find_entry_point(name)
        if ep is None:
            info.loaded = False
            info.error = f"Entry point '{name}' disappeared between discover and load"
            return info

        try:
            obj = ep.load()
            self._loaded_objects[name] = obj
            info.loaded = True
            info.error = None
            logger.info("Loaded plugin: %s -> %s", name, obj)
        except Exception as exc:  # noqa: BLE001 — intentionally broad
            info.loaded = False
            info.error = f"{type(exc).__name__}: {exc}"
            logger.warning("Failed to load plugin '%s': %s", name, exc)

        return info

    def list_plugins(self) -> list[str]:
        """Return names of all discovered plugins.

        Triggers discovery if it hasn't happened yet.
        """
        if not self._cache:
            self.discover()
        return list(self._cache.keys())

    def get_plugin_info(self, name: str) -> PluginInfo:
        """Return :class:`PluginInfo` for *name*.

        Raises :class:`KeyError` if the plugin was not discovered.
        """
        if not self._cache:
            self.discover()
        try:
            return self._cache[name]
        except KeyError:
            raise KeyError(
                f"Plugin '{name}' not found. "
                f"Discovered: {list(self._cache.keys())}"
            ) from None

    def get_loaded_object(self, name: str) -> Any:
        """Return the loaded Python object for *name*.

        Raises :class:`KeyError` if the plugin has not been loaded.
        """
        try:
            return self._loaded_objects[name]
        except KeyError:
            raise KeyError(
                f"Plugin '{name}' has not been loaded yet. Call load() first."
            ) from None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_entry_points() -> list[importlib.metadata.EntryPoint]:
        """Retrieve entry points, compatible with Python 3.9+."""
        try:
            # Python 3.12+ and some back-ports accept group=
            eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
        except TypeError:
            # Older Python: returns a dict keyed by group
            all_eps = importlib.metadata.entry_points()
            eps = all_eps.get(ENTRY_POINT_GROUP, [])  # type: ignore[union-attr,unused-ignore]
        return list(eps)

    @staticmethod
    def _dist_version(ep: importlib.metadata.EntryPoint) -> str:
        """Best-effort version lookup for the distribution providing *ep*."""
        try:
            dist = ep.dist
            if dist is not None:
                return dist.metadata["Version"] or "unknown"
        except Exception:  # noqa: BLE001
            pass
        return "unknown"

    def _find_entry_point(
        self, name: str
    ) -> importlib.metadata.EntryPoint | None:
        """Find a specific entry point by name."""
        for ep in self._get_entry_points():
            if ep.name == name:
                return ep
        return None
