# AGENTS.md — Security module

Threat model, secure-coding practices, dependency posture, cryptography
notes, privacy protections, disclosure process, and compliance posture
for COGANT. This module is the primary source for anyone running COGANT
against untrusted source code, deploying it in a regulated environment,
or reporting a vulnerability.

## Purpose and ownership

Security documentation is a legal and reputational surface, not just a
reference. Every claim in this module must be defensible. Owned jointly
by the security triage contact and whoever last shipped a control that
affects the posture.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC and recommended reading order | Any time a file is added, removed, or renamed |
| `AGENTS.md` | This file — maintenance rules | When ownership, triage workflow, or the "every claim defensible" policy changes |
| `overview.md` | High-level security posture | When the posture changes at a headline level |
| `threat_model.md` | Adversaries, assets, and trust boundaries | When a new trust boundary or asset is introduced |
| `security_controls.md` | Concrete controls implemented in the codebase | When a control is added, removed, or substantially modified |
| `privacy_protections.md` | What data COGANT reads, retains, and emits | When data handling changes (new inputs, new outputs, new retention) |
| `dependency_security.md` | Supply-chain posture and dependency policy | When dependency pinning, vendoring, or audit policy changes |
| `cryptography.md` | Crypto primitives and where they are used | When crypto primitives or key handling changes |
| `secure_coding_practices.md` | Coding standards enforced in the repository | When a new standard is adopted or removed |
| `security_testing.md` | Static, dynamic, and fuzzing posture | When testing tools or coverage change |
| `security_release_process.md` | How security fixes are released | When the release process changes |
| `compliance.md` | Compliance posture and applicable frameworks | When a new framework applies or a claimed one no longer does |
| `security_documentation.md` | Inventory of security-relevant docs | When files in this module are reorganized |
| `future_improvements.md` | Planned hardening work | When a hardening item is scheduled, completed, or cut |
| `responsible_disclosure.md` | How to report a vulnerability | When the triage contact, PGP key, or SLA changes |
| `python_package_audit_module_exports.md` | Audited public surface of the Python package | When a new public symbol is added or removed |
| `see_also.md` | Cross-links to related modules | When link targets move |
| `references.md` | External references cited in this section | When new references are cited or links rot |

## Adding a new doc

1. Decide which of the four groups (posture / controls / operations /
   references) the new page belongs to.
2. Use a short, lower-case, underscore-separated slug.
3. Open with a `> **Status**` banner stating whether the document is
   normative (the project commits to what is written here) or informative
   (description of current state, subject to change).
4. Every security claim should be either (a) backed by a link to code or
   tests in the repository, or (b) explicitly labeled "aspirational". No
   unbacked claims.
5. Add a row to the `## Contents` table in `README.md` and mention the
   page in `## Recommended Reading Order` if it belongs in the spine.

## Known gotchas

- `responsible_disclosure.md` is the public disclosure contract. Changes
  to the triage contact, PGP key, or SLA have to be mirrored in the
  repository-root `SECURITY.md` in the same PR.
- `compliance.md` lists frameworks the project explicitly claims to
  address. Do not add a framework unless there is a written policy and
  controls elsewhere in this module that back the claim.
- Recorded security advisories, when they happen, go into
  `security_release_process.md` or a dated sibling page — **not** inline
  in `threat_model.md` or `overview.md`, which stay forward-looking.
