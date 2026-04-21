# GNN Semantic Roles Ontology

## Overview

This document defines the semantic roles assigned to program entities for GNN training. Roles form a taxonomy suitable for both supervised and unsupervised learning tasks.

## Role Hierarchy

```
ProgramEntity
├── Functional
│   ├── FunctionDef       (Function definition)
│   ├── FunctionCall      (Function invocation)
│   ├── MethodDef         (Class method)
│   ├── MethodCall        (Method invocation)
│   └── Polymorphism      (Virtual dispatch)
├── Data
│   ├── VariableDef       (Variable definition)
│   ├── VariableUse       (Variable reference)
│   ├── FieldAccess       (Object field access)
│   ├── DataAccess        (Generic data access)
│   └── Constant          (Literal constant)
├── Type
│   ├── TypeDef           (Class/struct/interface)
│   ├── TypeRef           (Type usage)
│   ├── GenericParam      (Generic type parameter)
│   ├── TypeConstraint    (Type bound/constraint)
│   └── Interface         (Abstract contract)
├── Control
│   ├── ControlFlow       (Branch/loop)
│   ├── ErrorHandling     (Exception handling)
│   └── ErrorFlow         (Error propagation)
├── Module
│   ├── ModuleDef         (Package/namespace)
│   ├── ModuleImport      (Import statement)
│   └── DependencyInject  (Injected dependency)
├── Advanced
│   ├── Inheritance       (Class hierarchy)
│   ├── Implementation    (Interface realization)
│   ├── Instantiates      (Generic instantiation)
│   ├── Parameterizes     (Parameterization)
│   └── Overrides         (Method override)
├── Non-functional
│   ├── LoggingStmt       (Log statement)
│   ├── ConfigParam       (Configuration)
│   ├── TestCode          (Test code)
│   ├── Documentation     (Comments/docs)
│   ├── Annotation        (Decorator/attribute)
│   ├── PerfCritical      (Performance-sensitive)
│   └── SecurityCritical  (Security-sensitive)
└── Unknown               (Unclassified)
```

## Role Definitions

### Functional Roles

#### FunctionDef
**Definition**: Function definition (function declaration with body)
**GNN Use Case**: Node type for supervised learning on function properties
**Examples**: `def process()`, `int main()`, `function doWork() {}`
**Typical Features**:
- Arity (number of parameters)
- Estimated complexity
- Return type
- Side effects
- Call frequency

#### FunctionCall
**Definition**: Invocation of a function/method
**GNN Use Case**: Indicates control flow dependency
**Examples**: `process()`, `obj.method()`, `func.apply()`
**Typical Features**:
- Target function
- Argument count
- Is recursive
- Is tail call

#### MethodDef
**Definition**: Function defined inside a class/struct
**GNN Use Case**: Member-of-class relationship
**Examples**: `class A { def method(self): ... }`
**Typical Features**:
- Access modifier (public, private, protected)
- Is static
- Is abstract
- Is override

#### MethodCall
**Definition**: Invocation of a method on an object
**GNN Use Case**: Object-oriented dispatch edge
**Examples**: `obj.method()`, `self.func()`
**Typical Features**:
- Object type
- Method name
- Dynamic vs static dispatch
- Virtual vs non-virtual

#### Polymorphism
**Definition**: Virtual method dispatch or interface call
**GNN Use Case**: Indicates potential call targets (edge to all possible methods)
**Examples**: `animal.sound()` where `sound()` is overridden in multiple subclasses
**Typical Features**:
- Possible targets
- Dispatch mechanism (virtual table, vtable, etc.)
- Probability of each target

### Data Roles

#### VariableDef
**Definition**: Variable definition or assignment
**GNN Use Case**: Data source node
**Examples**: `x = 5`, `data = []`, `let count = 0`
**Typical Features**:
- Type annotation
- Initial value
- Scope (local, global, parameter, field)
- Immutability

#### VariableUse
**Definition**: Reference to a variable
**GNN Use Case**: Data consumer node
**Examples**: `print(x)`, `return data`, `process(x, y)`
**Typical Features**:
- Variable being referenced
- Context (read, write, read-write)
- Nested depth

#### FieldAccess
**Definition**: Access to object field/property
**GNN Use Case**: Object decomposition edge
**Examples**: `obj.field`, `obj.property`, `self.x`
**Typical Features**:
- Object type
- Field name
- Access mode (get, set, both)

#### DataAccess
**Definition**: Generic data access (including array/dictionary access)
**GNN Use Case**: Data dependency
**Examples**: `list[i]`, `dict["key"]`, `data.field`
**Typical Features**:
- Collection type
- Index/key type
- Access mode

