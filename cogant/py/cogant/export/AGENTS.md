# Agents — py/cogant/export

## Owner
Export and Serialization Lead

## What Is the Export Module

The `export/` module **serializes COGANT artifacts** to multiple formats: JSON (typed), GraphML (graph exchange), Parquet (columnar analytics), SVG (vector graphics), JSON Schema, and more. Exports preserve all metadata, provenance, and confidence scores. A single call can write to all formats simultaneously.

Export happens **late in the pipeline** (stage 9), after translation, state space construction, and validation. The output is a **bundle** — a directory with organized files, a manifest, and checksums.

## Pipeline Integration

```
stage 3: graph/         → ProgramGraph
    ↓
stage 4: translate/     → SemanticMappings
    ↓
stage 5: statespace/    → StateSpaceModel (A/B/C/D matrices)
    ↓
stage 6-8: process, validate, ...
    ↓
stage 9: export/        → Bundle (JSON, GraphML, Parquet, SVG, HTML, ...)
    ↓
stage 10: (users consume exported files)
```

## Supported Formats

### Format Enum & Usage Matrix

```python
class ExportFormat(Enum):
    JSON = "json"              # Typed JSON with schema
    GRAPHML = "graphml"        # Graph interchange format (XML-based)
    PARQUET = "parquet"        # Columnar format (Apache Arrow)
    SVG = "svg"                # Scalable vector graphics
    PNG = "png"                # Bitmap image
    PDF = "pdf"                # Multi-page PDF report
    MERMAID = "mermaid"        # Mermaid diagram syntax
    DOT = "dot"                # Graphviz DOT format
    JSONLINES = "jsonlines"    # Line-delimited JSON
```

| Format | Use Case | Data Type | Size (typical) | External Deps |
|--------|----------|-----------|----------------|---------------|
| JSON | Web APIs, data interchange | Structured, typed | 1-50 MB | None |
| GRAPHML | Graph visualization tools, Gephi | Graph representation | 2-100 MB | None |
| Parquet | Analytics, Data Warehouse | Tabular/columnar | 0.5-20 MB | PyArrow |
| SVG | Web embedding, scalable graphics | Vector image | 1-100 MB | graphviz (optional) |
| PNG | Quick previews, reports | Bitmap image | 0.5-50 MB | matplotlib, Pillow |
| PDF | Publication, reports | Multi-page document | 5-200 MB | matplotlib, reportlab |
| Mermaid | Markdown, GitHub wikis | Diagram syntax (text) | 0.01-1 MB | None |
| DOT | Graphviz processing | Graph syntax (text) | 0.1-10 MB | graphviz (optional) |
| JSONLINES | Streaming, log processing | Line-delimited JSON | 2-100 MB | None |

## Core Components

### Existing Export Modules (4 files)

**typed_export.py** — `TypedExporter`
- Export to JSON with schema (OpenAPI-compatible)
- Type annotations for all fields
- JSON Schema generation
- Methods: `export_graph()`, `export_semantic_mappings()`, `export_bundle()`

**graphml.py** — `GraphMLExporter`
- Export to GraphML (XML-based graph interchange format)
- Compatible with Gephi, yEd, Cytoscape
- Preserves node/edge attributes
- Methods: `export_graph()`, `with_metadata()`, `with_node_attributes()`

**parquet.py** — `ParquetExporter`
- Export nodes/edges to Parquet (columnar format)
- Requires PyArrow
- Methods: `export_nodes()`, `export_edges()`, `export_mappings()`

**bundle.py** — `BundleExporter`
- Orchestrate multi-format export in single call
- Generate bundle manifest with file inventory and checksums
- Create directory structure: `cogant_bundle_{timestamp}/`
- Methods: `export()`, `with_formats()`, `with_provenance()`

### New Export Modules (3 files)

**formats.py** — `MultiFormatExporter`
- High-level orchestration of multi-format export
- Batch export to multiple formats in single call
- Consistent error handling and logging
- Methods: `export_to_all()`, `export_subset()`, `with_validation()`

```python
class MultiFormatExporter:
    def export_to_all(
        self,
        graph: ProgramGraph,
        mappings: SemanticMappings,
        output_dir: Path,
        formats: List[ExportFormat]
    ) -> BundleManifest:
        """Export to multiple formats in one call."""
```

**svg_export.py** — `SVGExporter`
- Vector graph export via graphviz or Cairo
- Requires graphviz (optional)
- Methods: `export_graph()`, `export_with_layout()`, `with_styling()`

