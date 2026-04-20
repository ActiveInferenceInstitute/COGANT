"""Tests for cogant.normalize — CanonicalNormalizer and IdentityResolver."""

from __future__ import annotations

import pytest

from cogant.normalize.canonical import CanonicalNormalizer, LanguageFact, NormalizedFact
from cogant.normalize.identities import IdentityRecord, IdentityResolver
from cogant.schemas.core import NodeKind


# ---------------------------------------------------------------------------
# CanonicalNormalizer — normalize()
# ---------------------------------------------------------------------------


def test_normalize_python_class() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="class",
        language="python",
        data={"name": "MyClass", "qualified_name": "mymodule.MyClass", "path": "mymodule.py"},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.node_kind == NodeKind.CLASS
    assert result.name == "MyClass"
    assert result.qualified_name == "mymodule.MyClass"
    assert result.path == "mymodule.py"
    assert result.language == "python"


def test_normalize_python_function() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="function",
        language="python",
        data={"name": "my_func", "is_async": True},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.node_kind == NodeKind.FUNCTION
    assert result.metadata is not None
    assert result.metadata.get("is_async") is True


def test_normalize_javascript_arrow_function() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="arrow_function",
        language="javascript",
        data={"name": "handler", "is_arrow": True, "export_type": "named"},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.node_kind == NodeKind.FUNCTION
    assert result.metadata is not None
    assert result.metadata.get("is_arrow") is True
    assert result.metadata.get("export_type") == "named"


def test_normalize_java_class() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="class",
        language="java",
        data={"name": "MyService", "modifiers": ["public"], "annotations": ["@Service"]},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.node_kind == NodeKind.CLASS
    assert result.metadata is not None
    assert result.metadata.get("modifiers") == ["public"]
    assert result.metadata.get("annotations") == ["@Service"]


def test_normalize_generic_module() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="module",
        language="generic",
        data={"name": "utils"},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.node_kind == NodeKind.MODULE


def test_normalize_unmapped_returns_none() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="unknown_type",
        language="cobol",
        data={"name": "something"},
    )
    result = normalizer.normalize(fact)
    assert result is None


def test_normalize_logs_unmapped_fact() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(fact_type="xyz", language="brainfuck", data={})
    normalizer.normalize(fact)
    log = normalizer.get_normalization_log()
    assert len(log) == 1
    assert log[0]["status"] == "unmapped_fact"
    assert log[0]["language"] == "brainfuck"


def test_normalize_logs_success() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(fact_type="class", language="python", data={"name": "A"})
    normalizer.normalize(fact)
    log = normalizer.get_normalization_log()
    assert len(log) == 1
    assert log[0]["status"] == "normalized"


# ---------------------------------------------------------------------------
# CanonicalNormalizer — normalize_batch()
# ---------------------------------------------------------------------------


def test_normalize_batch_preserves_order() -> None:
    normalizer = CanonicalNormalizer()
    facts = [
        LanguageFact("class", "python", {"name": "A"}),
        LanguageFact("unknown", "cobol", {"name": "B"}),
        LanguageFact("function", "python", {"name": "C"}),
    ]
    results = normalizer.normalize_batch(facts)
    assert len(results) == 3
    assert results[0] is not None and results[0].name == "A"
    assert results[1] is None
    assert results[2] is not None and results[2].name == "C"


def test_normalize_batch_empty() -> None:
    normalizer = CanonicalNormalizer()
    assert normalizer.normalize_batch([]) == []


# ---------------------------------------------------------------------------
# CanonicalNormalizer — to_node()
# ---------------------------------------------------------------------------


def test_to_node_creates_valid_node() -> None:
    normalizer = CanonicalNormalizer()
    fact = LanguageFact("class", "python", {"name": "MyClass", "path": "mod.py"})
    normalized = normalizer.normalize(fact)
    assert normalized is not None
    node = normalizer.to_node(normalized, node_id="abc123")
    assert node.id == "abc123"
    assert node.kind == NodeKind.CLASS
    assert node.name == "MyClass"
    assert node.path == "mod.py"
    assert node.language == "python"


# ---------------------------------------------------------------------------
# CanonicalNormalizer — get_normalization_stats()
# ---------------------------------------------------------------------------


def test_normalization_stats_counts() -> None:
    normalizer = CanonicalNormalizer()
    normalizer.normalize(LanguageFact("class", "python", {"name": "A"}))
    normalizer.normalize(LanguageFact("function", "python", {"name": "B"}))
    normalizer.normalize(LanguageFact("??", "cobol", {"name": "C"}))
    stats = normalizer.get_normalization_stats()
    assert stats["total_normalizations"] == 3
    assert stats["normalized"] == 2
    assert stats["unmapped_facts"] == 1


def test_normalization_stats_empty() -> None:
    normalizer = CanonicalNormalizer()
    stats = normalizer.get_normalization_stats()
    assert stats["total_normalizations"] == 0
    assert stats["normalized"] == 0
    assert stats["unmapped_facts"] == 0


# ---------------------------------------------------------------------------
# IdentityResolver — generate_id() / get_id() idempotency
# ---------------------------------------------------------------------------


def test_generate_id_is_deterministic() -> None:
    r1, r2 = IdentityResolver(), IdentityResolver()
    id1 = r1.generate_id("symbol", "https://github.com/org/repo", "src/a.py", "A.method")
    id2 = r2.generate_id("symbol", "https://github.com/org/repo", "src/a.py", "A.method")
    assert id1 == id2


