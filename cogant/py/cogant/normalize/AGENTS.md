# Agents — py/cogant/normalize

## Owner
Normalization

## Responsibilities
CanonicalNormalizer maps language-specific fact types to canonical NodeKind. Supports Python, JavaScript, Java, and generic constructs. IdentityResolver generates SHA256-based stable IDs for all repository entities (repo, module, file, symbol, endpoint, event). Each ID is deterministic: same repo_uri + path + qualified_name always produces same ID.

## Coordination
Input: LanguageFact from static (parser-extracted) and dynamic (runtime) analysis. Output: NormalizedFact and stable IDs used by graph/builder.py. No configuration; pure transformation.

## How to Extend
Add language support: extend CanonicalNormalizer._fact_kind_mapping with new "language:fact_type" → NodeKind entries. Add entity type: extend IdentityResolver.generate_id entity_type enum and _build_hash_input as needed.
