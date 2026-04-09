## {'total_identities': N, 'unique_hash_inputs': M, 'type_module': X, ...}
```

#### 1.2 CanonicalNormalizer (`cogant/normalize/canonical.py`)

**Purpose:** Convert language-specific facts into canonical NodeKind objects.

**Mapping Examples:**
- `python:class` → `NodeKind.CLASS`
- `javascript:async_function` → `NodeKind.FUNCTION`
- `java:interface` → `NodeKind.CLASS`

**Key Methods:**
- `normalize()` - Convert single LanguageFact to NormalizedFact
- `normalize_batch()` - Convert multiple facts
- `to_node()` - Create Node object from normalized fact
- `get_normalization_stats()` - Track unmapped facts

**Example:**
```python
from cogant.normalize.canonical import CanonicalNormalizer, LanguageFact

normalizer = CanonicalNormalizer()

