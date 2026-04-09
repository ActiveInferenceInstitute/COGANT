# Provenance

Creates, stores, and queries provenance records linking evidence to extracted elements. Enables tracing of how elements were extracted and supports confidence assessment.

## API

ProvenanceTracker manages provenance records linking evidence to extracted elements. Initialize with no arguments, then call add_record() to record evidence for any extracted element (node, edge, variable, action, etc.). Query records with get_records_for_target() or get_record(record_id).

ProvenanceRecord represents a single piece of evidence with target_id (what was extracted), target_type (node/edge/variable/action/etc.), evidence_type (code_pattern/test/annotation/inference/metadata), evidence_location (file path), confidence (0-1), extraction_method (name of algorithm), timestamp, and metadata dict.

ProvenanceTracker.compute_target_confidence() aggregates confidence across all provenance records for a target. get_evidence_summary() returns aggregate statistics. Methods support filtering by evidence type and date range.

## Usage

```python
from cogant.provenance import ProvenanceTracker, ProvenanceRecord

tracker = ProvenanceTracker()

# Add evidence linking to an extracted variable
tracker.add_record(
    target_id="var_x",
    target_type="variable",
    evidence_type="code_pattern",
    evidence_location="src/main.py:42",
    extraction_method="StateVariableExtractor",
    confidence=0.85,
    metadata={"pattern": "hidden_state annotation"}
)

# Query records for a target
records = tracker.get_records_for_target("var_x")
confidence = tracker.compute_target_confidence("var_x")
```
