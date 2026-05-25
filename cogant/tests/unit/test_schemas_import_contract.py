"""Targeted unit tests for: cogant.schemas.__init__.

Targets the only uncovered branch in the schemas package init: the
``ImportError`` fallback (lines 104-120) and the corresponding
``__all__`` else block (line 209).

The fallback path runs only when at least one of the extended Pydantic
schema submodules fails to import. Real environments never hit this in
tests, so we drive the path by:

1. Saving the live ``cogant.schemas`` module + every submodule
2. Inserting a ``sys.meta_path`` finder that raises ``ImportError`` for
   ``cogant.schemas.base`` (the first import inside the try-block)
3. Removing ``cogant.schemas`` from ``sys.modules`` and re-importing it
4. Asserting the fallback ``__all__`` shape matches the spec
5. Restoring the original module so other tests stay clean

This is a real, deterministic test — no mocks, no monkeypatch on the
module under test, just a real ``importlib`` finder.
"""

from __future__ import annotations

import importlib
import sys
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from typing import Any


class _ForceImportError(MetaPathFinder):
    """Meta-path finder that raises ImportError for selected dotted names.

    The Python import machinery calls every meta-path finder in order
    when ``sys.modules`` does not already contain the requested module.
    This finder returns a synthetic ModuleSpec whose loader raises
    ``ImportError`` on every load attempt — which is exactly what the
    fallback branch in ``cogant.schemas`` is written to handle.
    """

    def __init__(self, target_names: set[str]) -> None:
        self.target_names = target_names

    def find_spec(self, fullname: str, path: Any | None = None, target: Any | None = None) -> Any:  # noqa: D401, ARG002
        if fullname in self.target_names:
            return ModuleSpec(fullname, _RaisingLoader())
        return None


class _RaisingLoader:
    """Loader half of the ``_ForceImportError`` mechanism."""

    def create_module(self, spec: Any) -> Any:  # noqa: ARG002
        return None

    def exec_module(self, module: Any) -> None:  # noqa: ARG002
        raise ImportError("forced ImportError for fallback-path coverage")


def _purge_schemas_from_sys_modules() -> dict[str, Any]:
    """Remove every ``cogant.schemas*`` module from sys.modules; return them."""
    saved = {k: v for k, v in list(sys.modules.items()) if k.startswith("cogant.schemas")}
    for k in saved:
        del sys.modules[k]
    return saved


def _restore(saved: dict[str, Any]) -> None:
    """Restore the original ``cogant.schemas*`` modules.

    We must also force a re-import of ``cogant.schemas`` from disk so
    the live module's ``_extended_available`` flag reflects the real
    environment again (the fallback branch sets it to False; without a
    fresh exec downstream code would see the wrong value).
    """
    # Drop any placeholder objects we created during the test
    for k in [k for k in list(sys.modules.keys()) if k.startswith("cogant.schemas")]:
        del sys.modules[k]
    # Restore the original module objects first so the parent package
    # has the right children attached.
    for k, v in saved.items():
        sys.modules[k] = v
    # Force a fresh execution of cogant.schemas/__init__.py so the
    # extended-import path runs to completion (sets
    # ``_extended_available = True``). We keep the originals saved in
    # case the reload fails so the next test can still find them.
    if "cogant.schemas" in sys.modules:
        del sys.modules["cogant.schemas"]
    importlib.import_module("cogant.schemas")


def test_fallback_path_when_base_import_fails() -> None:
    """Forcing ``cogant.schemas.base`` ImportError exercises the fallback.

    After the forced reload, ``_extended_available`` is False and
    ``__all__`` matches the basic-implementation list (lines 209-220).
    """
    saved = _purge_schemas_from_sys_modules()
    finder = _ForceImportError({"cogant.schemas.base"})
    sys.meta_path.insert(0, finder)
    try:
        # Re-import cogant.schemas. The try-block's first ``from .base
        # import ...`` will raise our forced ImportError, sending the
        # module into the except branch (lines 104-120).
        schemas = importlib.import_module("cogant.schemas")
        assert schemas._extended_available is False
        # Fallback __all__ matches the spec exactly
        assert set(schemas.__all__) == {
            "Node",
            "Edge",
            "NodeKind",
            "EdgeKind",
            "ProgramGraph",
            "GraphMetadata",
            "SemanticMapping",
            "MappingKind",
            "ConfidenceTier",
            "ProvenanceRecord",
        }
        # The fallback names must actually be present on the module
        for name in schemas.__all__:
            assert hasattr(schemas, name), f"missing fallback re-export: {name}"
    finally:
        # Critical: take the finder back out before restoring so any
        # follow-up imports use the real loader.
        sys.meta_path.remove(finder)
        _restore(saved)


def test_schemas_exports_when_extended_available() -> None:
    """In the normal environment ``_extended_available`` is True.

    This second test re-confirms the live behaviour after the fallback
    test has cleaned up. It also covers line 209-onwards (the
    extended-mode ``__all__`` definition) by name lookup.
    """
    import cogant.schemas as schemas

    # Live environment must have the extended Pydantic schemas available
    assert schemas._extended_available is True
    # Spot-check a few extended-only names
    for name in (
        "CogantBaseModel",
        "GNNExportBundle",
        "StateSpaceModel",
        "ValidationReport",
    ):
        assert name in schemas.__all__
        assert hasattr(schemas, name)
