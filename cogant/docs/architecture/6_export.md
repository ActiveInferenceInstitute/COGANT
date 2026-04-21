## 6. Export
final = reviewer.export_reviewed_mappings()
```

### File Locations

All files located in `/sessions/focused-bold-noether/mnt/cogant/`:

```
py/cogant/
├── normalize/
│   ├── __init__.py (14 lines)
│   ├── identities.py (293 lines)
│   └── canonical.py (337 lines)
├── graph/
│   ├── __init__.py (11 lines)
│   ├── builder.py (373 lines)
│   ├── queries.py (420 lines)
│   └── merge.py (280 lines)
├── translate/
│   ├── __init__.py (24 lines)
│   ├── engine.py (123 lines)
│   ├── rules.py (493 lines)
│   ├── confidence.py (283 lines)
│   └── review.py (273 lines)
└── schemas/
    ├── core.py (180 lines)
    ├── graph.py (95 lines)
    └── semantic.py (61 lines)

tests/
└── test_engine.py (394 lines)

documentation/
├── Detailed graph engine (850+ lines, this document)
└── Graph engine summary (this document)
```

### Testing

Run the test suite:

```bash
cd /sessions/focused-bold-noether/mnt/cogant
python tests/test_engine.py
```

Expected output:
```
============================================================
COGANT Engine Integration Tests
============================================================

=== Testing IdentityResolver ===
✓ IdentityResolver tests passed

=== Testing CanonicalNormalizer ===
✓ CanonicalNormalizer tests passed

=== Testing ProgramGraphBuilder ===
✓ ProgramGraphBuilder tests passed

=== Testing GraphQuery ===
✓ GraphQuery tests passed

=== Testing TranslationEngine ===
✓ TranslationEngine tests passed

=== Testing ConfidenceModel ===
✓ ConfidenceModel tests passed

=== Testing ReviewManager ===
✓ ReviewManager tests passed

=== Testing GraphMerger ===
✓ GraphMerger tests passed

============================================================
All tests passed! ✓
============================================================
```

### Architecture Highlights

1. **Modularity**: Each component (normalize, graph, translate) is independent and composable
2. **Type Safety**: Extensive use of dataclasses, enums, and type hints
3. **Deterministic**: Stable IDs and reproducible processing
4. **Provenance**: Complete audit trail of all operations
5. **Extensibility**: Easy to add new translation rules
6. **Confidence**: Evidence-based scoring with transparency
7. **Human-in-the-Loop**: Full review workflow with edit/split/merge
8. **Documentation**: Comprehensive examples and API docs

### Future Extensions

The engine is designed to support:
- Additional translation rules
- Custom confidence models
- Alternative identity schemes
- Graph visualization
- Export to various formats
- Integration with GNN training pipelines
- Real-time processing
- Distributed graph building

---
