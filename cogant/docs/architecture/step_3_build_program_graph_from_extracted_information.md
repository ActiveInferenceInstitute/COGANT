## Step 3: Build program graph from extracted information
print(f"\nAnalysis Results:")
print(f"  Symbols: {len(all_symbols)}")
print(f"  Imports: {len(all_imports)}")
print(f"  Calls: {len(all_calls)}")
print(f"  Type annotations: {len(all_types)}")
print(f"  Data flow edges: {len(all_flows)}")
```

### Data Structures

All modules use dataclasses for type safety and serialization support. Key structures include:

- `RepoSnapshot`: Complete repository state at ingestion time
- `PythonModule`: Parsed Python file contents
- `SymbolInfo`: Code symbol with qualified name and metadata
- `ImportEdge`: Import relationship between modules
- `CallEdge`: Function/method call relationship
- `TypeInfo`: Type information for a symbol
- `DataFlowEdge`: Data flow relationship between variables

### Error Handling

The pipeline provides graceful error handling:

- **File reading errors**: Logged, reported in `errors` field of results
- **Parse errors**: Syntax errors captured, module continues processing
- **Manifest parsing**: Unknown formats skip gracefully with warnings
- **Symbol resolution**: Unresolved references reported in metadata

### Performance Considerations

- **File checksums**: Computed on-demand via `compute_checksums` parameter
- **Import resolution**: Uses simple path-based heuristics for speed
- **Type inference**: Uses conservative heuristics for performance
- **Data flow analysis**: Simplified to avoid exponential complexity
- **AST visiting**: Selective visiting of relevant node types

### Testing

Run integration tests:

```bash
uv run pytest tests/integration/test_full_pipeline.py -v
uv run pytest tests/integration/test_gnn_package.py -v
```

All pipeline components are tested with:
- Unit-level parsing tests
- Integration tests with real code samples
- Error condition handling
- Edge case coverage
