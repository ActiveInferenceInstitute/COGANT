#!/usr/bin/env python3
"""Targeted branch tests — config modules, cache/hasher, cache/store.

Covers:
- config/gnn.py: GNNConfig defaults and field validation
- config/graph.py: GraphConfig defaults and field validation
- config/reverse.py: ReverseConfig defaults and field validation
- config/ingest.py: IngestConfig defaults and field validation
- config/translate.py: TranslateConfig defaults and field validation
- config/statespace.py: StatespaceConfig defaults and field validation
- cache/hasher.py: hash_file, hash_repo
- cache/store.py: CacheKey, CacheEntry, CacheStore full API
"""

import dataclasses
from pathlib import Path

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# config/gnn.py
# ---------------------------------------------------------------------------


class TestGNNConfig:
    def test_default_include_metadata(self):
        from cogant.config.gnn import GNNConfig

        cfg = GNNConfig()
        assert cfg.include_metadata is True

    def test_default_include_connections(self):
        from cogant.config.gnn import GNNConfig

        cfg = GNNConfig()
        assert cfg.include_connections is True

    def test_default_include_matrices(self):
        from cogant.config.gnn import GNNConfig

        cfg = GNNConfig()
        assert cfg.include_matrices is True

    def test_default_matrix_format(self):
        from cogant.config.gnn import GNNConfig

        cfg = GNNConfig()
        assert cfg.matrix_format == "dense"

    def test_sparse_matrix_format(self):
        from cogant.config.gnn import GNNConfig

        cfg = GNNConfig(matrix_format="sparse")
        assert cfg.matrix_format == "sparse"

    def test_frozen_config(self):
        from cogant.config.gnn import GNNConfig

        cfg = GNNConfig()
        with pytest.raises(ValidationError):
            cfg.include_metadata = False  # frozen

    def test_disable_connections(self):
        from cogant.config.gnn import GNNConfig

        cfg = GNNConfig(include_connections=False)
        assert cfg.include_connections is False

    def test_disable_matrices(self):
        from cogant.config.gnn import GNNConfig

        cfg = GNNConfig(include_matrices=False)
        assert cfg.include_matrices is False


# ---------------------------------------------------------------------------
# config/graph.py
# ---------------------------------------------------------------------------


class TestGraphConfig:
    def test_default_max_nodes(self):
        from cogant.config.graph import GraphConfig

        cfg = GraphConfig()
        assert cfg.max_nodes == 10_000

    def test_default_max_edges(self):
        from cogant.config.graph import GraphConfig

        cfg = GraphConfig()
        assert cfg.max_edges == 50_000

    def test_default_prune_isolated(self):
        from cogant.config.graph import GraphConfig

        cfg = GraphConfig()
        assert cfg.prune_isolated is True

    def test_default_include_builtins(self):
        from cogant.config.graph import GraphConfig

        cfg = GraphConfig()
        assert cfg.include_builtins is False

    def test_custom_max_nodes(self):
        from cogant.config.graph import GraphConfig

        cfg = GraphConfig(max_nodes=500)
        assert cfg.max_nodes == 500

    def test_frozen_config(self):
        from cogant.config.graph import GraphConfig

        cfg = GraphConfig()
        with pytest.raises(ValidationError):
            cfg.max_nodes = 100

    def test_include_builtins_enabled(self):
        from cogant.config.graph import GraphConfig

        cfg = GraphConfig(include_builtins=True)
        assert cfg.include_builtins is True

    def test_prune_isolated_disabled(self):
        from cogant.config.graph import GraphConfig

        cfg = GraphConfig(prune_isolated=False)
        assert cfg.prune_isolated is False


# ---------------------------------------------------------------------------
# config/reverse.py
# ---------------------------------------------------------------------------