#### Constant
**Definition**: Literal constant value
**GNN Use Case**: Leaf node in data flow
**Examples**: `42`, `"hello"`, `true`, `None`, `3.14`
**Typical Features**:
- Literal type
- Value (if small)
- First use location

### Type Roles

#### TypeDef
**Definition**: Type/class/struct/interface definition
**GNN Use Case**: Type taxonomy node
**Examples**: `class MyClass:`, `struct Point {}`, `interface Iterator`
**Typical Features**:
- Kind (class, struct, enum, interface, type alias)
- Modifier (abstract, final, sealed)
- Generic parameters
- Superclasses/interfaces

#### TypeRef
**Definition**: Reference to a type (in annotation, cast, etc.)
**GNN Use Case**: Type dependency edge
**Examples**: `x: int`, `(MyClass)obj`, `List<String>`
**Typical Features**:
- Type being referenced
- Generic instantiation (if applicable)
- Nullable vs non-nullable

#### GenericParam
**Definition**: Type parameter in generic definition
**GNN Use Case**: Parametric polymorphism node
**Examples**: `<T>`, `<K, V>`, `<T extends Comparable>`
**Typical Features**:
- Parameter name
- Bounds/constraints
- Variance (covariant, contravariant, invariant)

#### TypeConstraint
**Definition**: Constraint on type parameter
**GNN Use Case**: Type bound relationship
**Examples**: `<T extends Number>`, `<T: Hashable>`, `where T: Clone`
**Typical Features**:
- Constrained type parameter
- Bound type(s)
- Constraint kind (upper bound, lower bound, equality)

#### Interface
**Definition**: Abstract interface/protocol
**GNN Use Case**: Contract definition node
**Examples**: `interface Drawable`, `protocol Codable`, `ABC` (Python)
**Typical Features**:
- Method signatures
- Required methods
- Optional methods

### Control Roles

#### ControlFlow
**Definition**: Control flow structure (if, loop, switch)
**GNN Use Case**: Program path representation
**Examples**: `if condition:`, `while loop:`, `for each:`
**Typical Features**:
- Branch type (if, while, for, switch)
- Condition complexity
- Branch taken probability (if dynamic)

#### ErrorHandling
**Definition**: Exception handling (try/catch, error handling code)
**GNN Use Case**: Error path modeling
**Examples**: `try: ... except:`, `try { } catch (Exception e)`
**Typical Features**:
- Exception type(s) handled
- Handler complexity
- Re-throw vs swallow

#### ErrorFlow
**Definition**: Edge indicating error propagation
**GNN Use Case**: Exception path edge
**Examples**: `function_calls error_handler_on_failure`
**Typical Features**:
- Exception type
- Propagation vs handling
- Error message available

### Module Roles

#### ModuleDef
**Definition**: Module/namespace/package definition
**GNN Use Case**: Hierarchical grouping node
**Examples**: `package com.example`, `module math`, `namespace std`
**Typical Features**:
- Module name
- Public exports
- Dependencies

#### ModuleImport
**Definition**: Import of external module/dependency
**GNN Use Case**: External dependency edge
**Examples**: `import os`, `import java.util.*`, `using System`
**Typical Features**:
- Module being imported
- Imported items
- Alias (if applicable)

#### DependencyInject
**Definition**: Dependency injection point
**GNN Use Case**: Configuration dependency edge
**Examples**: `@Inject private Service service`, `@autowired`
**Typical Features**:
- Injected type
- Injection mechanism (constructor, field, setter)
- Optional vs required

### Advanced Roles

#### Inheritance
**Definition**: Class inheritance relationship
**GNN Use Case**: Type hierarchy edge
**Examples**: `class B extends A`, `class B(A):`
**Typical Features**:
- Superclass
- Method overrides
- Field inheritance

#### Implementation
**Definition**: Interface implementation
**GNN Use Case**: Contract satisfaction edge
**Examples**: `class A implements B`, `impl Trait for Type`
**Typical Features**:
- Interface being implemented
- Implemented methods
- Partial vs complete implementation

#### Instantiates
**Definition**: Generic type instantiation
**GNN Use Case**: Type specialization edge
**Examples**: `List<String>`, `Box<T>`, `Dict[str, int]`
**Typical Features**:
- Generic type
- Type arguments
- Bounds checking

#### Parameterizes
**Definition**: Parametric relationship
**GNN Use Case**: Generic edge
**Examples**: Function takes `T` parameter
**Typical Features**:
- Parameter count
- Parameter constraints
- Instantiation count

#### Overrides
**Definition**: Method override in subclass
**GNN Use Case**: Polymorphic relationship edge
**Examples**: `def method(self):` in subclass overrides parent
**Typical Features**:
- Overridden method
- Signature compatibility
- Annotation (@Override)

