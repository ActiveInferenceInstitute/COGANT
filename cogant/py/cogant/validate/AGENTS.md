# Agents — py/cogant/validate

## Owner
Quality Assurance & Validation

## What Is the Validate Module

The `validate/` module performs **end-to-end schema, integrity, and provenance validation** of the intermediate representations (IR) produced by earlier pipeline stages. It is stage 8 of the 10-stage COGANT pipeline. Given a `ProgramGraph`, `StateSpaceModel`, `ProcessModel`, and optional provenance records, this module:

1. **Validates Schema** — checks that all node/edge/variable types are recognized; validates cardinality and domain constraints
2. **Checks Integrity** — ensures structural consistency (no dangling references, valid transitions, sound factorization)
3. **Verifies Provenance** — confirms that evidence is tracked for all extracted elements; identifies gaps
4. **Generates Report** — produces structured ValidationReport with categorized issues, severity levels, and remediation guidance

A ValidationReport is the **quality gate before export and deployment**: it certifies that the model is structurally sound and has sufficient evidence for each component.

## Pipeline Integration

```
stage 7: gnn/               → GNN Bundle (model.gnn.md, matrices, state_space.json, etc.)
    ↓
stage 8: validate/          → ValidationReport (errors, warnings, coverage_score, confidence_score)
    ↓
stage 9: export/            → Final artifacts (PDFs, deployment bundles, dashboards)
    ↓
stage 10: scoring/          → Drift detection + quality metrics
```

The validate module is the **final quality checkpoint before release**. All bundles and artifacts depend on passing validation.

## Core Components

### ValidationIssue (schema_check.py)

Represents a single validation finding.

**Fields:**
- `id` — unique issue identifier (e.g., "SCHEMA_001", "INTEGRITY_042")
- `severity` — one of:
  - `ERROR` — blocking issue; model is invalid
  - `WARNING` — non-blocking concern; model usable but may be incorrect
  - `INFO` — informational; no action required
- `category` — issue type (e.g., "SCHEMA", "INTEGRITY", "PROVENANCE", "CONFIDENCE", "COVERAGE")
- `message` — human-readable problem description
- `affected_ids` — `list[str]` of node/variable/factor IDs involved
- `recommendation` — suggested remediation (optional; e.g., "Add type annotation to variable X")

### SchemaValidator (schema_check.py)

Validates that all IR objects conform to declared schemas.

**Validation Checks:**

On **ProgramGraph**:
- All node IDs are unique
- All nodes have recognized `kind` (FUNCTION, CLASS, VARIABLE, etc.)
- All edges have recognized `edge_type` (READS, WRITES, CALLS, etc.)
- Edge source/target nodes exist
- Node locations (line ranges) are valid (start <= end)
- All imports resolve to known modules (or logged as external)
- Symbol names are non-empty and valid identifiers

On **StateSpaceModel**:
- All variable IDs are unique
- All variables have recognized `var_type` (BOOLEAN, DISCRETE, CONTINUOUS, etc.)
- All observation modalities reference existing nodes
- All actions reference valid variable IDs in effects
- All transitions have valid source/target state tuples
- All likelihoods reference existing variables
- All preferences have non-empty scope lists
- Matrix dimensions are consistent (A: |observations| × |states|, B: |states| × |actions|, etc.)

On **ProcessModel**:
- All factor IDs are unique
- All factors reference valid variables
- All messages (edges) have recognized types
- Factor graph is acyclic (no cycles in message-passing)
- All message dimensions match node expectations

**Key Methods:**
- `validate_program_graph(graph) -> list[ValidationIssue]` — check graph schema
- `validate_state_space(state_space) -> list[ValidationIssue]` — check state space schema
- `validate_process_model(process) -> list[ValidationIssue]` — check process schema
- `get_issues() -> list[ValidationIssue]` — all issues collected
- `get_errors() -> list[ValidationIssue]` — filter to ERROR severity
- `get_warnings() -> list[ValidationIssue]` — filter to WARNING severity
- `is_valid() -> bool` — True iff no ERROR-severity issues

### IntegrityChecker (integrity.py)

Verifies internal consistency of IR objects.

**Consistency Checks:**

