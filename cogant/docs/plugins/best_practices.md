## Best Practices

### Performance

- Minimize memory allocations in hot paths
- Use generators for large result sets
- Cache expensive computations
- Profile with large projects

### Compatibility

- Target Python 3.11+ (see root [`pyproject.toml`](https://github.com/docxology/cogant/blob/main/cogant/pyproject.toml))
- Don't assume import order
- Handle missing optional dependencies gracefully
- Follow COGANT's error handling patterns

### Documentation

- Document configuration options
- Include code examples
- Specify language versions supported
- List dependencies clearly

### Testing

- Unit test all code paths
- Test with real codebases
- Include regression tests
- Document test setup
