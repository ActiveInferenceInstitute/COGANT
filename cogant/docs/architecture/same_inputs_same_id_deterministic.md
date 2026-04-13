## Same inputs = same ID (deterministic)
assert module_id == resolver.get_id(
    entity_type="module",
    repo_uri="https://github.com/example/repo",
    path="src/mymodule.py",
    qualified_name="myapp.core"
)
```

**Cache Statistics:**
```python
stats = resolver.get_statistics()