def test_generate_id_hex_16_chars() -> None:
    resolver = IdentityResolver()
    identity_id = resolver.generate_id("module", "repo_uri")
    assert len(identity_id) == 16
    assert all(c in "0123456789abcdef" for c in identity_id)


def test_get_id_is_idempotent() -> None:
    resolver = IdentityResolver()
    id1 = resolver.get_id("file", "repo", path="src/main.py")
    id2 = resolver.get_id("file", "repo", path="src/main.py")
    assert id1 == id2


def test_get_id_same_as_generate_id() -> None:
    resolver = IdentityResolver()
    generated = resolver.generate_id("class", "repo", "mod.py", "MyClass")
    retrieved = resolver.get_id("class", "repo", "mod.py", "MyClass")
    assert generated == retrieved


def test_different_inputs_produce_different_ids() -> None:
    resolver = IdentityResolver()
    id_a = resolver.generate_id("symbol", "repo", "a.py", "FuncA")
    id_b = resolver.generate_id("symbol", "repo", "b.py", "FuncB")
    assert id_a != id_b


# ---------------------------------------------------------------------------
# IdentityResolver — lookup_id()
# ---------------------------------------------------------------------------


def test_lookup_id_returns_none_before_generation() -> None:
    resolver = IdentityResolver()
    result = resolver.lookup_id("symbol", "repo", "a.py", "Missing")
    assert result is None


def test_lookup_id_returns_id_after_generation() -> None:
    resolver = IdentityResolver()
    identity_id = resolver.generate_id("symbol", "repo", "a.py", "Exists")
    assert resolver.lookup_id("symbol", "repo", "a.py", "Exists") == identity_id


# ---------------------------------------------------------------------------
# IdentityResolver — deduplicate_ids()
# ---------------------------------------------------------------------------


def test_deduplicate_ids_removes_duplicates() -> None:
    resolver = IdentityResolver()
    ids = ["aaa", "bbb", "aaa", "ccc", "bbb"]
    assert resolver.deduplicate_ids(ids) == ["aaa", "bbb", "ccc"]


def test_deduplicate_ids_empty() -> None:
    resolver = IdentityResolver()
    assert resolver.deduplicate_ids([]) == []


def test_deduplicate_ids_all_unique() -> None:
    resolver = IdentityResolver()
    ids = ["x", "y", "z"]
    assert resolver.deduplicate_ids(ids) == ids


# ---------------------------------------------------------------------------
# IdentityResolver — generate_edge_id()
# ---------------------------------------------------------------------------


def test_generate_edge_id_deterministic() -> None:
    r1, r2 = IdentityResolver(), IdentityResolver()
    eid1 = r1.generate_edge_id("node_a", "node_b", "CALLS")
    eid2 = r2.generate_edge_id("node_a", "node_b", "CALLS")
    assert eid1 == eid2


def test_generate_edge_id_differs_by_kind() -> None:
    resolver = IdentityResolver()
    eid_calls = resolver.generate_edge_id("n1", "n2", "CALLS")
    eid_reads = resolver.generate_edge_id("n1", "n2", "READS")
    assert eid_calls != eid_reads


def test_generate_edge_id_asymmetric() -> None:
    resolver = IdentityResolver()
    eid_fwd = resolver.generate_edge_id("src", "dst", "DEPENDS_ON")
    eid_rev = resolver.generate_edge_id("dst", "src", "DEPENDS_ON")
    assert eid_fwd != eid_rev


# ---------------------------------------------------------------------------
# IdentityResolver — get_statistics() / clear_cache()
# ---------------------------------------------------------------------------


def test_get_statistics_counts_by_type() -> None:
    resolver = IdentityResolver()
    resolver.generate_id("module", "repo", "mod.py")
    resolver.generate_id("module", "repo", "other.py")
    resolver.generate_id("symbol", "repo", "mod.py", "Func")
    stats = resolver.get_statistics()
    assert stats["total_identities"] == 3
    assert stats["type_module"] == 2
    assert stats["type_symbol"] == 1


def test_get_statistics_empty() -> None:
    resolver = IdentityResolver()
    stats = resolver.get_statistics()
    assert stats["total_identities"] == 0
    assert stats["unique_hash_inputs"] == 0


def test_clear_cache_resets_state() -> None:
    resolver = IdentityResolver()
    resolver.generate_id("module", "repo", "mod.py")
    resolver.clear_cache()
    stats = resolver.get_statistics()
    assert stats["total_identities"] == 0
    assert resolver.lookup_id("module", "repo", "mod.py") is None


# ---------------------------------------------------------------------------
# IdentityRecord
# ---------------------------------------------------------------------------


def test_get_record_returns_full_record() -> None:
    resolver = IdentityResolver()
    identity_id = resolver.generate_id("file", "my_repo", "src/a.py")
    record = resolver.get_record(identity_id)
    assert record is not None
    assert isinstance(record, IdentityRecord)
    assert record.id == identity_id
    assert record.entity_type == "file"
    assert record.repo_uri == "my_repo"
    assert record.path == "src/a.py"


def test_get_record_missing_returns_none() -> None:
    resolver = IdentityResolver()
    assert resolver.get_record("nonexistent_id") is None
