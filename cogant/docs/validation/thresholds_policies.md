## Thresholds & Policies

### Default Thresholds

```yaml
validation:
  # Coverage
  coverage_min: 0.95
  coverage_warning: 0.9

  # Confidence
  confidence_min: 0.6
  confidence_warning: 0.5

  # Consistency
  max_warnings: 10
  max_errors: 5

  # Performance
  max_memory_mb: 2048
  max_duration_seconds: 3600
```

### Custom Thresholds

```yaml
validation:
  thresholds:
    coverage_min: 0.90  # Accept 90% coverage
    confidence_min: 0.7  # Stricter confidence requirement
    max_warnings: 20    # Allow more warnings
```
