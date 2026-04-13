# Security

> Threat model, secure coding practices, dependency posture, and disclosure process for COGANT. Read this section if you are running COGANT against untrusted source code, deploying it in a regulated environment, or reporting a vulnerability.

## Contents

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | High-level security posture of COGANT | Beginner |
| [Threat Model](threat_model.md) | Adversaries, assets, and trust boundaries | Intermediate |
| [Security Controls](security_controls.md) | Concrete controls implemented in the codebase | Intermediate |
| [Privacy Protections](privacy_protections.md) | What data COGANT reads, retains, and emits | Intermediate |
| [Dependency Security](dependency_security.md) | Supply-chain posture and dependency policy | Intermediate |
| [Cryptography](cryptography.md) | Crypto primitives and where they are used | Advanced |
| [Secure Coding Practices](secure_coding_practices.md) | Coding standards enforced in the repository | Intermediate |
| [Security Testing](security_testing.md) | Static, dynamic, and fuzzing test posture | Advanced |
| [Security Release Process](security_release_process.md) | How security fixes are released | Reference |
| [Compliance](compliance.md) | Compliance posture and applicable frameworks | Reference |
| [Security Documentation](security_documentation.md) | Inventory of security-relevant docs | Reference |
| [Future Improvements](future_improvements.md) | Planned hardening work | Reference |
| [Responsible Disclosure](responsible_disclosure.md) | How to report a vulnerability | Beginner |
| [Python Package Audit (Module Exports)](python_package_audit_module_exports.md) | Audited public surface of the Python package | Advanced |
| [See Also](see_also.md) | Cross-links to related documentation | Beginner |
| [References](references.md) | External references cited in this section | Reference |

## Recommended Reading Order

1. [Overview](overview.md) — establish the baseline posture.
2. [Threat Model](threat_model.md) — understand which adversaries COGANT defends against.
3. [Security Controls](security_controls.md) and [Secure Coding Practices](secure_coding_practices.md) — see how the threats are mitigated.
4. [Privacy Protections](privacy_protections.md) — learn what data leaves the local machine.
5. [Dependency Security](dependency_security.md) and [Cryptography](cryptography.md) — supply chain and crypto posture.
6. [Security Testing](security_testing.md) — assurance evidence for the controls.
7. [Responsible Disclosure](responsible_disclosure.md) — required reading before reporting an issue.
8. [Security Release Process](security_release_process.md) and [Compliance](compliance.md) — operational and audit context.

## Related modules

- [../architecture/README.md](../architecture/README.md) — architecture against which the threat model is stated.
- [../validation/README.md](../validation/README.md) — validators backing several security claims.
- [../roadmap/deprecation_policy.md](../roadmap/deprecation_policy.md) — how security-driven deprecations are staged.
- [../reference/README.md](../reference/README.md) — public Python package surface audited here.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
