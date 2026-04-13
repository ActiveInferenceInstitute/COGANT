# Schemas — Type and Schema Specification

Canonical schema definitions for graph representation, exports, and types.

## Contents
- ir-reference.md — Intermediate representation schema (Graph, Node, Edge, Symbol, etc.)

## Schema specification
Defines:
- Node types: Function, Class, Variable, Module, File, etc.
- Edge types: CALLS, IMPORTS, USES, DEFINES, TYPE_USES, etc.
- Attributes: source spans, confidence, metadata
- Type system: primitive types, generics, constraints
- Provenance: audit trail, source attribution

## Versioning

Current schema version: 1.0
- Breaking changes increment major version
- New field additions are backward compatible
- Deprecations require deprecation period before removal

## Implementation
Code in py/cogant/schemas/ must implement this spec.