class TestReverseConfig:
    def test_default_synthesis_strategy(self):
        from cogant.config.reverse import ReverseConfig

        cfg = ReverseConfig()
        assert cfg.synthesis_strategy == "minimal"

    def test_default_include_tests(self):
        from cogant.config.reverse import ReverseConfig

        cfg = ReverseConfig()
        assert cfg.include_tests is False

    def test_default_role_threshold(self):
        from cogant.config.reverse import ReverseConfig

        cfg = ReverseConfig()
        assert cfg.role_threshold == 0.7

    def test_full_strategy(self):
        from cogant.config.reverse import ReverseConfig

        cfg = ReverseConfig(synthesis_strategy="full")
        assert cfg.synthesis_strategy == "full"

    def test_include_tests_enabled(self):
        from cogant.config.reverse import ReverseConfig

        cfg = ReverseConfig(include_tests=True)
        assert cfg.include_tests is True

    def test_custom_role_threshold(self):
        from cogant.config.reverse import ReverseConfig

        cfg = ReverseConfig(role_threshold=0.9)
        assert cfg.role_threshold == 0.9

    def test_frozen_config(self):
        from cogant.config.reverse import ReverseConfig

        cfg = ReverseConfig()
        with pytest.raises(ValidationError):
            cfg.role_threshold = 0.5


# ---------------------------------------------------------------------------
# config/ingest.py
# ---------------------------------------------------------------------------


class TestIngestConfig:
    def test_default_max_file_size_kb(self):
        from cogant.config.ingest import IngestConfig

        cfg = IngestConfig()
        assert cfg.max_file_size_kb == 512

    def test_default_include_extensions(self):
        from cogant.config.ingest import IngestConfig

        cfg = IngestConfig()
        assert ".py" in cfg.include_extensions

    def test_default_exclude_patterns(self):
        from cogant.config.ingest import IngestConfig

        cfg = IngestConfig()
        assert "__pycache__" in cfg.exclude_patterns

    def test_default_follow_symlinks(self):
        from cogant.config.ingest import IngestConfig

        cfg = IngestConfig()
        assert cfg.follow_symlinks is False

    def test_default_encoding(self):
        from cogant.config.ingest import IngestConfig

        cfg = IngestConfig()
        assert cfg.encoding == "utf-8"

    def test_custom_extensions(self):
        from cogant.config.ingest import IngestConfig

        cfg = IngestConfig(include_extensions=[".py"])
        assert cfg.include_extensions == [".py"]

    def test_follow_symlinks_enabled(self):
        from cogant.config.ingest import IngestConfig

        cfg = IngestConfig(follow_symlinks=True)
        assert cfg.follow_symlinks is True

    def test_frozen_config(self):
        from cogant.config.ingest import IngestConfig

        cfg = IngestConfig()
        with pytest.raises(ValidationError):
            cfg.encoding = "latin-1"


# ---------------------------------------------------------------------------
# config/translate.py
# ---------------------------------------------------------------------------


class TestTranslateConfig:
    def test_default_max_iterations(self):
        from cogant.config.translate import TranslateConfig

        cfg = TranslateConfig()
        assert cfg.max_iterations == 10

    def test_default_confidence_threshold(self):
        from cogant.config.translate import TranslateConfig

        cfg = TranslateConfig()
        assert cfg.confidence_threshold == 0.5

    def test_default_enable_rules_empty(self):
        from cogant.config.translate import TranslateConfig

        cfg = TranslateConfig()
        assert cfg.enable_rules == []

    def test_default_disable_rules_empty(self):
        from cogant.config.translate import TranslateConfig

        cfg = TranslateConfig()
        assert cfg.disable_rules == []

    def test_custom_max_iterations(self):
        from cogant.config.translate import TranslateConfig

        cfg = TranslateConfig(max_iterations=5)
        assert cfg.max_iterations == 5

    def test_custom_confidence_threshold(self):
        from cogant.config.translate import TranslateConfig

        cfg = TranslateConfig(confidence_threshold=0.8)
        assert cfg.confidence_threshold == 0.8

    def test_enable_specific_rules(self):
        from cogant.config.translate import TranslateConfig

        cfg = TranslateConfig(enable_rules=["rule_a", "rule_b"])
        assert "rule_a" in cfg.enable_rules

    def test_frozen_config(self):
        from cogant.config.translate import TranslateConfig

        cfg = TranslateConfig()
        with pytest.raises(ValidationError):
            cfg.max_iterations = 20


# ---------------------------------------------------------------------------
# config/statespace.py
# ---------------------------------------------------------------------------


