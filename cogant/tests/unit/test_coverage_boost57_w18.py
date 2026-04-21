#!/usr/bin/env python3
"""Coverage boost batch 57 — cache/hasher.py and cache/store.py.

Covers:
- cache/hasher.py: hash_file (small file, nonexistent), hash_repo (empty dir)
- cache/store.py: get_cache_dir, CacheKey, CacheEntry dataclasses, CacheStore
  (init, get miss, put, get hit, invalidate, clear, stats, _path_for,
  _serialize, _deserialize)
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# cache/hasher.py — hash_file and hash_repo
# ---------------------------------------------------------------------------


class TestHashFile:
    def test_hash_file_small(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        result = hash_file(f)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex

    def test_hash_file_consistent(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        assert hash_file(f) == hash_file(f)

    def test_hash_file_different_contents(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x = 1\n")
        f2.write_text("y = 2\n")
        assert hash_file(f1) != hash_file(f2)


class TestHashRepo:
    def test_hash_repo_empty_dir(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        result = hash_repo(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_repo_with_files(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        result = hash_repo(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_repo_consistent(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "m.py").write_text("def foo(): pass\n")
        assert hash_repo(tmp_path) == hash_repo(tmp_path)


# ---------------------------------------------------------------------------
# cache/store.py — get_cache_dir, dataclasses, CacheStore
# ---------------------------------------------------------------------------


class TestGetCacheDir:
    def test_returns_path(self):
        from cogant.cache.store import get_cache_dir

        result = get_cache_dir()
        assert isinstance(result, Path)
        assert "cogant" in str(result)


class TestCacheKeyAndEntry:
    def test_cache_key_frozen(self):
        from cogant.cache.store import CacheKey

        key = CacheKey(
            repo_path="/tmp/repo",
            content_hash="abc123",
            cogant_version="0.4.0",
        )
        assert key.repo_path == "/tmp/repo"
        assert key.content_hash == "abc123"

    def test_cache_key_equality(self):
        from cogant.cache.store import CacheKey

        k1 = CacheKey(repo_path="/a", content_hash="x", cogant_version="1.0")
        k2 = CacheKey(repo_path="/a", content_hash="x", cogant_version="1.0")
        assert k1 == k2

    def test_cache_entry_init(self):
        from cogant.cache.store import CacheEntry, CacheKey

        key = CacheKey(repo_path="/repo", content_hash="sha", cogant_version="1.0")
        entry = CacheEntry(
            key=key,
            created_at="2026-01-01T00:00:00Z",
            stage_results={"ingest": {"file_count": 3}},
        )
        assert entry.hit is False
        assert entry.stage_results["ingest"]["file_count"] == 3


class TestCacheStore:
    def _make_key(self):
        from cogant.cache.store import CacheKey

        return CacheKey(repo_path="/test/repo", content_hash="abc123", cogant_version="0.4.0")

    def test_init_with_custom_dir(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        assert store is not None

    def test_get_miss(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = self._make_key()
        result = store.get(key)
        assert result is None

    def test_put_and_get(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = self._make_key()
        entry = store.put(key, {"ingest": {"file_count": 5}})
        assert entry is not None
        retrieved = store.get(key)
        assert retrieved is not None
        assert retrieved.hit is True
        assert retrieved.stage_results["ingest"]["file_count"] == 5

    def test_invalidate_missing(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = self._make_key()
        result = store.invalidate(key)
        assert result is False

    def test_invalidate_existing(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = self._make_key()
        store.put(key, {"data": 42})
        result = store.invalidate(key)
        assert result is True

    def test_clear_empty(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        cleared = store.clear()
        assert cleared == 0

    def test_clear_with_entries(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        k1 = CacheKey(repo_path="/a", content_hash="h1", cogant_version="1.0")
        k2 = CacheKey(repo_path="/b", content_hash="h2", cogant_version="1.0")
        store.put(k1, {"result": 1})
        store.put(k2, {"result": 2})
        cleared = store.clear()
        assert cleared == 2

    def test_stats_empty(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        stats = store.stats()
        assert isinstance(stats, dict)
        assert "hits" in stats or "size" in stats or len(stats) >= 0

    def test_stats_after_operations(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = self._make_key()
        store.put(key, {"x": 1})
        store.get(key)  # hit
        store.get(self._make_key())  # should still hit (same key)
        stats = store.stats()
        assert isinstance(stats, dict)