**json_schema.py** — `JSONSchemaExporter`
- Export JSON Schema (OpenAPI 3.0 compatible)
- Document ProgramGraph and SemanticMappings structure
- Methods: `export_schema()`, `with_examples()`, `with_validation_rules()`

## Data Representations

### Bundle Structure

```
cogant_bundle_2026_04_13_120000/
├── manifest.json              # Bundle metadata + checksums
├── graph.json                 # Typed graph export
├── graph.graphml              # GraphML graph
├── graph.parquet              # Columnar edges/nodes
├── semantic_mappings.json     # SemanticMappings
├── matrices/
│   ├── A_matrix.json
│   ├── B_matrix.json
│   ├── C_prior.json
│   └── D_prior.json
├── analysis/
│   ├── complexity_report.json
│   ├── coupling_report.json
│   └── metrics_report.json
├── visualizations/
│   ├── graph.png
│   ├── graph.pdf
│   └── graph.svg
└── metadata.json              # Pipeline stage info, timestamps
```

### Manifest Format

```python
@dataclass
class BundleManifest:
    bundle_id: str              # Unique ID
    timestamp: datetime
    cogant_version: str
    source_language: str
    repo_root: Path
    
    files: dict[str, FileMetadata]  # Path -> metadata
    
    # Integrity
    total_size: int
    file_count: int
    checksums: dict[str, str]   # Path -> SHA256
    
    # Provenance
    pipeline_stages: list[StageMetadata]
    provenance: dict[str, Any]
    
    # Quality
    validation_score: float     # 0.0-100.0
    error_count: int
    warning_count: int

@dataclass
class FileMetadata:
    path: Path
    format: ExportFormat
    size: int
    checksum: str
    created_at: datetime
    schema_version: str
```

## Common Usage Patterns

### Export to All Formats

```python
from cogant.export.formats import MultiFormatExporter
from cogant.export.bundle import ExportFormat, ExportConfig
from pathlib import Path

exporter = MultiFormatExporter()

manifest = exporter.export_to_all(
    graph=program_graph,
    mappings=semantic_mappings,
    output_dir=Path("output/export"),
    formats=[
        ExportFormat.JSON,
        ExportFormat.GRAPHML,
        ExportFormat.PARQUET,
        ExportFormat.PNG,
        ExportFormat.MERMAID,
    ]
)

print(f"Exported to: {manifest.bundle_id}")
for path, meta in manifest.files.items():
    print(f"  {path}: {meta.size} bytes, {meta.checksum[:8]}")
```

### Export with Custom Configuration

```python
from cogant.export.bundle import BundleExporter, ExportConfig

exporter = BundleExporter()
config = ExportConfig(
    formats=[ExportFormat.JSON, ExportFormat.GRAPHML],
    output_dir="output",
    prefix="my_project",
    overwrite=False  # Don't overwrite existing files
)

manifest = exporter.export(
    graph=program_graph,
    config=config
)

print(f"Manifest: {manifest}")
```

### Export Graph to Specific Format

```python
from cogant.export.graphml import GraphMLExporter
from cogant.export.json_schema import JSONSchemaExporter

# GraphML for visualization tools
graphml_exporter = GraphMLExporter()
graphml_exporter.export_graph(program_graph, "output/graph.graphml")

# JSON Schema for API documentation
schema_exporter = JSONSchemaExporter()
schema = schema_exporter.export_schema(program_graph)
with open("output/schema.json", "w") as f:
    json.dump(schema, f, indent=2)
```

### Export with Provenance Tracking

```python
from cogant.export.bundle import BundleExporter

exporter = BundleExporter()

# Track which stage produced each fact
provenance = {
    "graph_source": "static + dynamic",
    "translation_rules": 22,
    "confidence_threshold": 0.8,
    "pipeline_duration": 2.5,  # seconds
}

manifest = exporter.export(
    graph=program_graph,
    provenance=provenance,
    output_dir="output"
)

# Manifest includes provenance
print(manifest.provenance)
```

### Batch Export from Multiple Runs

```python
from cogant.export.formats import MultiFormatExporter
from pathlib import Path

exporter = MultiFormatExporter()

# Export results from multiple analyses
for project in ["project_a", "project_b", "project_c"]:
    graph = analyze_project(project)
    manifest = exporter.export_to_all(
        graph=graph,
        output_dir=Path(f"output/{project}"),
        formats=[ExportFormat.JSON, ExportFormat.PARQUET]
    )
    print(f"{project}: {manifest.file_count} files")
```

### Validate and Export