class TestStatespaceConfig:
    def test_default_normalize_matrices(self):
        from cogant.config.statespace import StatespaceConfig

        cfg = StatespaceConfig()
        assert cfg.normalize_matrices is True

    def test_default_matrix_tolerance(self):
        from cogant.config.statespace import StatespaceConfig

        cfg = StatespaceConfig()
        assert cfg.matrix_tolerance == 1e-6

    def test_default_max_hidden_states(self):
        from cogant.config.statespace import StatespaceConfig

        cfg = StatespaceConfig()
        assert cfg.max_hidden_states == 512

    def test_default_max_observations(self):
        from cogant.config.statespace import StatespaceConfig

        cfg = StatespaceConfig()
        assert cfg.max_observations == 2048

    def test_disable_normalization(self):
        from cogant.config.statespace import StatespaceConfig

        cfg = StatespaceConfig(normalize_matrices=False)
        assert cfg.normalize_matrices is False

    def test_custom_max_hidden_states(self):
        from cogant.config.statespace import StatespaceConfig

        cfg = StatespaceConfig(max_hidden_states=128)
        assert cfg.max_hidden_states == 128

    def test_frozen_config(self):
        from cogant.config.statespace import StatespaceConfig

        cfg = StatespaceConfig()
        with pytest.raises(ValidationError):
            cfg.max_hidden_states = 1024


# ---------------------------------------------------------------------------
# cache/hasher.py
# ---------------------------------------------------------------------------


