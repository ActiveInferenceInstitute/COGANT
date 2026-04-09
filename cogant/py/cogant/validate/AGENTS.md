# Agents — py/cogant/validate

## Owner
Quality Assurance and Validation Lead

## Responsibilities
Run schema, integrity, and provenance validation on all IR objects. Generate comprehensive validation reports. Identify and categorize validation issues. Track coverage and confidence metrics.

## Key Responsibilities
- Run SchemaValidator on program graph and state space models
- Run IntegrityChecker to verify structural consistency
- Run ProvenanceChecker to verify evidence tracking completeness
- Generate ValidationReport with is_valid, coverage_score, confidence_score
- Categorize issues by severity and type for user remediation

## How to Extend
Add new validation methods to SchemaValidator for domain-specific types. Extend IntegrityChecker with additional consistency checks. Create specialized issue categories in ValidationIssue. Add new confidence aggregation strategies in ReportGenerator.

## Coordination
- Consumes: ProgramGraph, StateSpaceModel, ProcessModel from compile/extract
- Produces: ValidationReport consumed by export/, users
- Works with: provenance/ for evidence tracking, scoring/ for quality metrics
