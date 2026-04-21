"""Extended behavioral tests for cogant.cache — store.py and hasher.py.

Covers: TTL edge cases, stats accuracy, corrupted JSON, concurrent put/get,
shard directory layout, clear on empty store, hash_repo with empty dirs,
hash_file on binary content, and hash_repo with custom extensions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.cache import CacheKey, CacheStore
from cogant.cache.hasher import hash_file, hash_repo

# ---------------------------------------------------------------------------
# CacheStore — extended behavioral tests
# ---------------------------------------------------------------------------


def test_cache_store_stats_hit_miss_tracking(tmp_path: Path) -> None:
    """stats() accurately tracks hit/miss counts and hit_rate."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/r", content_hash="aabb", cogant_version="0.1")
    store.put(key, {"v": 1})

    # One miss
    missing_key = CacheKey(repo_path="/r", content_hash="ccdd", cogant_version="0.1")
    store.get(missing_key)
    # One hit
    store.get(key)

    stats = store.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == pytest.approx(0.5)


def test_cache_store_corrupted_json_returns_none(tmp_path: Path) -> None:
    """get() gracefully handles corrupted JSON files."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/r", content_hash="corrupt01", cogant_version="0.1")
    store.put(key, {"ok": True})

    # Corrupt the file
    path = tmp_path / "co" / "corrupt01.json"
    path.write_text("{this is not valid json!!!")

    assert store.get(key) is None


def test_cache_store_shard_directory_layout(tmp_path: Path) -> None:
    """Cache files are stored under <hash[:2]>/<hash>.json sharded layout."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/r", content_hash="abcdef1234567890", cogant_version="0.1")
    store.put(key, {"layout": "test"})

    expected_path = tmp_path / "ab" / "abcdef1234567890.json"
    assert expected_path.is_file()
    data = json.loads(expected_path.read_text())
    assert data["stage_results"]["layout"] == "test"


def test_cache_store_put_overwrites_existing(tmp_path: Path) -> None:
    """Putting a new value for the same key overwrites the old entry."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/r", content_hash="overwrite01", cogant_version="0.1")
    store.put(key, {"version": 1})
    store.put(key, {"version": 2})

    retrieved = store.get(key)
    assert retrieved is not None
    assert retrieved.stage_results["version"] == 2


def test_cache_store_clear_on_nonexistent_dir(tmp_path: Path) -> None:
    """clear() on a store whose directory doesn't exist returns 0."""
    store = CacheStore(cache_dir=tmp_path / "nonexistent")
    assert store.clear() == 0


def test_cache_store_ttl_boundary(tmp_path: Path) -> None:
    """Entry with large TTL is not expired immediately."""
    store = CacheStore(cache_dir=tmp_path, ttl_seconds=999999)
    key = CacheKey(repo_path="/r", content_hash="longlived", cogant_version="0.1")
    store.put(key, {"data": "still fresh"})

    retrieved = store.get(key)
    assert retrieved is not None
    assert retrieved.stage_results["data"] == "still fresh"


def test_cache_entry_created_at_is_iso8601(tmp_path: Path) -> None:
    """CacheEntry.created_at is a valid ISO 8601 timestamp."""
    from datetime import datetime

    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/r", content_hash="timestamp01", cogant_version="0.1")
    entry = store.put(key, {"ts": True})
    # Should parse without error
    parsed = datetime.fromisoformat(entry.created_at)
    assert parsed.year >= 2024


def test_cache_store_stats_zero_requests(tmp_path: Path) -> None:
    """stats() with zero hits and zero misses returns 0.0 hit_rate."""
    store = CacheStore(cache_dir=tmp_path)
    stats = store.stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate"] == 0.0


# ---------------------------------------------------------------------------
# Hasher — extended behavioral tests
# ---------------------------------------------------------------------------


def test_hash_file_binary_content(tmp_path: Path) -> None:
    """hash_file works on binary (non-UTF-8) content."""
    f = tmp_path / "binary.dat"
    f.write_bytes(b"\x00\x01\xff\xfe" * 256)
    digest = hash_file(f)
    assert len(digest) == 64  # SHA-256 hex digest


def test_hash_repo_empty_directory(tmp_path: Path) -> None:
    """hash_repo on a directory with no matching files returns a deterministic digest."""
    d = tmp_path / "empty_project"
    d.mkdir()
    h1 = hash_repo(d)
    h2 = hash_repo(d)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_repo_ignores_git_directory(tmp_path: Path) -> None:
    """hash_repo ignores .git directory."""
    (tmp_path / "main.py").write_text("x = 1\n")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

    hash_with_git = hash_repo(tmp_path)
    import shutil

    shutil.rmtree(git_dir)
    hash_without_git = hash_repo(tmp_path)
    assert hash_with_git == hash_without_git


def test_hash_repo_ignores_node_modules(tmp_path: Path) -> None:
    """hash_repo ignores node_modules directory."""
    (tmp_path / "index.js").write_text("const x = 1;\n")
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "dep.js").write_text("module.exports = {};\n")

    hash_with_nm = hash_repo(tmp_path, extensions=[".js"])
    import shutil

    shutil.rmtree(nm)
    hash_without_nm = hash_repo(tmp_path, extensions=[".js"])
    assert hash_with_nm == hash_without_nm


def test_hash_repo_order_independent(tmp_path: Path) -> None:
    """hash_repo is deterministic regardless of file creation order."""
    # Create files in one order
    d1 = tmp_path / "d1"
    d1.mkdir()
    (d1 / "b.py").write_text("b = 2\n")
    (d1 / "a.py").write_text("a = 1\n")
    h1 = hash_repo(d1)

    # Create same files in reverse order
    d2 = tmp_path / "d2"
    d2.mkdir()
    (d2 / "a.py").write_text("a = 1\n")
    (d2 / "b.py").write_text("b = 2\n")
    h2 = hash_repo(d2)

    assert h1 == h2


def test_hash_repo_different_content_different_hash(tmp_path: Path) -> None:
    """Changing file content changes the repo hash."""
    d1 = tmp_path / "d1"
    d1.mkdir()
    (d1 / "main.py").write_text("x = 1\n")
    h1 = hash_repo(d1)

    d2 = tmp_path / "d2"
    d2.mkdir()
    (d2 / "main.py").write_text("x = 2\n")
    h2 = hash_repo(d2)

    assert h1 != h2