class TestHashFile:
    def test_hash_returns_string(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f = tmp_path / "test.py"
        f.write_bytes(b"x = 1\n")
        result = hash_file(f)
        assert isinstance(result, str)

    def test_hash_is_hex(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f = tmp_path / "test.py"
        f.write_bytes(b"print('hello')")
        result = hash_file(f)
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_length_sha256(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f = tmp_path / "test.py"
        f.write_bytes(b"content")
        result = hash_file(f)
        assert len(result) == 64

    def test_different_content_different_hash(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_bytes(b"x = 1")
        f2.write_bytes(b"y = 2")
        assert hash_file(f1) != hash_file(f2)

    def test_same_content_same_hash(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_bytes(b"hello")
        f2.write_bytes(b"hello")
        assert hash_file(f1) == hash_file(f2)


class TestHashRepo:
    def test_hash_empty_repo(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        result = hash_repo(tmp_path)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_repo_with_py_file(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "main.py").write_text("x = 1\n")
        result = hash_repo(tmp_path)
        assert isinstance(result, str)

    def test_hash_changes_when_file_added(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        h1 = hash_repo(tmp_path)
        (tmp_path / "new.py").write_text("new = True\n")
        h2 = hash_repo(tmp_path)
        assert h1 != h2

    def test_hash_ignores_non_default_extensions(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        h1 = hash_repo(tmp_path)
        (tmp_path / "readme.txt").write_text("ignored\n")
        h2 = hash_repo(tmp_path)
        assert h1 == h2

    def test_hash_custom_extensions(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "config.yaml").write_text("key: value\n")
        h1 = hash_repo(tmp_path, extensions=[".yaml"])
        h2 = hash_repo(tmp_path, extensions=[".py"])
        assert h1 != h2

    def test_hash_ignores_pycache(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        h1 = hash_repo(tmp_path)
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "compiled.py").write_text("# compiled\n")
        h2 = hash_repo(tmp_path)
        assert h1 == h2

    def test_hash_deterministic_order(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "z.py").write_text("z = 1\n")
        (tmp_path / "a.py").write_text("a = 1\n")
        h1 = hash_repo(tmp_path)
        h2 = hash_repo(tmp_path)
        assert h1 == h2


# ---------------------------------------------------------------------------
# cache/store.py
# ---------------------------------------------------------------------------


class TestCacheKey:
    def test_creation(self):
        from cogant.cache.store import CacheKey

        key = CacheKey(
            repo_path="/tmp/repo",
            content_hash="abc123",
            cogant_version="0.4.0",
        )
        assert key.repo_path == "/tmp/repo"
        assert key.content_hash == "abc123"
        assert key.cogant_version == "0.4.0"

    def test_frozen(self):
        from cogant.cache.store import CacheKey

        key = CacheKey(repo_path="/r", content_hash="h", cogant_version="1.0")
        with pytest.raises(dataclasses.FrozenInstanceError):
            key.repo_path = "/other"

    def test_equality(self):
        from cogant.cache.store import CacheKey

        k1 = CacheKey(repo_path="/r", content_hash="h", cogant_version="1.0")
        k2 = CacheKey(repo_path="/r", content_hash="h", cogant_version="1.0")
        assert k1 == k2

    def test_inequality(self):
        from cogant.cache.store import CacheKey

        k1 = CacheKey(repo_path="/r1", content_hash="h", cogant_version="1.0")
        k2 = CacheKey(repo_path="/r2", content_hash="h", cogant_version="1.0")
        assert k1 != k2


class TestCacheEntry:
    def test_creation(self):
        from cogant.cache.store import CacheEntry, CacheKey

        key = CacheKey(repo_path="/r", content_hash="h", cogant_version="1.0")
        entry = CacheEntry(key=key, created_at="2025-01-01T00:00:00Z", stage_results={})
        assert entry.key == key
        assert entry.hit is False

    def test_hit_default_false(self):
        from cogant.cache.store import CacheEntry, CacheKey

        key = CacheKey(repo_path="/r", content_hash="h", cogant_version="1.0")
        entry = CacheEntry(key=key, created_at="2025-01-01T00:00:00Z", stage_results={})
        assert entry.hit is False


class TestGetCacheDir:
    def test_returns_path(self):
        from cogant.cache.store import get_cache_dir

        result = get_cache_dir()
        assert isinstance(result, Path)

    def test_ends_with_cogant(self):
        from cogant.cache.store import get_cache_dir

        result = get_cache_dir()
        assert result.name == "cogant"


class TestCacheStore:
    def _make_key(self, suffix="abc123"):
        from cogant.cache.store import CacheKey

        return CacheKey(
            repo_path="/test/repo",
            content_hash="a" * 64,
            cogant_version="0.4.0",
        )

    def test_init_with_custom_dir(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        assert store._dir == tmp_path

    def test_miss_returns_none(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = self._make_key()
        result = store.get(key)
        assert result is None

    def test_put_and_get(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = self._make_key()
        store.put(key, {"analysis": {"nodes": 5}})
        entry = store.get(key)
        assert entry is not None
        assert entry.stage_results["analysis"]["nodes"] == 5

    def test_put_returns_entry(self, tmp_path):
        from cogant.cache.store import CacheEntry, CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = self._make_key()
        entry = store.put(key, {"x": 1})
        assert isinstance(entry, CacheEntry)

    def test_hit_flag_set_on_retrieval(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = self._make_key()
        store.put(key, {})
        entry = store.get(key)
        assert entry is not None
        assert entry.hit is True

    def test_invalidate_existing(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = self._make_key()
        store.put(key, {})
        result = store.invalidate(key)
        assert result is True
        assert store.get(key) is None

    def test_invalidate_missing(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = self._make_key()
        result = store.invalidate(key)
        assert result is False

    def test_clear_removes_entries(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path)
        k1 = CacheKey(repo_path="/r1", content_hash="a" * 64, cogant_version="1.0")
        k2 = CacheKey(repo_path="/r2", content_hash="b" * 64, cogant_version="1.0")
        store.put(k1, {"a": 1})
        store.put(k2, {"b": 2})
        count = store.clear()
        assert count == 2

    def test_clear_empty_store(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        count = store.clear()
        assert count == 0

    def test_stats_initial(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        s = store.stats()
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["hit_rate"] == 0.0

    def test_stats_after_miss(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        store.get(self._make_key())
        s = store.stats()
        assert s["misses"] == 1

    def test_stats_after_put_and_get(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = self._make_key()
        store.put(key, {})
        store.get(key)
        s = store.stats()
        assert s["hits"] == 1

    def test_stats_entries_count(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = self._make_key()
        store.put(key, {"x": 1})
        s = store.stats()
        assert s["entries"] == 1

    def test_ttl_expiry(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path, ttl_seconds=0)
        key = self._make_key()
        store.put(key, {})
        # With ttl=0, the entry should be expired immediately
        result = store.get(key)
        assert result is None

    def test_path_for_uses_hash_prefix(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = CacheKey(repo_path="/r", content_hash="deadbeef" + "0" * 56, cogant_version="1.0")
        path = store._path_for(key)
        assert path.parent.name == "de"  # first 2 chars of hash

    def test_serialize_deserialize_roundtrip(self, tmp_path):
        from cogant.cache.store import CacheEntry, CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path)
        key = CacheKey(repo_path="/r", content_hash="a" * 64, cogant_version="1.0")
        entry = CacheEntry(key=key, created_at="2025-01-01T00:00:00+00:00", stage_results={"n": 7})
        serialized = store._serialize(entry)
        deserialized = store._deserialize(serialized)
        assert deserialized.stage_results["n"] == 7
        assert deserialized.key.repo_path == "/r"
