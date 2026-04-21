"""Tests for cogant.cache — content-addressed result cache."""

from __future__ import annotations

import time
from pathlib import Path

from cogant.cache import CacheEntry, CacheKey, CacheStore, get_cache_dir
from cogant.cache.hasher import hash_file, hash_repo

# ---------------------------------------------------------------------------
# get_cache_dir
# ---------------------------------------------------------------------------


def test_cache_dir_default() -> None:
    """get_cache_dir() returns a Path under the user's home directory."""
    cache_dir = get_cache_dir()
    assert isinstance(cache_dir, Path)
    assert cache_dir == Path.home() / ".cache" / "cogant"


# ---------------------------------------------------------------------------
# CacheStore — miss / put / get / invalidate / clear / stats
# ---------------------------------------------------------------------------


def test_cache_store_get_miss(tmp_path: Path) -> None:
    """A fresh store returns None for an unknown key."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/fake/repo", content_hash="abc123", cogant_version="0.2.0")
    assert store.get(key) is None


def test_cache_store_put_and_get(tmp_path: Path) -> None:
    """put() persists an entry that get() can retrieve."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/some/repo", content_hash="deadbeef01", cogant_version="0.2.0")
    stage_results = {"parse": {"files": 10}, "translate": {"nodes": 42}}

    entry = store.put(key, stage_results)
    assert isinstance(entry, CacheEntry)
    assert entry.key == key
    assert entry.stage_results == stage_results

    retrieved = store.get(key)
    assert retrieved is not None
    assert retrieved.stage_results == stage_results


def test_cache_entry_hit_flag(tmp_path: Path) -> None:
    """An entry returned by get() has hit=True."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/repo", content_hash="hit_flag_test", cogant_version="0.2.0")
    store.put(key, {"stage": "data"})

    retrieved = store.get(key)
    assert retrieved is not None
    assert retrieved.hit is True


def test_cache_store_invalidate(tmp_path: Path) -> None:
    """invalidate() removes the entry; subsequent get() returns None."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/repo", content_hash="to_invalidate", cogant_version="0.2.0")
    store.put(key, {"x": 1})

    assert store.invalidate(key) is True
    assert store.get(key) is None
    # Invalidating a missing key returns False.
    assert store.invalidate(key) is False


def test_cache_store_clear(tmp_path: Path) -> None:
    """clear() removes all entries and returns the count."""
    store = CacheStore(cache_dir=tmp_path)
    for i in range(5):
        key = CacheKey(repo_path="/repo", content_hash=f"hash_{i}", cogant_version="0.2.0")
        store.put(key, {"i": i})

    count = store.clear()
    assert count == 5

    # A second clear returns 0.
    assert store.clear() == 0


def test_cache_store_stats(tmp_path: Path) -> None:
    """stats() returns entries count and total size."""
    store = CacheStore(cache_dir=tmp_path)
    key = CacheKey(repo_path="/repo", content_hash="stats_test", cogant_version="0.2.0")
    store.put(key, {"data": list(range(100))})

    stats = store.stats()
    assert stats["entries"] == 1
    assert stats["total_size_bytes"] > 0


def test_cache_store_expiry(tmp_path: Path) -> None:
    """Expired entries are not returned by get()."""
    store = CacheStore(cache_dir=tmp_path, ttl_seconds=0)
    key = CacheKey(repo_path="/repo", content_hash="expired", cogant_version="0.2.0")
    store.put(key, {"old": True})
    # With ttl_seconds=0 the entry is immediately expired.
    time.sleep(0.01)
    assert store.get(key) is None


# ---------------------------------------------------------------------------
# Hasher
# ---------------------------------------------------------------------------


def test_hash_file_deterministic(tmp_path: Path) -> None:
    """Hashing the same content twice yields the same digest."""
    f = tmp_path / "hello.py"
    f.write_text("print('hello')\n")
    assert hash_file(f) == hash_file(f)
    # Different content gives a different hash.
    g = tmp_path / "world.py"
    g.write_text("print('world')\n")
    assert hash_file(f) != hash_file(g)


def test_hash_repo_ignores_pycache(tmp_path: Path) -> None:
    """hash_repo skips __pycache__ directories."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("x = 1\n")

    pycache = src / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-312.pyc").write_bytes(b"\x00" * 100)

    hash_with_pycache = hash_repo(tmp_path)

    # Remove __pycache__ and re-hash — should be identical.
    import shutil

    shutil.rmtree(pycache)
    hash_without_pycache = hash_repo(tmp_path)
    assert hash_with_pycache == hash_without_pycache


def test_hash_repo_respects_extensions(tmp_path: Path) -> None:
    """hash_repo only includes files matching requested extensions."""
    (tmp_path / "code.py").write_text("x = 1\n")
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")

    hash_py = hash_repo(tmp_path, extensions=[".py"])
    hash_csv = hash_repo(tmp_path, extensions=[".csv"])
    hash_both = hash_repo(tmp_path, extensions=[".py", ".csv"])

    assert hash_py != hash_csv
    assert hash_both != hash_py
    assert hash_both != hash_csv
