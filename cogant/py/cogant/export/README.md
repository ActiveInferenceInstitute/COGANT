# Export

Orchestrates full export to multiple formats with manifest creation. Writes GNN markdown, JSON, GraphML, Parquet, HTML, and complete provenance bundles with checksums and metadata.

## API

BundleExporter orchestrates full export to multiple formats and creates a complete bundle with manifest. Initialize with program_graph, state_space_model, process_model, semantic_mappings, and output_dir, then call export() with optional format list. Produces BundleManifest with bundle_id, schema_name, created_at, files dict, checksums dict, and metadata.

TypedExporter exports program graphs in typed JSON, DOT, Cytoscape.js, and adjacency matrix formats with full type information preserved.

GraphMLExporter exports graphs in GraphML format for visualization tools (Gephi, Cytoscape, yEd).

ParquetExporter exports graphs as columnar PyArrow tables for ML training and data analysis.

## Usage

```python
from cogant.export import BundleExporter
from pathlib import Path

exporter = BundleExporter(
    graph, state_space, process_model, 
    mappings, output_dir=Path("output")
)

# Export to all formats
output_path = exporter.export()

# Or specific formats
output_path = exporter.export(["json", "graphml", "html"])

print(f"Exported to: {output_path}")
```
