## Use final_mappings for GNN export

> **Note:** "GNN" here refers to Generalized Notation Notation (the Active Inference Institute's structured state-space and process-model notation), NOT graph neural networks. COGANT translates code into GNN model artifacts; it does not train neural network layers.
```

---

### Key Data Structures

#### Node
```python
@dataclass
class Node:
    id: str                          # Stable ID from IdentityResolver
    kind: NodeKind                   # REPO, MODULE, CLASS, FUNCTION, etc.
    name: str                        # Human-readable name
    qualified_name: str              # Fully qualified name
    path: Optional[str]              # File/module path
    language: Optional[str]          # python, javascript, java, etc.
    source_range: Optional[Dict]     # Start/end line/column
    metadata: Dict[str, Any]         # Language-specific metadata
```

#### Edge
```python
@dataclass
class Edge:
    id: str                          # Stable ID
    source_id: str                   # Source node ID
    target_id: str                   # Target node ID
    kind: EdgeKind                   # CALLS, READS, WRITES, etc.
    weight: float                    # Frequency, confidence, etc.
    metadata: Dict[str, Any]         # Additional info
    evidence_sources: List[str]      # ["static", "dynamic", etc.]
```

#### SemanticMapping
```python
@dataclass
class SemanticMapping:
    id: str                          # Unique ID
    kind: MappingKind                # OBSERVATION, ACTION, etc.
    graph_fragment_node_ids: List[str]
    graph_fragment_edge_ids: List[str]
    semantic_label: str              # Human-readable label
    description: str                 # Detailed description
    confidence_score: float          # 0.0-1.0
    confidence_tier: ConfidenceTier  # STATIC_ONLY, etc.
    provenance: List[ProvenanceRecord]
    evidence_count: int
    evidence_diversity: float
    parser_certainty: float
    conflict_penalties: List[float]
    status: str                      # auto_proposed, accepted, etc.
    review_feedback: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
```

---

### File Organization

```
py/cogant/
├── normalize/
│   ├── __init__.py
│   ├── identities.py        # IdentityResolver
│   └── canonical.py         # CanonicalNormalizer
├── graph/
│   ├── __init__.py
│   ├── builder.py           # ProgramGraphBuilder
│   ├── queries.py           # GraphQuery
│   └── merge.py             # GraphMerger
├── translate/
│   ├── __init__.py
│   ├── engine.py            # TranslationEngine
│   ├── rules.py             # 8 concrete rules
│   ├── confidence.py        # ConfidenceModel
│   └── review.py            # ReviewManager
└── schemas/
    ├── __init__.py
    ├── core.py              # Node, Edge, NodeKind, EdgeKind
    ├── graph.py             # ProgramGraph, GraphMetadata
    └── semantic.py          # SemanticMapping, etc.
```

---

### Running Tests

```bash
cd /sessions/focused-bold-noether/mnt/cogant
python tests/test_engine.py
```

Output shows:
- Identity generation and idempotency
- Normalization of language facts
- Graph building and statistics
- Query operations (filtering, centrality, paths)
- Translation rule application
- Confidence scoring
- Review management
- Graph merging

---

### Integration with GNN (Generalized Notation Notation) export

The final semantic mappings from the ReviewManager are ready for:

1. **State space modeling** - Observations, actions, hidden states populate the GNN `StateSpaceBlock`
2. **Policy synthesis** - Constraint and preference roles populate the GNN policy section
3. **Transition modeling** - State transition structure populates the B matrix
4. **Likelihood modeling** - Probabilistic relationships populate the A matrix
5. **GNN package emission** - Final mappings are serialized to a GNN package directory consumed by the reverse pipeline. GNN here is the Active Inference Institute's notation, not graph neural networks.

All mappings include provenance, confidence scores, and human review status for traceability and quality assurance.

---
