## Dependency Security

### Rust Dependencies

Core dependencies with security significance:

| Crate | Version | Audit | Risk |
|-------|---------|-------|------|
| serde | 1.0 | ✓ | Low |
| petgraph | 0.6 | ✓ | Low |
| pyo3 | 0.22 | ✓ | Medium* |
| uuid | 1.6 | ✓ | Low |
| thiserror | 1.0 | ✓ | Low |

\* PyO3 bridges Python ↔ Rust; use latest for security patches

### Python Dependencies

| Package | Version | Use | Risk |
|---------|---------|-----|------|
| serde_json | 1.0 | Serialization | Low |
| PyYAML | 6.0 | Config parsing | Medium** |

\** Requires safe mode (no code execution)

### Update Policy

1. **Security patches**: Apply immediately (patch release)
2. **Critical updates**: Evaluate, apply in next release
3. **Regular updates**: Monthly dependency review
4. **Deprecation**: Phase out unsupported versions

