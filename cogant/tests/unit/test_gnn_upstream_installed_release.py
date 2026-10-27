"""Real installed-package identity checks, separate from bridge routing tests."""

from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from cogant.gnn.upstream_bridge import (
    MIN_UPSTREAM_MAJOR,
    UPSTREAM_DISTRIBUTION,
    is_upstream_gnn_available,
    upstream_version,
)


def test_bridge_ignores_a_retired_src_gnn_provider(tmp_path: Path) -> None:
    # Given: an importable legacy namespace that fails if the bridge selects it.
    legacy = tmp_path / "src"
    legacy.mkdir()
    (legacy / "__init__.py").write_text("", encoding="utf-8")
    (legacy / "gnn.py").write_text(
        "raise AssertionError('retired provider selected')\n", encoding="utf-8"
    )
    try:
        expected_version = importlib.metadata.version(UPSTREAM_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        expected_version = None
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)
    program = (
        "import json; from cogant.gnn.upstream_bridge import "
        "is_upstream_gnn_available, upstream_version; "
        "print(json.dumps({'available':is_upstream_gnn_available(),"
        "'version':upstream_version()}))"
    )
    # When: resolving the real COGANT bridge with the conflicting namespace present.
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    # Then: only the installed top-level provider controls availability and version.
    assert json.loads(result.stdout) == {
        "available": expected_version is not None,
        "version": expected_version,
    }


def test_installed_upstream_matches_locked_release_identity() -> None:
    # Given: the explicitly optional upstream distribution and committed lock.
    try:
        distribution = importlib.metadata.distribution(UPSTREAM_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("optional upstream gnn dependency not installed")
    root = Path(__file__).resolve().parents[2]
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked = next(
        package for package in lock["package"] if package["name"] == UPSTREAM_DISTRIBUTION
    )
    direct_url_text = distribution.read_text("direct_url.json")
    assert direct_url_text is not None
    direct_url = json.loads(direct_url_text)
    # When: resolving the public import through the guarded COGANT bridge.
    assert is_upstream_gnn_available(), "installed upstream failed the bridge availability gate"
    version = upstream_version()
    # Then: metadata, import version, installed source, and lock identify one release.
    assert version is not None
    assert int(version.split(".")[0]) >= MIN_UPSTREAM_MAJOR
    assert version == distribution.version == locked["version"]
    assert direct_url["vcs_info"]["commit_id"] == locked["source"]["git"].rsplit("#", 1)[1]
