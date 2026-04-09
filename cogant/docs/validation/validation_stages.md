## Validation Stages

### Coverage Validation

Measures what percentage of code was analyzed.

```json
{
  "coverage": {
    "lines_analyzed": 14950,
    "lines_total": 15000,
    "coverage_percent": 99.67,
    "uncovered_files": ["tests/mock_data.py"],
    "coverage_by_file": {
      "src/main.py": 1.0,
      "src/utils.py": 0.95,
      "tests/mock_data.py": 0.0
    }
  }
}
```

**Target**: ≥95% coverage  
**Warning**: <90% coverage  
**Error**: <70% coverage  

### Confidence Validation

Analyzes distribution of confidence scores.

```json
{
  "confidence": {
    "mean": 0.92,
    "median": 0.95,
    "min": 0.3,
    "max": 1.0,
    "distribution": {
      "CERTAIN_1.0": 280,
      "HIGH_0.8_0.99": 35,
      "MEDIUM_0.6_0.8": 4,
      "LOW_0.0_0.6": 1
    },
    "low_confidence_nodes": [
      {
        "id": "node_xyz",
        "name": "complex_function",
        "confidence": 0.3,
        "reason": "Dynamic dispatch detected"
      }
    ]
  }
}
```

**Target**: Mean ≥0.85  
**Flags**: Confidence <0.6  

### Consistency Validation

Checks for structural issues.

```json
{
  "consistency": {
    "duplicate_nodes": 0,
    "orphaned_nodes": 0,
    "disconnected_components": 1,
    "cycles_detected": true,
    "self_loops": 0,
    "issues": [
      {
        "level": "WARNING",
        "message": "Orphaned node fn_unused has no incoming/outgoing edges",
        "node_id": "node_123"
      }
    ]
  }
}
```

### Schema Validation

Validates against IR schemas.

```json
{
  "schema": {
    "version": "1.0.0",
    "valid": true,
    "violations": []
  }
}
```

### Reproducibility Validation

Verifies that the same input produces the same output.

```json
{
  "reproducibility": {
    "cogant_version": "0.1.0",
    "input_hash": "sha256:abc123...",
    "config_hash": "sha256:def456...",
    "output_hash": "sha256:xyz789...",
    "timestamp": "2024-10-01T12:00:00Z",
    "reproducible": true
  }
}
```

