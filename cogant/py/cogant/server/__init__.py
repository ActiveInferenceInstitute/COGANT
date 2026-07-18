"""COGANT's local-safe FastAPI server package.

The server defaults to loopback, confines repository access to a configured
workspace, and requires explicit authentication for non-loopback binding.
Use :func:`create_app_from_config` with the canonical project configuration
to apply request, archive, and rate-limit settings consistently.
"""

from __future__ import annotations

from cogant.server.app import create_app, create_app_from_config, run_server

__all__ = ["create_app", "create_app_from_config", "run_server"]