On **ProgramGraph**:
- No isolated nodes (all nodes have at least one edge)
- No orphaned edges (all edges reference existing nodes)
- Call graph is acyclic or has documented cycles
- Import graph has no circular dependencies (or flagged as INFO for self-tests)
- Data flow is consistent with control flow (no reads before definition)
- Type annotations are consistent with inferred types (warn if mismatches)

On **StateSpaceModel**:
- All observation modalities are reachable (observable variables are in some action's effects or direct reads)
- All actions are reachable (at least one policy can select each action)
- All variables appear in at least one transition or observation
- Likelihood distribution parameters are valid (e.g., probabilities in [0, 1], positive covariances)
- Preference weights are non-negative
- Time regime is consistent with temporal structure:
  - If SYNCHRONOUS, no async markers allowed
  - If ASYNCHRONOUS, no synchronous barriers required
  - If EVENT_DRIVEN, all edges must have event triggers
- Factorization is valid: independent factors do not share variables

On **ProcessModel**:
- All factors have at least one message
- Message dimensions match factor node expectations
- No factor has circular internal dependencies
- All probability potentials sum to valid distributions

**Key Methods:**
- `check_program_graph(graph) -> list[ValidationIssue]` — consistency checks on graph
- `check_state_space(state_space) -> list[ValidationIssue]` — consistency checks on state space
- `check_process_model(process) -> list[ValidationIssue]` — consistency checks on process
- `get_issues() -> list[ValidationIssue]` — all issues collected
- `is_valid() -> bool` — True iff no ERROR-severity issues

### ProvenanceChecker (provenance_check.py)

Tracks and verifies evidence for all extracted elements.

**ProvenanceGap** — NamedTuple indicating missing evidence:
- `element_id` — the element (node, variable, factor) lacking evidence
- `element_type` — "NODE", "VARIABLE", "FACTOR", "EDGE", "PREFERENCE"
- `message` — explanation (e.g., "Variable extracted without type annotation or assignment analysis")
- `severity` — "ERROR" (no evidence), "WARNING" (weak evidence), "INFO" (speculative)

**Provenance Records** — dictionary: `{element_id: [list of evidence objects]}`

Each evidence object tracks:
- `source_type` — "ANNOTATION", "ASSIGNMENT", "TYPE_INFERENCE", "HEURISTIC"
- `source_location` — file and line number
- `confidence` — ConfidenceLevel (DEFINITE, HIGH, MEDIUM, LOW, UNCERTAIN)
- `details` — arbitrary metadata

**Key Methods:**
- `check_graph_provenance(graph) -> list[ProvenanceGap]` — verify all nodes have evidence
- `check_state_space_provenance(state_space) -> list[ProvenanceGap]` — verify all variables have evidence
- `get_gaps() -> list[ProvenanceGap]` — all gaps found
- `get_coverage_percentage(total_elements) -> float` — [0.0, 100.0] ratio of elements with evidence
- `merge_records(other_records)` — combine multiple provenance dictionaries
- `add_record(element_id, evidence_object)` — add evidence for an element

### ValidationReport (report.py)

Comprehensive validation result with metadata and guidance.

**Fields:**
- `id` — unique report identifier (e.g., "VAL_20240413_abc123")
- `schema_name` — name of the target schema (e.g., "pymcts", "pomdp")
- `validated_at` — ISO8601 timestamp of validation
- `model_id` — ID of the model being validated
- `issues` — `list[ValidationIssue]` of all findings
- `is_valid` — boolean; True iff no ERROR issues
- `coverage_score` — [0.0, 100.0] percentage of elements with evidence
- `confidence_score` — [0.0, 100.0] average extraction confidence across elements
- `summary` — one-line summary (e.g., "Valid: 47/47 variables, avg confidence 94%")
- `details` — `dict[str, Any]` with breakdown by category:
  - `error_count`, `warning_count`, `info_count` — issue counts
  - `schema_issues`, `integrity_issues`, `provenance_issues` — grouped findings
  - `variable_confidence_histogram` — distribution of confidence levels
  - `matrix_dimensions` — A/B/C/D shape info

### ReportGenerator (report.py)

Orchestrates validation and generates reports.

**Key Methods:**
- `__init__(program_graph, state_space_model, process_model, schema_name)` — initialize with IRs
- `generate(provenance_records=None) -> ValidationReport` — main entry; returns full report
- `export_to_dict(report) -> dict[str, Any]` — serialize to JSON-compatible dict
- `export_to_json_string(report) -> str` — serialize to JSON string with pretty-printing

**Algorithm (pseudocode):**
```
1. validator = SchemaValidator()
   schema_issues = validator.validate_program_graph(graph)
                 + validator.validate_state_space(state_space)
                 + validator.validate_process_model(process)

2. checker = IntegrityChecker()
   integrity_issues = checker.check_program_graph(graph)
                    + checker.check_state_space(state_space)
                    + checker.check_process_model(process)

3. provenance_checker = ProvenanceChecker(provenance_records)
   provenance_issues = provenance_checker.check_graph_provenance(graph)
                     + provenance_checker.check_state_space_provenance(state_space)

4. all_issues = schema_issues + integrity_issues + provenance_issues
   is_valid = len([i for i in all_issues if i.severity == "ERROR"]) == 0

5. coverage_score = provenance_checker.get_coverage_percentage(total_elements)
   confidence_score = average_confidence(all_variables_and_edges)

6. return ValidationReport(
     id=generate_id(),
     issues=all_issues,
     is_valid=is_valid,
     coverage_score=coverage_score,
     confidence_score=confidence_score,
     summary=format_summary(...)
   )
```

## Data Representations

### Example: Full Validation Workflow

```python
from cogant.validate import (
    SchemaValidator, IntegrityChecker, ProvenanceChecker, ReportGenerator
)

# Given: graph, state_space, process_model from earlier stages
# Optional: provenance_records = {element_id: [evidence, ...]}

# 1. Schema validation
schema_validator = SchemaValidator()
schema_issues = (
    schema_validator.validate_program_graph(graph) +
    schema_validator.validate_state_space(state_space) +
    schema_validator.validate_process_model(process)
)
print(f"Schema issues: {len(schema_issues)}")
for issue in schema_validator.get_errors():
    print(f"  ERROR: {issue.id} - {issue.message}")

# 2. Integrity checking
integrity_checker = IntegrityChecker()
integrity_issues = (
    integrity_checker.check_program_graph(graph) +
    integrity_checker.check_state_space(state_space) +
    integrity_checker.check_process_model(process)
)
print(f"Integrity issues: {len(integrity_issues)}")
for issue in integrity_checker.get_issues():
    if issue.severity == "ERROR":
        print(f"  {issue.severity}: {issue.category} - {issue.message}")

# 3. Provenance verification
provenance_records = {
    "var_request_id": [
        {"source_type": "ANNOTATION", "confidence": "DEFINITE", ...},
    ],
    "var_status": [
        {"source_type": "ASSIGNMENT", "confidence": "HIGH", ...},
    ],
}
provenance_checker = ProvenanceChecker(provenance_records)
provenance_gaps = (
    provenance_checker.check_graph_provenance(graph) +
    provenance_checker.check_state_space_provenance(state_space)
)
coverage = provenance_checker.get_coverage_percentage(total_elements=100)
print(f"Provenance coverage: {coverage:.1%}")

# 4. Generate comprehensive report
report_gen = ReportGenerator(graph, state_space, process, schema_name="pymcts")
report = report_gen.generate(provenance_records=provenance_records)

print(f"\n=== Validation Report ===")
print(f"Valid: {report.is_valid}")
print(f"Coverage: {report.coverage_score:.1f}%")
print(f"Confidence: {report.confidence_score:.1f}%")
print(f"Summary: {report.summary}")
print(f"\nIssues ({len(report.issues)} total):")
for issue in report.issues[:5]:
    print(f"  [{issue.severity}] {issue.category}/{issue.id}: {issue.message}")
    if issue.recommendation:
        print(f"      → {issue.recommendation}")

# 5. Export
json_str = report_gen.export_to_json_string(report)
with open("validation_report.json", "w") as f:
    f.write(json_str)
```

### Example: Categorized Issue Inspection

```python
from cogant.validate import ReportGenerator

report = report_gen.generate()

# Filter by severity
errors = [i for i in report.issues if i.severity == "ERROR"]
warnings = [i for i in report.issues if i.severity == "WARNING"]

print(f"Errors: {len(errors)}, Warnings: {len(warnings)}")

# Filter by category
schema_issues = [i for i in report.issues if i.category == "SCHEMA"]
integrity_issues = [i for i in report.issues if i.category == "INTEGRITY"]
provenance_issues = [i for i in report.issues if i.category == "PROVENANCE"]

print(f"\nBy category:")
print(f"  Schema: {len(schema_issues)}")
print(f"  Integrity: {len(integrity_issues)}")
print(f"  Provenance: {len(provenance_issues)}")

# Get recommendations
actionable = [i for i in report.issues if i.recommendation]
print(f"\nActionable remediation: {len(actionable)} items")
for issue in actionable[:3]:
    print(f"  {issue.message}")
    print(f"    → {issue.recommendation}")
```

## Integration with Downstream Stages

1. **Export** (stage 9) — only exports bundles that have `is_valid=True` and `confidence_score > threshold`
2. **Scoring** (stage 10) — uses coverage and confidence scores for drift detection
3. **Quality Gates** — CI/CD pipelines can enforce `confidence_score >= 85.0` and `coverage_score >= 95.0`

## Responsibilities & Coordination

### Core Responsibilities
- Validate schemas of ProgramGraph, StateSpaceModel, ProcessModel against declared types
- Check structural consistency (no dangling references, valid transitions, sound factorization)
- Verify provenance/evidence tracking for all extracted elements
- Generate comprehensive ValidationReport with categorized issues and remediation guidance
- Support severity filtering (ERROR/WARNING/INFO) and category filtering (SCHEMA/INTEGRITY/PROVENANCE)
- Track coverage and confidence scores
- Export reports to JSON and dict formats

### Coordination
- **Input**: ProgramGraph (from graph/), StateSpaceModel (from statespace/), ProcessModel (from process/), optional provenance_records
- **Output**: ValidationReport (with detailed findings, coverage, confidence scores)
- **Consumed by**: GNN Validator (stage 7), Export pipelines (stage 9), Quality gates, CI/CD systems
- **Configuration**: schema_name (target schema type, e.g., "pymcts", "pomdp")
- **No mutable state**: Reports are immutable after generation; checkers are reusable

## How to Extend

### Add New Schema Validation Rule
1. Create check method in SchemaValidator: `def validate_X(...) -> list[ValidationIssue]:`
2. Call new method from main validation flow
3. Return issues with unique IDs, clear messages, and affected_ids
4. Test on fixtures and known-bad cases

### Add Integrity Check
1. Create check method in IntegrityChecker: `def check_property_X(...) -> list[ValidationIssue]:`
2. Register in main validation flow
3. Provide remediation recommendations where possible
4. Document expected behavior in comments

### Track New Provenance Types
1. Extend provenance record schema with new `source_type` enum value
2. Update ProvenanceChecker to recognize new types in coverage calculation
3. Add validation rules to check for minimal evidence thresholds
4. Document source type in provenance schema

### Add Issue Categories
1. Extend ValidationIssue.category enum with new value
2. Update ReportGenerator.generate() to categorize new issue types
3. Add filtering/grouping logic in report details
4. Test on fixtures

## Error Handling & Diagnostics

All validators follow a consistent error handling pattern:

```python
try:
    issues = validator.validate_graph(graph)
except Exception as e:
    logger.error(f"Validation failed: {e}")
    # Return generic error issue
    return [ValidationIssue(
        id="VALIDATION_EXCEPTION",
        severity="ERROR",
        category="VALIDATION",
        message=f"Internal validation error: {e}",
        affected_ids=[],
        recommendation="Contact support or file a bug report."
    )]
```

- Graph traversal errors → logged, validation continues
- Missing attributes → treated as schema violations
- Circular dependencies → flagged as INFO (may be intentional in tests)
- Confidence aggregation errors → defaults to 50.0

## Validation Thresholds

Bundles are considered **publishable** (safe to ship downstream) when:
- `is_valid == True` (no ERROR issues)
- `coverage_score >= 95.0` (95% of elements have evidence)
- `confidence_score >= 85.0` (average confidence is HIGH or better)

Use in CI/CD gates:
```yaml
validate:
  min_coverage: 95.0
  min_confidence: 85.0
  allow_warnings: true
  allow_info: true
```

## See Also

- `py/cogant/validate/README.md` — module-level overview
- `py/cogant/statespace/` — produces StateSpaceModel consumed by validate/
- `py/cogant/process/` — produces ProcessModel consumed by validate/
- `py/cogant/gnn/validator.py` — GNN bundle validation (separate from IR validation)
- `py/cogant/export/` — exports only after validation passes
- `py/cogant/scoring/` — uses validation results for quality metrics
