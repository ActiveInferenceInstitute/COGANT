## Merge static and dynamic graphs
merged, provenance = merger.merge_graphs(
    static_graph=static_graph,
    dynamic_graph=dynamic_graph,
    conflict_resolution="union"
)

print(f"Nodes added: {provenance.nodes_added}")
print(f"Edges updated: {provenance.edges_updated}")
print(f"Conflicts: {len(provenance.conflicts)}")
```

---

### 3. Translation Layer

#### 3.1 TranslationEngine (`cogant/translate/engine.py`)

**Purpose:** Orchestrate rule application over program graphs.

**Key Methods:**
- `register_rule()` - Add a translation rule
- `translate()` - Apply all rules to graph
- `get_mappings_by_kind()` - Filter by MappingKind
- `get_mappings_by_confidence()` - Filter by ConfidenceTier
- `get_statistics()` - Mapping counts and distribution

**Example:**
```python
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import (
    ReadOnlyInputRule,
    MutatingSubsystemRule,
    OrchestratorRule,
)

engine = TranslationEngine()

