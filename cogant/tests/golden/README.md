# Golden Tests

Golden test fixtures and expected outputs for regression detection.

## Purpose

Golden tests ensure export stability by comparing pipeline output against saved "golden" expectations.

## Golden files

Stored in this directory:
- python-service-bundle.json — Expected bundle output for python-service fixture
- python-service-graph.yaml — Expected graph structure
- python-service-validation-report.md — Expected validation output

## Updating golden files

When intentionally changing output format or behavior:

```bash
pytest tests/integration/test_golden.py --update-golden
```

Then review and commit the changed .json / .yaml / .md files.

## Workflow

1. Run pipeline on fixture repo
2. Capture output (bundle, graph, validation report)
3. Compare against golden files
4. If mismatch:
   - If intentional: update golden (requires review)
   - If unintentional: fix the bug

## Golden fixtures

Fixtures run against:
- examples/python-service/ — Python service example
- examples/workflow-engine/ — Workflow engine example
- Additional small test repos as needed