```python
from cogant.export.bundle import BundleExporter
from cogant.validate.validator import Validator

# Validate before export
validator = Validator()
score = validator.score(program_graph)
print(f"Validation score: {score}/100")

# Export with validation metadata
exporter = BundleExporter()
manifest = exporter.export(
    graph=program_graph,
    validation_score=score,
    output_dir="output"
)
```

## Export Workflows

### "I want to analyze this codebase in Gephi"
1. Run: `cogant translate --project myproject`
2. Export to GraphML: `cogant export --format graphml`
3. Open in Gephi, run layout + community detection algorithms
4. Visualize with Gephi's rendering

### "I want to build a dashboard for my graph"
1. Export to JSON: `cogant export --format json`
2. Use JSON as data source in frontend (React, Vue, etc.)
3. Render with D3.js, Cytoscape, or custom visualization

### "I want Parquet for analytics/warehouse"
1. Export to Parquet: `cogant export --format parquet`
2. Load into DuckDB/Snowflake/BigQuery for SQL analysis
3. Run queries on nodes, edges, metadata

### "I want all possible exports at once"
1. Export to all: `cogant export --format all`
2. Outputs: JSON, GraphML, Parquet, SVG, PNG, PDF, Mermaid, DOT, JSONLINES
3. Pick formats you need; ignore rest

### "I want to preserve full provenance and validate integrity"
1. Export with provenance: `cogant export --with-provenance`
2. manifest.json includes pipeline stages, timestamps, checksums
3. Verify checksums later with: `cogant validate-bundle manifest.json`

## Responsibilities & Coordination

### Core Responsibilities
- Serialize artifacts to 9+ formats (JSON, GraphML, Parquet, SVG, PNG, PDF, Mermaid, DOT, JSONLINES)
- Generate bundle manifests with file inventory and checksums
- Preserve metadata, provenance, and confidence scores
- Support multi-format batch export in single call
- Validate integrity via checksums
- Graceful fallback if external dependencies (graphviz, PyArrow) unavailable

### Input Sources
- **graph/** — ProgramGraph for serialization
- **translate/** — SemanticMappings (HIDDEN_STATE, OBSERVATION, ACTION, POLICY roles)
- **statespace/** — StateSpaceModel (A/B/C/D matrices)
- **validate/** — ValidationReport with scores and findings
- **viz/** — PNG/PDF/SVG visualizations

### Output Sinks
- **Disk**: Bundle directory with organized files
- **Users**: Data scientists, visualization tools (Gephi, yEd), web dashboards
- **Downstream systems**: Data warehouses (Parquet), APIs (JSON), wikis (Mermaid)

### Guarantees
- **Deterministic**: same input → same checksums
- **Integrity**: manifest checksums prevent silent corruption
- **Compatibility**: GraphML works in Gephi/yEd/Cytoscape; JSON in web apps
- **Provenance**: all exports include source/timestamp/stage info
- **Graceful degradation**: unavailable dependencies don't break export

## How to Extend

### Add a New Export Format

1. Create new exporter class: `py/cogant/export/my_format.py`
```python
class MyFormatExporter:
    def export_graph(self, graph: ProgramGraph, output_path: Path) -> Path:
        """Export graph to my format."""
        pass
```

2. Add format to `ExportFormat` enum in `formats.py`
3. Wire into `MultiFormatExporter.export_to_all()` switch statement
4. Add tests with sample graphs and validation

### Add Format-Specific Validation

1. Extend `BundleExporter` to validate format-specific constraints
2. Check file size limits, schema validation, roundtrip integrity
3. Document validation rules in docstrings

### Add Custom Metadata to Exports

1. Extend `BundleManifest` fields (or add nested metadata dict)
2. Update all exporters to include new metadata
3. Document how downstream tools consume metadata

### Support Streaming Export (Large Graphs)

1. Implement streaming version for Parquet/JSONLINES/GraphML
2. Write in chunks to avoid memory bloat
3. Test on 100k+ node graphs

## Performance Notes

- **JSON export**: ~1-10s (serialization + writing)
- **GraphML export**: ~2-30s (XML generation)
- **Parquet export**: ~1-20s (columnar compression)
- **SVG export**: ~5-60s (graphviz layout + rendering, optional)
- **Bundle manifest generation**: ~100ms
- **Checksum computation**: ~100-500ms (SHA256)

For graphs > 100k nodes, prefer Parquet (most efficient).

## See Also

- `py/cogant/export/README.md` — module overview
- `py/cogant/graph/` — provides ProgramGraph to export
- `py/cogant/translate/` — provides SemanticMappings to export
- `py/cogant/statespace/` — provides matrices to export
- `py/cogant/viz/` — provides visualizations to export
