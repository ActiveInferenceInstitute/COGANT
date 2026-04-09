## COGANT Graph Construction, Normalization, and Translation Engine

**Which doc should I read?** Short inventory: [Graph engine summary](#graph-engine-summary). Ingest/static pipeline: [SPEC.md](../reference/README.md). Architecture: [ARCHITECTURE.md](../architecture/README.md). Hub: [README.md](./README.md).

This document describes the complete engine for COGANT - the **Codebase-to-GNN Translation** system. The engine consists of three major components: normalization, graph construction, and semantic translation.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    STATIC/DYNAMIC ANALYSIS                  │
│              (Language-specific facts extracted)             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  NORMALIZATION LAYER                         │
│  • IdentityResolver: Stable ID generation                    │
│  • CanonicalNormalizer: Language-agnostic transformation    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  GRAPH CONSTRUCTION LAYER                    │
│  • ProgramGraphBuilder: Typed nodes and edges                │
│  • GraphQuery: Analysis and traversal                        │
│  • GraphMerger: Combine static + dynamic evidence            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  TRANSLATION LAYER                           │
│  • TranslationEngine: Rule orchestration                     │
│  • 8 Concrete Rules: Pattern detection                       │
│  • ConfidenceModel: Evidence scoring                         │
│  • ReviewManager: Human curation                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              SEMANTIC MAPPINGS (for GNN training)            │
│  • Observations, Actions, Hidden State                       │
│  • Policies, Constraints, Preferences                        │
│  • Provenance and Confidence Tiers                           │
└─────────────────────────────────────────────────────────────┘
```

---

### 1. Normalization Layer

#### 1.1 IdentityResolver (`cogant/normalize/identities.py`)

**Purpose:** Generate stable, deterministic IDs for all repository elements.

**Key Methods:**
- `generate_id()` - Create stable ID using SHA256(repo_uri | path | qualified_name)
- `get_id()` - Get or create ID (idempotent)
- `lookup_id()` - Look up without creating
- `generate_edge_id()` - Create stable edge IDs
- `deduplicate_ids()` - Remove duplicates while preserving order

**Example:**
```python
from cogant.normalize.identities import IdentityResolver

resolver = IdentityResolver()

