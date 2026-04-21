## Validation

Exported graphs are validated for:

1. **Structural integrity**:
   - All edge endpoints exist
   - No self-loops (unless allowed)
   - No duplicate edges

2. **Feature consistency**:
   - All features have correct dimensions
   - No NaN or Inf values
   - Values in expected ranges (0-1 for confidence)

3. **Metadata completeness**:
   - All required fields present
   - Timestamps valid
   - Checksums match

CLI and policy details: [Validation module](../validation/README.md), [`cogant validate`](../cli/README.md).

### See also

- [Overview](overview.md)
- [Reproducibility](reproducibility.md)
