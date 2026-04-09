## Translation Rules

Translation rules map (NodeKind, SemanticRole) → target semantic role.

**Example rule**:
```python
Rule: FUNCTION + FUNCTION_DEF → FUNCTION_DEF
Confidence: 1.0 (syntactic)
Conditions:
  - type_name is not None
  - provenance.type == "SourceCode"
Transformations:
  - extract_signature: Parse signature
  - compute_complexity: Estimate complexity
  - identify_side_effects: Annotate side effects
```

Rules are:
- **Composable**: Apply multiple rules, aggregate results
- **Extensible**: User can define custom rules
- **Traceable**: Log all rule matches in provenance
- **Versioned**: Rules evolve with language versions

See [Translation Rules](../specs/mappings/code-to-gnn.md) for full reference.

