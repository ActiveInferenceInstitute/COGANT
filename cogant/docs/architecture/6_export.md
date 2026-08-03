## 6. Export

The export stage serializes the pipeline's artifacts — the `ProgramGraph`, semantic
mappings, and derived state-space / process models — into a **bundle**: a directory of
files plus a manifest with checksums and provenance. It runs after translation,
state-space compilation, and process extraction (stage 9 of the 10-stage pipeline) and
is followed by validation (stage 10).

The GNN bundle itself (the 19-section markdown package) is emitted by
`cogant.gnn`; the multi-format serializers live under `py/cogant/export/` and are
driven by `cogant export` / `cogant export-gnn` on the CLI.

### File Locations

All paths are relative to the package root (the directory containing `py/`, `tests/`,
`pyproject.toml`):

```
py/cogant/
├── normalize/
│   ├── identities.py        # IdentityResolver
│   └── canonical.py         # CanonicalNormalizer
├── graph/
│   ├── builder.py           # ProgramGraphBuilder
│   ├── queries.py           # GraphQuery
│   ├── merge.py             # GraphMerger
│   └── analysis.py          # GraphAnalyzer (centrality, communities, cycles)
├── translate/
│   ├── engine.py            # TranslationEngine
│   ├── rules/               # 22 concrete rules across 5 family modules
│   │   ├── structural.py
│   │   ├── semantic.py
│   │   ├── control.py
│   │   ├── behavioral.py
│   │   └── resilience.py
│   ├── confidence.py        # ConfidenceModel
│   └── review.py            # ReviewManager
├── export/
│   ├── formats.py           # ExportFormat enum, ExportConfig, MultiFormatExporter
│   ├── bundle.py            # BundleExporter
│   ├── typed_export.py      # TypedExporter (JSON + schema)
│   ├── graphml.py           # GraphMLExporter
│   ├── parquet.py           # ParquetExporter
│   ├── svg_export.py        # SVGExporter
│   ├── json_schema.py       # JSONSchemaExporter
│   └── markdown.py          # render_bundle_markdown (export-gnn --format markdown)
└── schemas/
    ├── core.py              # NodeKind, EdgeKind
    ├── graph.py             # ProgramGraph, GraphMetadata
    ├── semantic.py          # MappingKind, ConfidenceTier
    ├── semantic_mapping.py  # SemanticMapping, SemanticRole
    └── gnn_export.py        # 19 canonical GNN bundle sections
```

The `ExportFormat` enum in `py/cogant/export/formats.py` is the canonical list of
supported formats: `json`, `graphml`, `parquet`, `svg`, `png`, `pdf`, `mermaid`,
`dot`, and `jsonlines`.

### Testing

Run the test suite from the package root:

```bash
cd <package-root>   # the directory containing py/, tests/, pyproject.toml
uv run pytest tests/ -q --no-cov
```

This runs the full unit / integration / property / golden / fuzz suite, including the
pipeline integration tests in `tests/test_engine.py`. For a single file:

```bash
uv run pytest tests/test_engine.py -v
```

### Architecture Highlights

1. **Modularity**: Each component (normalize, graph, translate, export) is independent and composable
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
