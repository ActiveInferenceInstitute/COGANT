## Threat Model

### Assets

1. **Analyzed Codebase**: Proprietary/sensitive source code
2. **Analysis Results**: Generated IRs, graphs, insights
3. **Pipeline Process**: Integrity of analysis engine
4. **User System**: Development machine, CI/CD pipeline

### Attack Vectors

#### 1. Code Injection via Malicious Codebase

**Threat**: Attacker inserts malicious code that exploits COGANT parser.

**Mitigations**:
- **No execution**: COGANT never executes user code
- **Parser limits**: Timeouts on parsing (default: 30s per file)
- **Memory limits**: Bounded allocations (prevent DoS)
- **Input validation**: Reject files >100MB
- **Sandboxing**: Parse in isolated subprocess (future)

**Risk Level**: Low (execution-free)

#### 2. Information Disclosure

**Threat**: COGANT output leaks sensitive information about code.

**Mitigations**:
- **Local processing**: No transmission by default
- **Anonymization**: Option to strip names, docs
- **Access control**: Respect file permissions
- **Secure deletion**: Clear sensitive data from memory
- **Audit logging**: Track all operations (if enabled)

**Risk Level**: Medium (design mitigates, user must configure)

#### 3. Dependency Compromise

**Threat**: Malicious library in Rust/Python dependencies.

**Mitigations**:
- **Pin versions**: All dependencies pinned in lock file
- **Audit supply chain**: Regular dependency review
- **Minimal deps**: Keep dependency count low
- **Verify signatures**: Verify critical crates (future)
- **Vendor code**: Critical Rust crates vendored

**Risk Level**: Low-Medium (managed via CI/CD)

#### 4. Plugin Malware

**Threat**: User loads malicious plugin that steals code/results.

**Mitigations**:
- **Plugin sandbox**: Run plugins in separate process (future)
- **Permission model**: Declare what plugin needs (future)
- **Code review**: Document plugin development security
- **Trust model**: Plugins trusted by default (user responsibility)

**Risk Level**: Medium (user responsibility)

#### 5. Configuration Injection

**Threat**: Malicious config file changes pipeline behavior.

**Mitigations**:
- **Schema validation**: Strict YAML schema enforcement
- **Type checking**: All config values type-checked
- **Path validation**: Reject paths with `../` or absolute paths
- **Explicit whitelist**: Only recognized config options
- **Immutability**: Config read-only after validation

**Risk Level**: Low

