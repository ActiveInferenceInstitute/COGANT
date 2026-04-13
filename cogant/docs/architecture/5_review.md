## 5. Review

```python
reviewer = ReviewManager()
for mapping in mappings:
    reviewer.add_mapping(mapping)
    if should_accept(mapping):
        reviewer.accept_mapping(mapping.id, "human")
```

See [COGANT Engine Implementation Summary](cogant_engine_implementation_summary.md) (Translation module / `ReviewManager`) and [Review process (interactive)](review_process_interactive.md).
