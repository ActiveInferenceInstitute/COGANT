# Specs — Technical Specifications

Canonical specifications, schemas, and design documents.

## Contents
- **architecture/** — Pipeline design, system architecture, data flow
- **schemas/** — Graph schema, export schema, GNN format specification
- **mappings/** — Code-to-GNN mappings, cross-language symbol translation
- **ontology/** — Semantic type system and semantic tags
- **rfc/** — Request for Comments, design proposals, major decisions

## Structure

Each spec is a Markdown document with:
- Status (Draft, Review, Accepted, Deprecated)
- Authors and reviewers
- Rationale and design decisions
- Examples and test cases
- Cross-references to code

## RFC Process

1. Create rfc/NNNN-description.md
2. Submit for review (Architecture Lead assigns reviewers)
3. Iterate with feedback
4. Accept and implement (or defer/reject)
5. Update relevant specs and documentation

## Versioning

Specs are versioned with their content. Breaking changes increment version number.

## Dependencies
- None; specs are canonical sources of truth
