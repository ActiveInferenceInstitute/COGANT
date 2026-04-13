## Error Handling

```python
try:
    session = Session.from_target("./repo")
    session.extract_static()
except FileNotFoundError as e:
    print(f"Target not found: {e}")
except RuntimeError as e:
    print(f"Analysis failed: {e}")

# Check bundle errors
if bundle.errors:
    for error in bundle.errors:
        print(f"Error: {error}")
```

