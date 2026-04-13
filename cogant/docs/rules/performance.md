## Performance

### Rule Application Order

**Fast Rules First** (syntactic checks):
- `rule_fn_def_001` (syntactic)
- `rule_type_def_001` (syntactic)
- `rule_has_type_001` (syntactic)

**Medium Rules** (simple heuristics):
- `rule_fn_call_001` (explicit in source)
- `rule_var_def_001` (source location available)

**Slow Rules** (complex analysis):
- `rule_polymorphism_001` (type hierarchy analysis)
- `heuristic_implicit_call_001` (reflection detection)

### Benchmark (100K functions)

- Core rules: <5s (4 cores)
- With heuristics: <10s (4 cores)

