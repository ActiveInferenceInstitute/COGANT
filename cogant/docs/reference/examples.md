## Examples

### Example 1: Analyze a Simple Function

**Input Code** (`main.py`):
```python
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

def main():
    result = add(5, 3)
    print(result)
```

**Generated Graph**:
- Node: `fn_add` (FUNCTION, FUNCTION_DEF, confidence=1.0)
- Node: `fn_main` (FUNCTION, FUNCTION_DEF, confidence=1.0)
- Node: `var_result` (VARIABLE, VARIABLE_DEF, confidence=0.9)
- Edge: `main` → `add` (CALLS, confidence=1.0)
- Edge: `main` → `result` (DEFINES, confidence=0.95)

### Example 2: Inheritance Hierarchy

**Input Code**:
```python
class Animal:
    def sound(self) -> str:
        pass

class Dog(Animal):
    def sound(self) -> str:
        return "Woof"
```

**Generated Roles**:
- `Animal` node: TYPE_DEF
- `Dog` node: TYPE_DEF
- `sound` in Animal: METHOD_DEF, INTERFACE
- `sound` in Dog: METHOD_DEF, OVERRIDES
- Edge Dog → Animal: INHERITS

### Example 3: State Space Extraction

Given execution traces, state space identifies:
- Observable variables (data, count, state)
- Actions (function calls, mutations)
- Transitions (feasible state changes with probability)
- Initial and accepting states

This enables GNN training for behavioral prediction.

