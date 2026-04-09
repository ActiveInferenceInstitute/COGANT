# Agents — py/cogant/provenance

## Owner
Evidence and Audit Trail Lead

## Responsibilities
Manage provenance records linking extracted elements to source evidence. Track extraction method, evidence type, confidence, and location. Support confidence aggregation and evidence queries.

## Key Responsibilities
- Run ProvenanceTracker to add records for all extracted elements
- Record evidence_type, extraction_method, confidence, and metadata
- Support target-based lookup of all supporting evidence
- Compute aggregate confidence scores from provenance records
- Enable filtering by evidence type and date range

## How to Extend
Add new evidence_type values (e.g., "runtime_trace", "type_annotation"). Extend metadata schema for domain-specific evidence attributes. Create specialized confidence aggregation strategies (weighted average, Bayesian, etc.).

## Coordination
- Consumes: Extraction events from all modules during pipeline execution
- Produces: ProvenanceRecord objects queried by validate/, export/
- Works with: validate/ for integrity checking, export/ for bundle serialization
