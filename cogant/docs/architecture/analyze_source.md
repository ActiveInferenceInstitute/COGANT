## Analyze source
source = """
def process(items):
    result = []
    for item in items:          # Read: items
        value = item * 2        # Read: item, Write: value
        result.append(value)    # Read: value, Mutate: result
    return result               # Read: result
"""
flows = analyzer.analyze_source(source, Path("example.py"))

for flow in flows:
    print(f"Flow: {flow.source_symbol} -> {flow.target_symbol}")
    print(f"  Type: {flow.edge_type}")
    print(f"  Line: {flow.line_num}")
    print(f"  Context: {flow.context}")
```

##### DataFlowEdge Structure:

```python
@dataclass
class DataFlowEdge:
    id: str                    # Unique edge ID
    source_symbol: str         # Source symbol name
    target_symbol: str         # Target symbol name
    edge_type: str             # reads/writes/mutates/depends_on
    file_path: Path
    line_num: int
    context: str               # module/function_name/class.method
    metadata: Dict[str, Any]
```

### Integration Example

Complete example showing pipeline usage from repository to code graph:

```python
from pathlib import Path
from cogant.ingest import RepoIngester
from cogant.static import (
    SymbolExtractor,
    ImportAnalyzer,
    CallGraphBuilder,
    TypeInferencer,
    DataFlowAnalyzer,
)
