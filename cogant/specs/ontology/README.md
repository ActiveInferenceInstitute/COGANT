# Ontology — Semantic Type System

Semantic type definitions and role assignment rules for COGANT.

## Contents
- gnn-roles.md — GNN node and edge role types, semantic tags

## Semantic type system

Types include:
- **Node roles**: function, class, variable, module, parameter, return-value, field
- **Edge roles**: calls, defines, uses, imports, type-uses, data-flow
- **Semantic tags**: synchronous, asynchronous, recursive, polymorphic, inferred

## Hierarchy

- Symbol (abstract)
  - Callable (functions, methods, lambdas, classes with __call__)
  - Variable (local, global, field)
  - Module
- Type (abstract)
  - PrimitiveType
  - AggregateType (class, struct, enum, union)
  - GenericType (parameterized)

## Tag semantics

Tags express confidence, semantics, or special properties:
- inferred — derived from usage, not explicit
- polymorphic — overloaded or generic
- external — defined outside this codebase
- recursive — calls itself (directly or transitively)
