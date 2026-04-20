#!/usr/bin/env python3
"""Tests for cache/hasher.py (deterministic repo digests)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.cache.hasher import hash_file, hash_repo

pytestmark = pytest.mark.unit


def test_hash_file_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "sample.txt"
    p.write_bytes(b"alpha")
    d = hash_file(p)
    assert len(d) == 64
    assert d == hash_file(p)


def test_hash_repo_skips_ignored_and_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    sub = tmp_path / "__pycache__"
    sub.mkdir()
    (sub / "bad.py").write_text("ignored\n")
    (tmp_path / "readme.md").write_text("no\n")

    d1 = hash_repo(tmp_path)
    (tmp_path / "b.py").write_text("y = 2\n")
    d2 = hash_repo(tmp_path)
    assert d1 != d2

    assert hash_repo(tmp_path, extensions=[".md"]) != d1
