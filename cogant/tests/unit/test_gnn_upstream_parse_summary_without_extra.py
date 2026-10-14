"""Parsing ``model.gnn.md`` without the optional upstream extra stays quiet.

``cogant[upstream]`` is optional and upstream validation is off by default,
yet the validate stage always asks for an upstream parse summary. A missing
extra is an expected configuration: ``parse_upstream_model_gnn_md`` must
return an ``available: False`` summary without logging a warning with a
chained traceback. Genuine upstream parse failures still warn.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

import cogant.gnn.upstream_bridge as bridge

pytestmark = pytest.mark.unit


def _package(tmp_path: Path) -> Path:
    (tmp_path / "model.gnn.md").write_text("## GNNSection\nm\n", encoding="utf-8")
    return tmp_path


def test_missing_extra_returns_unavailable_summary_without_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def _not_installed() -> Any:
        raise ImportError("generalized-notation-notation (import package `gnn`) is not installed.")

    monkeypatch.setattr(bridge, "_require_upstream_gnn", _not_installed)
    caplog.set_level(logging.DEBUG, logger=bridge.__name__)

    out = bridge.parse_upstream_model_gnn_md(_package(tmp_path))

    assert out["available"] is False
    assert "not installed" in out["error"]
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


def test_upstream_parse_failure_still_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class _Upstream:
        @staticmethod
        def parse_gnn_file(path: Path) -> Any:
            raise ValueError(f"cannot parse {path.name}")

    monkeypatch.setattr(bridge, "_require_upstream_gnn", lambda: _Upstream)
    caplog.set_level(logging.DEBUG, logger=bridge.__name__)

    out = bridge.parse_upstream_model_gnn_md(_package(tmp_path))

    assert out["error"] == "cannot parse model.gnn.md"
    assert "available" not in out
    assert any(r.levelno == logging.WARNING for r in caplog.records)
