## Language-Specific Variants

### Python

#### Decorator Detection
- **Pattern**: Function with `@decorator`
- **Transformation**: Add `is_decorated=true`, `decorator_names=[...]`
- **Confidence boost**: +0.1

#### Generator/Coroutine
- **Pattern**: `yield` or `async def`
- **Target**: Mark COROUTINE in attributes
- **Confidence**: 1.0 (syntactic marker)

#### Property Access
- **Pattern**: `@property` method
- **Transformation**: Treat as DATA_ACCESS, not FUNCTION_CALL
- **Confidence**: 0.95

#### Class Decorator
- **Pattern**: `@dataclass`, `@enum`, etc.
- **Transformation**: Add semantic flag
- **Confidence**: 0.95

### Java

#### Interface Implementation
- **Pattern**: `implements` keyword
- **Transformation**: IMPLEMENTS edge
- **Confidence**: 1.0 (syntactic)

#### Annotation Presence
- **Pattern**: `@Annotation`
- **Transformation**: Add metadata flags
- **Confidence**: 1.0

#### Generics
- **Pattern**: `<T>`, `<K extends Comparable>`
- **Transformation**: Track constraints
- **Confidence**: 0.95

### JavaScript/TypeScript

#### Promise/Async
- **Pattern**: `async function`, `Promise<T>`
- **Transformation**: Mark COROUTINE
- **Confidence**: 1.0

#### Object Method
- **Pattern**: Method in object literal
- **Transformation**: Both FUNCTION_DEF and MEMBER_OF
- **Confidence**: 0.95

#### Dynamic Property
- **Pattern**: `obj[key]` access
- **Transformation**: LOW confidence DATA_ACCESS
- **Confidence**: 0.3

### Rust

#### Trait Implementation
- **Pattern**: `impl Trait for Type`
- **Transformation**: IMPLEMENTATION edge
- **Confidence**: 1.0

#### Generic Constraints
- **Pattern**: `where T: Bound`
- **Transformation**: TYPE_CONSTRAINT edge
- **Confidence**: 0.95

#### Unsafe Block
- **Pattern**: `unsafe { ... }`
- **Transformation**: Mark SECURITY_CRITICAL
- **Confidence**: 0.9

