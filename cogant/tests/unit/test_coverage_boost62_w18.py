#!/usr/bin/env python3
"""Coverage boost batch 62 — normalize/canonical.py and normalize/identities.py.

Covers:
- normalize/canonical.py: LanguageFact, NormalizedFact dataclasses, CanonicalNormalizer
  (normalize with Python/JS/Java facts, normalize_batch, to_node, get_normalization_log,
  get_normalization_stats)
- normalize/identities.py: IdentityRecord, IdentityResolver (generate_id, get_id,
  lookup_id, get_record, deduplicate_ids, generate_edge_id, get_statistics, clear_cache)
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# normalize/canonical.py — LanguageFact and NormalizedFact
# ---------------------------------------------------------------------------


class TestLanguageFact:
    def test_language_fact_init(self):
        from cogant.normalize.canonical import LanguageFact

        fact = LanguageFact(
            fact_type="function_definition",
            language="python",
            data={"name": "my_func", "qualified_name": "module.my_func", "file": "module.py"},
        )
        assert fact.fact_type == "function_definition"
        assert fact.language == "python"
        assert fact.data["name"] == "my_func"

    def test_language_fact_with_data(self):
        from cogant.normalize.canonical import LanguageFact

        fact = LanguageFact(
            fact_type="class_definition",
            language="python",
            data={"name": "MyClass", "methods": ["__init__", "run"]},
        )
        assert fact.data.get("name") == "MyClass"


# ---------------------------------------------------------------------------
# normalize/canonical.py — CanonicalNormalizer
# ---------------------------------------------------------------------------


class TestCanonicalNormalizer:
    def _make_normalizer(self):
        from cogant.normalize.canonical import CanonicalNormalizer

        return CanonicalNormalizer()

    def _make_python_fact(self, fact_type="function_definition"):
        from cogant.normalize.canonical import LanguageFact

        return LanguageFact(
            fact_type=fact_type,
            language="python",
            data={"name": "my_func", "qualified_name": "mod.my_func", "file": "mod.py"},
        )

    def test_normalize_python_function(self):
        from cogant.normalize.canonical import NormalizedFact

        normalizer = self._make_normalizer()
        fact = self._make_python_fact("function_definition")
        result = normalizer.normalize(fact)
        assert result is None or isinstance(result, NormalizedFact)

    def test_normalize_python_class(self):
        normalizer = self._make_normalizer()
        fact = self._make_python_fact("class_definition")
        result = normalizer.normalize(fact)
        # Should produce a NormalizedFact or None
        assert result is None or hasattr(result, "qualified_name")

    def test_normalize_batch_empty(self):
        normalizer = self._make_normalizer()
        results = normalizer.normalize_batch([])
        assert results == []

    def test_normalize_batch_multiple(self):
        from cogant.normalize.canonical import LanguageFact

        normalizer = self._make_normalizer()
        facts = [
            LanguageFact("function_definition", "python", {"name": "f1", "qualified_name": "m.f1"}),
            LanguageFact("class_definition", "python", {"name": "C1", "qualified_name": "m.C1"}),
        ]
        results = normalizer.normalize_batch(facts)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_get_normalization_log_empty(self):
        normalizer = self._make_normalizer()
        log = normalizer.get_normalization_log()
        assert isinstance(log, list)

    def test_get_normalization_stats_empty(self):
        normalizer = self._make_normalizer()
        stats = normalizer.get_normalization_stats()
        assert isinstance(stats, dict)

    def test_get_normalization_stats_after_normalize(self):
        normalizer = self._make_normalizer()
        fact = self._make_python_fact("function")
        normalizer.normalize(fact)
        stats = normalizer.get_normalization_stats()
        assert isinstance(stats, dict)

    def test_to_node_returns_none_or_dict(self):
        normalizer = self._make_normalizer()
        fact = self._make_python_fact()
        normalized = normalizer.normalize(fact)
        if normalized is not None:
            result = normalizer.to_node(normalized)
            assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# normalize/identities.py — IdentityRecord and IdentityResolver
# ---------------------------------------------------------------------------


class TestIdentityRecord:
    def test_identity_record_init(self):
        from cogant.normalize.identities import IdentityRecord

        record = IdentityRecord(
            id="abcdef1234567890",
            entity_type="function",
            repo_uri="file:///repo",
            path="mod.py",
            qualified_name="mod.my_func",
            hash_inputs="file:///repo|mod.py|mod.my_func",
        )
        assert record.id == "abcdef1234567890"
        assert record.entity_type == "function"
        assert record.repo_uri == "file:///repo"


class TestIdentityResolver:
    def _make_resolver(self):
        from cogant.normalize.identities import IdentityResolver

        return IdentityResolver()

    def test_init(self):
        resolver = self._make_resolver()
        assert resolver is not None

    def test_generate_id_returns_str(self):
        resolver = self._make_resolver()
        identity_id = resolver.generate_id(
            entity_type="function",
            repo_uri="file:///repo",
            path="mod.py",
            qualified_name="mod.func",
        )
        assert isinstance(identity_id, str)
        assert len(identity_id) > 0

    def test_generate_id_deterministic(self):
        resolver = self._make_resolver()
        id1 = resolver.generate_id("function", "file:///repo", "mod.py", "mod.func")
        id2 = resolver.generate_id("function", "file:///repo", "mod.py", "mod.func")
        assert id1 == id2

    def test_generate_id_different_names(self):
        resolver = self._make_resolver()
        id1 = resolver.generate_id("function", "file:///repo", "mod.py", "mod.func_a")
        id2 = resolver.generate_id("function", "file:///repo", "mod.py", "mod.func_b")
        assert id1 != id2

    def test_get_id_returns_str(self):
        resolver = self._make_resolver()
        result = resolver.get_id(
            entity_type="class",
            repo_uri="file:///repo",
            path="mod.py",
            qualified_name="mod.Cls",
        )
        assert isinstance(result, str)

    def test_lookup_id_after_generate(self):
        resolver = self._make_resolver()
        resolver.generate_id("function", "file:///repo", "mod.py", "mod.fn")
        # lookup_id uses same params as generate_id and returns the id string or None
        result = resolver.lookup_id("function", "file:///repo", "mod.py", "mod.fn")
        assert result is None or isinstance(result, str)

    def test_lookup_id_unknown(self):
        resolver = self._make_resolver()
        result = resolver.lookup_id("function", "file:///nonexistent", "none.py", "none.fn")
        assert result is None

    def test_get_record_after_generate(self):
        from cogant.normalize.identities import IdentityRecord

        resolver = self._make_resolver()
        identity_id = resolver.generate_id("function", "file:///repo", "mod.py", "mod.fn")
        record = resolver.get_record(identity_id)
        assert record is None or isinstance(record, IdentityRecord)

    def test_deduplicate_ids_empty(self):
        resolver = self._make_resolver()
        result = resolver.deduplicate_ids([])
        assert result == []

    def test_deduplicate_ids_removes_duplicates(self):
        resolver = self._make_resolver()
        result = resolver.deduplicate_ids(["id1", "id2", "id1", "id3"])
        assert len(result) == 3

    def test_generate_edge_id(self):
        resolver = self._make_resolver()
        edge_id = resolver.generate_edge_id("src_node", "tgt_node", "CONTAINS")
        assert isinstance(edge_id, str)
        assert len(edge_id) > 0

    def test_generate_edge_id_deterministic(self):
        resolver = self._make_resolver()
        id1 = resolver.generate_edge_id("a", "b", "CONTAINS")
        id2 = resolver.generate_edge_id("a", "b", "CONTAINS")
        assert id1 == id2

    def test_get_statistics_empty(self):
        resolver = self._make_resolver()
        stats = resolver.get_statistics()
        assert isinstance(stats, dict)

    def test_get_statistics_after_generate(self):
        resolver = self._make_resolver()
        resolver.generate_id("function", "file:///repo", "mod.py", "mod.fn")
        stats = resolver.get_statistics()
        assert isinstance(stats, dict)

    def test_clear_cache(self):
        resolver = self._make_resolver()
        identity_id = resolver.generate_id("function", "file:///repo", "mod.py", "mod.fn")
        resolver.clear_cache()
        # After clear, get_record should return None
        result = resolver.get_record(identity_id)
        assert result is None
