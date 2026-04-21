## Infer from source
source = """
def add(x: int, y: int) -> int:
    return x + y

name: str = "Alice"
count = 42
items = [1, 2, 3]
mapping = {"a": 1}
"""
type_infos = inferencer.infer_types_from_source(source, Path("example.py"))

for info in type_infos:
    print(f"Symbol: {info.symbol_name} ({info.symbol_kind})")
    print(f"  Type: {info.annotation or info.inferred_type}")
    print(f"  Confidence: {info.confidence}")
```

##### TypeInfo Structure:

```python
@dataclass
class TypeInfo:
    symbol_id: str             # Symbol ID
    symbol_name: str
    symbol_kind: str           # function/variable/etc.
    inferred_type: Optional[str]
    annotation: Optional[str]  # Explicit annotation
    is_mutable: bool
    confidence: float          # 0.0 to 1.0
    metadata: Dict[str, Any]
```

#### DataFlowAnalyzer

**Location:** `cogant.static.dataflow.DataFlowAnalyzer`

Analyzes data flow within functions and across module.

##### Features:
- Track variable assignments (writes)
- Track variable reads and uses
- Detect mutations (augmented assignments, method calls on objects)
- Build data flow edges with context information
- Handle parameter passing and return statements

##### Usage:

```python
from cogant.static import DataFlowAnalyzer
from pathlib import Path

analyzer = DataFlowAnalyzer(repo_root=Path("."))
