## Security Testing

### SAST (Static Analysis)

**Rust**: `cargo clippy --all-targets --all-features`  
**Python**: `bandit`, `pylint`, `mypy`

**CI**: Fail on HIGH severity issues

### Dependency Scanning

**Tool**: `cargo audit`  
**CI**: Block on known vulnerabilities

### DAST (Dynamic Analysis - Future)

Plan for v0.2:
- Fuzzing with malformed inputs
- Memory profiling for leaks
- Resource limit testing

### Penetration Testing

Plan for v1.0:
- External security audit
- Bug bounty program
- Threat model refinement

