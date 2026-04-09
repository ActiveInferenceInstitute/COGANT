## Rule Set Management

### Built-in Rule Sets

```yaml
rule_sets:
  default:
    version: 1.0.0
    language: python
    language_version: 3.9+
    rules:
      - rule_fn_def_001
      - rule_fn_call_001
      - rule_var_def_001
      - rule_type_def_001
      - ... (all core rules)

  strict:
    version: 1.0.0
    language: python
    language_version: 3.9+
    rules:
      - rule_fn_def_001
      - rule_fn_call_001
      # High confidence rules only

  experimental:
    version: 1.0.0
    language: python
    language_version: 3.9+
    rules:
      - rule_fn_def_001
      - rule_fn_call_001
      - heuristic_implicit_call_001  # Includes heuristics
      - heuristic_inferred_dep_001
```

### Switch Rule Set

```yaml
# cogant.yaml
translation:
  rule_set: strict  # Use high-confidence rules only
```

