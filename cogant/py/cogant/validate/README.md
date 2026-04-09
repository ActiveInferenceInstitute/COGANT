# Validate

Validates IR objects, checks structural integrity, verifies provenance coverage, and compiles comprehensive validation reports. Identifies schema compliance issues, dangling references, orphaned nodes, and confidence anomalies.

## API

SchemaValidator validates IR objects against Pydantic schemas. Call validate_program_graph(), validate_state_space(), or validate_process_model() to check type consistency, required fields, and value ranges. Returns list of ValidationIssue objects.

ValidationIssue represents a single validation problem with severity (error/warning/info), category (schema/integrity/provenance/coverage), message, affected_ids, and recommendation.

IntegrityChecker verifies structural integrity: node ID uniqueness, edge endpoint validity, reference validity, orphaned nodes, and confidence values in [0, 1]. Detects dangling references and cycles.

ProvenanceChecker verifies source attribution completeness and ProvenanceGap represents missing evidence.

ReportGenerator orchestrates all validators and produces a ValidationReport with is_valid boolean, coverage_score (0-1), confidence_score (0-1), summary, and detailed results.

## Usage

```python
from cogant.validate import SchemaValidator, IntegrityChecker, ReportGenerator

# Validate individual models
schema_validator = SchemaValidator()
issues = schema_validator.validate_program_graph(graph)

integrity_checker = IntegrityChecker()
issues += integrity_checker.check_program_graph(graph)

# Generate comprehensive report
report_gen = ReportGenerator(graph, state_space, process_model, "my_schema")
report = report_gen.generate()

print(f"Valid: {report.is_valid}")
print(f"Coverage: {report.coverage_score}")
print(f"Issues: {len(report.issues)}")
```