### Non-functional Roles

#### LoggingStmt
**Definition**: Logging statement
**GNN Use Case**: Instrumentation node (often filtered)
**Examples**: `print(x)`, `logger.info()`, `console.log()`
**Typical Features**:
- Log level (debug, info, warn, error)
- Message
- Conditional vs unconditional

#### ConfigParam
**Definition**: Configuration parameter
**GNN Use Case**: Configuration value node
**Examples**: `TIMEOUT = 30`, `config.get("API_KEY")`
**Typical Features**:
- Config key
- Default value
- Type

#### TestCode
**Definition**: Test or specification code
**GNN Use Case**: Often excluded from primary analysis
**Examples**: `def test_foo():`, `@Test void testBar()`
**Typical Features**:
- Test type (unit, integration, end-to-end)
- Assertion count
- Setup/teardown

#### Documentation
**Definition**: Documentation or comment
**GNN Use Case**: Feature source for ML
**Examples**: `"""This function does..."""`, `// TODO: refactor`
**Typical Features**:
- Comment type (doc, TODO, FIXME, explanation)
- Length
- Code reference

#### Annotation
**Definition**: Annotation/decorator/attribute
**GNN Use Case**: Metadata node
**Examples**: `@property`, `@deprecated`, `#[attribute]`
**Typical Features**:
- Annotation name
- Parameters
- Semantic meaning

#### PerfCritical
**Definition**: Performance-sensitive code region
**GNN Use Case**: Optimization target marker
**Examples**: Loop body, hot function, tight loop
**Typical Features**:
- Criticality level (high, medium)
- Estimated call frequency
- Performance requirement

#### SecurityCritical
**Definition**: Security-sensitive code region
**GNN Use Case**: Security analysis target
**Examples**: Authentication, encryption, input validation
**Typical Features**:
- Security concern type (crypto, auth, injection, etc.)
- Threat level
- Validation performed

#### Unknown
**Definition**: Unable to classify
**GNN Use Case**: Placeholder
**Typical Features**: None

## Role Assignment Guidelines

### Confidence-Based Assignment

Assign roles with confidence scores:

```
node.role = FunctionDef           # confidence = 1.0 (syntactic)
node.role = FunctionCall          # confidence = 0.9 (explicitly in source)
node.role = Polymorphism          # confidence = 0.6 (inferred from type)
node.role = Unknown               # confidence = 0.0 (no evidence)
```

### Multi-Role Handling

Some entities may have multiple roles (use edge to represent):

```
@property
def value(self):      # BOTH: MethodDef (confidence=1.0)
  return self._v      #      AND FieldAccess (confidence=0.9)
```

Represent as two nodes or one node with multiple role edges.

### Language-Specific Mappings

#### Python
- `@property` → FIELD_ACCESS (not MethodCall)
- `@decorator` → ANNOTATION + target node
- `async def` → MethodDef + async marker
- `*args, **kwargs` → VariableDef with variadic marker

#### Java
- `@Override` → Overrides edge
- `abstract method` → Interface node (contract) + MethodDef
- `interface` → Interface node
- `class` → TypeDef node

#### JavaScript/TypeScript
- `async function` → MethodDef + async marker
- `Promise<T>` → TypeRef + async context
- `() => {}` → FunctionDef (arrow function)
- `export` → ModuleExport annotation

#### Rust
- `impl Trait for Type` → Implementation edge
- `pub fn` → MethodDef + visibility marker
- `<T>` → GenericParam node
- `where T: Bound` → TypeConstraint edge

## GNN Features from Roles

Each role suggests default feature extraction:

| Role | Typical Features |
|------|------------------|
| FunctionDef | arity, complexity, return type, docstring present |
| FunctionCall | arg count, target type, frequency, is_recursive |
| VariableDef | type, immutable, scope, initialized |
| TypeDef | kind, abstract, final, superclass count |
| MethodDef | visibility, static, virtual, override |
| ControlFlow | type, nesting level, branch probability |
| ErrorHandling | exception types, complexity, location |

## Training Dataset Construction

### Supervised Learning

Use roles as labels for node classification:
- Features: subgraph structure, textual features, type information
- Labels: role assignment
- Metric: accuracy, F1, macro-F1 (for imbalanced classes)

### Unsupervised Learning

Use roles as regularization or validation:
- Clustering nodes, validate clusters match role categories
- Link prediction, predict edges matching typical role patterns
- Community detection, align with module/namespace structure

### Transfer Learning

Pre-train role classifier on large codebase, fine-tune on domain-specific code.

## References

- [Translation Rules](../mappings/code-to-gnn.md)
- [IR Reference](../schemas/ir-reference.md)
- [Program Graph IR](../rfc/0002-ir-schemas.md)
