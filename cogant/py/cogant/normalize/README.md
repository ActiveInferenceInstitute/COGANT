# Normalize — Language-Specific Fact Normalization

The normalize module converts language-specific facts extracted by static and dynamic analysis into a canonical form suitable for universal graph construction.

## Module Overview

LanguageFact represents a raw fact extracted from code analysis: a fact_type (e.g., "class_definition", "function_call"), language name, and arbitrary data dictionary. CanonicalNormalizer converts LanguageFact to NormalizedFact, mapping language-specific fact types to canonical NodeKind values. The mapping handles Python, JavaScript, Java, and generic constructs.

IdentityResolver generates and caches stable, deterministic identities for repository elements. Each identity is a 16-character hex string derived from SHA256(repo_uri + path + qualified_name). The same input always produces the same ID, enabling consistent deduplication across multiple analysis runs.

IdentityRecord documents a generated identity: the ID itself, entity type (repo, module, file, symbol, endpoint, event), repo URI, path, qualified name, and the concatenated hash input.

## API Reference

CanonicalNormalizer class with methods:
- normalize(fact) — Convert LanguageFact to NormalizedFact (returns None if unmappable)

IdentityResolver class with methods:
- generate_id(entity_type, repo_uri, path=None, qualified_name=None) — Generate deterministic ID and cache it
- get_id_record(identity_id) — Retrieve cached IdentityRecord
- lookup_id(repo_uri, path, qualified_name) — Find ID by reverse lookup (returns None if not in cache)

Data classes:
- LanguageFact(fact_type, language, data) — Raw language-specific fact
- NormalizedFact(node_kind, name, qualified_name, path, language, metadata) — Canonical form of fact
- IdentityRecord(id, entity_type, repo_uri, path, qualified_name, hash_inputs) — Record of generated identity
