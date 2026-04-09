# Agents — py/cogant/export

## Owner
Export and Serialization Lead

## Responsibilities
Orchestrate multi-format export of bundles and models. Write format-specific files (JSON, GraphML, Parquet, HTML) with manifest and checksums. Preserve provenance and confidence metadata throughout serialization.

## Key Responsibilities
- Run BundleExporter to export to multiple formats
- Generate BundleManifest with file inventory and checksums
- Call format-specific exporters (TypedExporter, GraphMLExporter, ParquetExporter)
- Create output directory with organized file structure
- Preserve all metadata and provenance information

## How to Extend
Add new format support by creating new exporter classes. Extend BundleExporter.export() to support additional format strings. Add format-specific validation and checksumming.

## Coordination
- Consumes: ProgramGraph, StateSpaceModel, ProcessModel, semantic_mappings
- Produces: Bundle directory with manifest and multiple format exports
- Works with: viz/ for HTML generation, validate/ for integrity checks
