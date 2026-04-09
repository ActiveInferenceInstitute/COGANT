## Extract from source
source = """
def helper(x: int) -> int:
    return x * 2

def main():
    result = helper(10)
    print(result)
    obj.method()
"""
edges = builder.extract_calls_from_source(source, Path("example.py"))

for edge in edges:
    print(f"Call: {edge.caller_name} -> {edge.callee_name}")
    print(f"  Line: {edge.line_num}")
    print(f"  Method call: {edge.is_method_call}")
    if edge.receiver:
        print(f"  Receiver: {edge.receiver}")
    print(f"  Args: {edge.args}")
```

##### CallEdge Structure:

```python
@dataclass
class CallEdge:
    id: str                    # Unique edge ID
    source_file: Path
    caller_id: str             # Symbol ID of caller
    caller_name: str
    callee_name: str
    callee_id: Optional[str]   # Symbol ID of callee (if resolved)
    line_num: int
    is_method_call: bool
    receiver: Optional[str]    # Object the method is called on
    args: List[str]            # Argument values as strings
    metadata: Dict[str, Any]
```

#### TypeInferencer

**Location:** `cogant.static.types.TypeInferencer`

Extracts type annotations and infers types from code.

##### Features:
- Extract explicit type annotations
- Infer types from literal values (list, dict, str, int, float, bool, etc.)
- Infer types from constructor calls
- Track confidence scores
- Handle function return types and variable types

##### Usage:

```python
from cogant.static import TypeInferencer
from pathlib import Path

inferencer = TypeInferencer(repo_root=Path("."))

