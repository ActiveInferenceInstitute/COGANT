# Generated robustness degradation table (do not edit — re-run harness.py)

| Transform | Category | Min role similarity | Status |
|---|---|---:|---|
| `reformat` | semantics_preserving | 1.0000 | ROBUST |
| `insert_comments` | semantics_preserving | 1.0000 | ROBUST |
| `insert_dead_code` | semantics_preserving | 1.0000 | ROBUST |
| `rename_locals` | semantics_preserving | 1.0000 | ROBUST |
| `reorder_methods` | semantics_preserving | 1.0000 | ROBUST |
| `swap_if_branches` | semantics_preserving | 1.0000 | ROBUST |
| `outline_first_function` | sensitivity_probe | 1.0000 | PRESERVED |
| `drop_half_definitions` | negative_control | 0.7882 | DETECTED |
