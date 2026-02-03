# Modern Python Features Guide (3.9-3.12+)

Comprehensive reference for Python 3.9+ type system, performance, and syntax improvements.

---

## Quick Reference Table

| Feature | Python | Impact | Complexity | Priority |
|---------|--------|--------|------------|----------|
| Built-in Generics (PEP 585) | 3.9+ | None | Low | ⭐⭐⭐ Essential |
| Union Operator (PEP 604) | 3.10+ | None | Low | ⭐⭐⭐ Essential |
| Type Aliases (PEP 695) | 3.12+ | None | Low | ⭐⭐ Recommended |
| typing.Self | 3.11+ | None | Low | ⭐⭐⭐ Essential |
| typing.override | 3.12+ | None | Low | ⭐⭐⭐ Essential |
| __slots__ | 2.2+ | -40-60% memory | Medium | ⭐⭐⭐ High Impact |
| cached_property | 3.8+ | +100-1000% speed | Low | ⭐⭐⭐ High Impact |
| Pattern Matching | 3.10+ | Slight + | Medium | ⭐ Optional |

---

## 1. PEP 585 - Built-in Generic Types (Python 3.9+)

### Overview
Use built-in collection types directly as generics without importing from `typing`.

### Syntax Comparison

| Old (3.8-) | New (3.9+) |
|------------|------------|
| `from typing import List, Dict, Set, Tuple, Optional` | No import needed |
| `List[int]` | `list[int]` |
| `Dict[str, int]` | `dict[str, int]` |
| `Set[str]` | `set[str]` |
| `Tuple[float, float]` | `tuple[float, float]` |
| `Optional[str]` | Use PEP 604 instead |

### Examples

```python
# Simple types
numbers: list[int] = [1, 2, 3]
mapping: dict[str, float] = {"pi": 3.14}
unique: set[str] = {"a", "b"}
coords: tuple[float, float] = (1.0, 2.0)

# Nested generics
data: dict[str, list[tuple[int, str]]] = {
    "items": [(1, "a"), (2, "b")]
}

# Variable-length tuples
values: tuple[int, ...] = (1, 2, 3, 4, 5)

# Function signatures
def process(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}
```

### Trade-offs

| Pros ✅ | Cons ❌ |
|---------|---------|
| Simpler imports | Requires Python 3.9+ |
| Consistent naming (runtime = type hint) | Breaking change for 3.8- |
| Less verbose | Must use `from __future__ import annotations` for 3.8 |
| Better IDE support | - |
| Future-proof | - |

---

## 2. PEP 604 - Union Type Operator (Python 3.10+)

### Overview
Use `|` operator for union types instead of `Union[...]` or `Optional[...]`.

### Syntax Comparison

| Old (3.9-) | New (3.10+) |
|------------|-------------|
| `from typing import Union, Optional` | No import needed |
| `Union[int, str]` | `int \| str` |
| `Optional[str]` | `str \| None` |
| `Union[int, str, float]` | `int \| str \| float` |
| `Union[List[int], Dict[str, int]]` | `list[int] \| dict[str, int]` |

### Examples

```python
# Optional values
result: str | None = None
value: int | None = get_value()

# Multiple types
def process(data: int | float | str) -> bool:
    return isinstance(data, (int, float, str))

# Complex unions
CellType = GridCell | list[GridCell]
Response = dict[str, Any] | None
Number = int | float | complex

# Function returns
def find_item(key: str) -> dict[str, Any] | None:
    ...

# With generics
Cache = dict[str, list[int]] | dict[str, str] | None
```

### Trade-offs

| Pros ✅ | Cons ❌ |
|---------|---------|
| More readable (`str \| None` vs `Optional[str]`) | Requires Python 3.10+ |
| Mathematical notation (set theory) | Runtime evaluation (needs `__future__` for 3.9) |
| Less imports | Not a runtime operator (can't use with isinstance) |
| Symmetric and chainable | - |

### Important Notes

```python
# ✅ Type hints
def func(x: int | str) -> bool: ...

# ❌ Runtime - Use tuple for isinstance
if isinstance(value, (int, str)):  # NOT: int | str
    ...
```

---

## 3. PEP 695 - Type Aliases (Python 3.12+)

### Overview
New `type` keyword for creating type aliases with cleaner syntax.

### Syntax Comparison

| Old (3.11-) | New (3.12+) |
|-------------|-------------|
| `from typing import TypeAlias` | No import needed |
| `Coordinate: TypeAlias = tuple[float, float]` | `type Coordinate = tuple[float, float]` |
| `ID: TypeAlias = int` | `type ID = int` |
| `Data: TypeAlias = dict[str, Any]` | `type Data = dict[str, Any]` |

### Examples

```python
# Simple aliases
type UserID = int
type Username = str
type Email = str

# Complex types
type JSONValue = dict[str, Any] | list[Any] | str | int | float | bool | None
type Callback = Callable[[str], bool]
type DataSet = list[tuple[float, float]]

# Generic aliases (Python 3.12+)
type Point[T] = tuple[T, T]
type Matrix[T] = list[list[T]]

# Usage
def get_user(id: UserID) -> Username: ...
coords: Point[float] = (1.5, 2.5)
grid: Matrix[int] = [[1, 2], [3, 4]]
```

### Trade-offs

| Pros ✅ | Cons ❌ |
|---------|---------|
| Cleaner syntax | Requires Python 3.12+ |
| Explicit intent (`type` keyword) | Very new (limited adoption) |
| Better scoping | Can't mix with `TypeAlias` |
| Generic support built-in | - |
| Better IDE support | - |

### Best Practices

```python
# ✅ Use for domain-specific types
type CellID = str
type Precision = int
type AreaKM2 = float

# ✅ Use for complex nested types
type Config = dict[str, str | int | list[str]]

# ❌ Don't overuse for trivial types
type MyString = str  # Unnecessary
```

---

## 4. typing.Self (Python 3.11+)

### Overview
Type hint representing the current class type, useful for methods returning instances.

### Syntax Comparison

| Old (3.10-) | New (3.11+) |
|-------------|-------------|
| `from typing import TypeVar` | `from typing import Self` |
| `T = TypeVar('T', bound='MyClass')` | - |
| `def method(cls: type[T]) -> T: ...` | `def method(cls) -> Self: ...` |
| `def copy(self) -> "MyClass": ...` | `def copy(self) -> Self: ...` |

### Examples

```python
from typing import Self

class Builder:
    def __init__(self, name: str):
        self.name = name
        self._options: dict[str, Any] = {}

    # Factory methods
    @classmethod
    def create(cls, name: str) -> Self:
        return cls(name)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        instance = cls(data["name"])
        instance._options = data["options"]
        return instance

    # Fluent interface / builder pattern
    def with_option(self, key: str, value: Any) -> Self:
        self._options[key] = value
        return self

    def reset(self) -> Self:
        self._options.clear()
        return self

    # Copy methods
    def copy(self) -> Self:
        return self.__class__(self.name)

# Works correctly with inheritance
class EnhancedBuilder(Builder):
    def special_method(self) -> Self:
        # Returns EnhancedBuilder, not Builder!
        return self.copy()

# Usage
builder = Builder.create("test").with_option("a", 1).with_option("b", 2)
```

### Trade-offs

| Pros ✅ | Cons ❌ |
|---------|---------|
| Correct type with inheritance | Requires Python 3.11+ |
| No boilerplate (TypeVar) | Limited to self-references |
| Better IDE autocomplete | Not a real type (special form) |
| Cleaner syntax | - |
| Type-safe builder patterns | - |

### Use Cases

| Pattern | Example |
|---------|---------|
| Factory methods | `@classmethod def create(cls) -> Self: ...` |
| Fluent interfaces | `def set_value(self, v) -> Self: return self` |
| Copy/clone | `def copy(self) -> Self: ...` |
| Method chaining | `def filter(...) -> Self: ...` |

---

## 5. typing.override (Python 3.12+)

### Overview
Decorator marking methods as overriding parent class methods, enabling static verification.

### Syntax

```python
from typing import override

class Parent:
    def process(self, data: str) -> int:
        return len(data)

class Child(Parent):
    @override
    def process(self, data: str) -> int:
        return len(data) * 2
```

### What It Catches

```python
class Base:
    def method(self, x: int) -> str:
        return str(x)

class Derived(Base):
    # ❌ TYPE ERROR: Wrong return type
    @override
    def method(self, x: int) -> int:  # mypy/pyright error!
        return x

    # ❌ TYPE ERROR: Wrong parameter type
    @override
    def method(self, x: str) -> str:  # mypy/pyright error!
        return x

    # ❌ TYPE ERROR: Method doesn't exist in parent
    @override
    def methdo(self, x: int) -> str:  # Typo caught!
        return str(x)
```

### Examples

```python
from abc import ABC, abstractmethod
from typing import override

class BaseProcessor(ABC):
    @abstractmethod
    def process(self, data: str) -> int:
        ...

    def optional_hook(self) -> None:
        pass  # Optional override

class ConcreteProcessor(BaseProcessor):
    @override
    def process(self, data: str) -> int:
        return len(data)

    @override
    def optional_hook(self) -> None:
        print("Hook called")

# Combining decorators
class CachedProcessor(BaseProcessor):
    @cached_property
    @override
    def process(self, data: str) -> int:
        return expensive_operation(data)
```

### Trade-offs

| Pros ✅ | Cons ❌ |
|---------|---------|
| Catches typos at type-check time | Requires Python 3.12+ |
| Validates signatures | Only useful with type checkers |
| Self-documenting | Adds verbosity |
| Refactoring safety | Runtime no-op |
| Better IDE navigation | - |

### Best Practices

```python
# ✅ Always use for abstract method implementations
class MyClass(AbstractBase):
    @override
    def required_method(self): ...

# ✅ Use for optional parent methods
class MyClass(Base):
    @override
    def optional_hook(self): ...

# ❌ Don't use on new methods
class MyClass(Base):
    @override  # ERROR!
    def my_new_method(self): ...

# ✅ Run type checker to get benefits
# mypy --strict mymodule.py
# pyright mymodule.py
```

---

## 6. __slots__ (Python 2.2+)

### Overview
Restricts instance attributes to a fixed set, saving memory and improving performance.

### Syntax Comparison

| Without __slots__ | With __slots__ |
|-------------------|----------------|
| Instance has `__dict__` (~288 bytes) | Only defined attributes (~72 bytes) |
| Can add attributes dynamically | Fixed attributes only |
| Slower attribute access | Faster attribute access |

### Examples

```python
# Basic usage
class Point:
    __slots__ = ('x', 'y')

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

# With type hints (Python 3.10+)
class Point:
    __slots__ = ('x', 'y')
    x: float
    y: float

# Including __dict__ for flexibility
class FlexiblePoint:
    __slots__ = ('x', 'y', '__dict__')  # Fixed + dynamic

# Including __weakref__
class RefPoint:
    __slots__ = ('x', 'y', '__weakref__')

# With inheritance
class Point2D:
    __slots__ = ('x', 'y')

class Point3D(Point2D):
    __slots__ = ('z',)  # Only add new attributes

# With dataclass (Python 3.10+)
from dataclasses import dataclass

@dataclass(slots=True)
class Point:
    x: float
    y: float
```

### Memory Impact

```python
import sys

# Without __slots__
class Regular:
    def __init__(self, a, b):
        self.a = a
        self.b = b

# With __slots__
class Slotted:
    __slots__ = ('a', 'b')
    def __init__(self, a, b):
        self.a = a
        self.b = b

regular = Regular(1, 2)
slotted = Slotted(1, 2)

# Memory comparison
print(f"Regular: {sys.getsizeof(regular) + sys.getsizeof(regular.__dict__)} bytes")
# Regular: 152 bytes

print(f"Slotted: {sys.getsizeof(slotted)} bytes")
# Slotted: 72 bytes

# Memory reduction: ~53%
```

### Trade-offs

| Pros ✅ | Cons ❌ |
|---------|---------|
| 40-60% memory reduction | No dynamic attributes |
| 10-20% faster attribute access | Inheritance complexity |
| Prevents typos | No default values (use dataclass) |
| Explicit attribute declaration | Needs `__weakref__` for weak refs |
| Significant with many instances | Some libraries expect `__dict__` |

### When to Use

| Use ✅ | Don't Use ❌ |
|--------|--------------|
| Classes with many instances (1000+) | Classes needing dynamic attributes |
| Data-heavy applications | Single-instance classes |
| Known, fixed attributes | Plugin/extensible architectures |
| Performance-critical code | Small, rarely-instantiated classes |
| With dataclass for convenience | When debugging flexibility needed |

### Best Practices

```python
# ✅ Use tuple (immutable)
class Point:
    __slots__ = ('x', 'y')

# ✅ Include __dict__ if using cached_property
class MyClass:
    __slots__ = ('id', 'data', '__dict__')

    @cached_property
    def computed(self):
        return expensive_calc(self.data)

# ❌ Don't repeat parent slots
class Parent:
    __slots__ = ('a',)

class Child(Parent):
    __slots__ = ('b',)  # ✅ Only new attributes
    # __slots__ = ('a', 'b')  # ❌ Don't repeat 'a'

# ✅ Document when using __dict__
class HybridClass:
    """Fixed attributes with __dict__ for cached properties."""
    __slots__ = ('id', 'name', '__dict__')
```

---

## 7. functools.cached_property (Python 3.8+)

### Overview
Decorator that caches property results, computing once and storing the value.

### Syntax Comparison

| Manual Caching | cached_property |
|----------------|-----------------|
| Define `_cached_value = None` | No extra attributes |
| Check if cached in getter | Automatic caching |
| Store manually | Automatic storage |
| 10+ lines of code | 1 decorator |

### Examples

```python
from functools import cached_property
import time

class DataAnalysis:
    def __init__(self, data: list[float]):
        self.data = data

    @cached_property
    def mean(self) -> float:
        """Computed once, then cached."""
        print("Computing mean...")
        time.sleep(1)  # Simulate expensive operation
        return sum(self.data) / len(self.data)

    @cached_property
    def std_dev(self) -> float:
        """Uses cached mean value."""
        mean = self.mean  # Uses cached value
        return (sum((x - mean) ** 2 for x in self.data) / len(self.data)) ** 0.5

    @cached_property
    def summary(self) -> dict[str, float]:
        return {
            "mean": self.mean,
            "std_dev": self.std_dev,
            "min": min(self.data),
            "max": max(self.data)
        }

# Usage
analysis = DataAnalysis([1, 2, 3, 4, 5])
mean1 = analysis.mean  # Prints "Computing mean...", waits 1 sec
mean2 = analysis.mean  # Instant! Cached
mean3 = analysis.mean  # Still instant!

# Clear cache
del analysis.mean
mean4 = analysis.mean  # Recomputes
```

### With __slots__

```python
# ⚠️ Requires __dict__ in __slots__
class MyClass:
    __slots__ = ('data', '__dict__')  # Must include __dict__!

    def __init__(self, data):
        self.data = data

    @cached_property
    def expensive_result(self):
        return expensive_operation(self.data)

# ❌ Without __dict__
class BadClass:
    __slots__ = ('data',)  # Missing __dict__

    @cached_property
    def expensive_result(self):  # TypeError at runtime!
        return expensive_operation(self.data)
```

### Trade-offs

| Pros ✅ | Cons ❌ |
|---------|---------|
| Automatic caching | Requires `__dict__` |
| Clean syntax | Per-instance (no sharing) |
| Lazy evaluation | No expiration |
| Thread-safe (3.8+) | No size limit |
| Easy to clear (`del`) | Included in pickle |
| No boilerplate | - |

### Best Practices

```python
# ✅ Use for expensive computations
class DataProcessor:
    @cached_property
    def processed_data(self):
        return expensive_transformation(self.raw_data)

# ✅ Use for derived values
class Circle:
    def __init__(self, radius: float):
        self.radius = radius

    @cached_property
    def area(self) -> float:
        return 3.14159 * self.radius ** 2

    @cached_property
    def circumference(self) -> float:
        return 2 * 3.14159 * self.radius

# ❌ Don't use for changing values
class Counter:
    def __init__(self):
        self.count = 0

    @cached_property  # ❌ BAD!
    def doubled(self):
        return self.count * 2  # Won't update when count changes

# ✅ Clear cache when data changes
class MutableData:
    def __init__(self, values: list[int]):
        self._values = values

    @cached_property
    def sum(self) -> int:
        return sum(self._values)

    def update(self, values: list[int]):
        self._values = values
        if 'sum' in self.__dict__:
            del self.__dict__['sum']  # Clear cache

# ✅ Document expensive operations
class Analysis:
    @cached_property
    def result(self) -> float:
        """
        Expensive calculation (~2 seconds).
        Cached after first access.
        """
        return super_expensive_operation()
```

---

## 8. Pattern Matching (match/case) (Python 3.10+)

### Overview
Structural pattern matching for dispatch and destructuring, more powerful than switch/case.

### Basic Syntax

```python
# Simple value matching
match status:
    case "active":
        process_active()
    case "inactive":
        process_inactive()
    case "pending":
        process_pending()
    case _:  # Default
        raise ValueError(f"Unknown status: {status}")

# Multiple values
match value:
    case 0:
        return "zero"
    case 1 | 2 | 3:  # OR pattern
        return "small"
    case _:
        return "large"
```

### Advanced Patterns

```python
# Sequence patterns
match point:
    case [x, y]:
        return f"2D: ({x}, {y})"
    case [x, y, z]:
        return f"3D: ({x}, {y}, {z})"
    case _:
        return "Unknown"

# Dictionary patterns
match config:
    case {"type": "local", "path": path}:
        return load_local(path)
    case {"type": "remote", "url": url}:
        return load_remote(url)
    case {"type": t}:
        raise ValueError(f"Unknown type: {t}")

# Object patterns
match obj:
    case Point(x=0, y=0):
        return "origin"
    case Point(x=0):
        return f"on y-axis at y={obj.y}"
    case Point(y=0):
        return f"on x-axis at x={obj.x}"
    case Point():
        return f"point at ({obj.x}, {obj.y})"

# Guards (conditions)
match value:
    case x if x < 0:
        return "negative"
    case 0:
        return "zero"
    case x if x > 0:
        return "positive"

# Capture patterns
match data:
    case [first, *rest]:
        print(f"First: {first}, Rest: {rest}")
    case []:
        print("Empty")

# Nested patterns
match event:
    case {"type": "click", "position": [x, y]}:
        handle_click(x, y)
    case {"type": "key", "key": key} if key.isalpha():
        handle_letter(key)
```

### Real-World Examples

```python
# API response handling
match response:
    case {"status": 200, "data": data}:
        return process_success(data)
    case {"status": 404}:
        raise NotFoundError()
    case {"status": code, "error": msg}:
        raise APIError(code, msg)

# Command dispatch
match command:
    case ["create", resource, *args]:
        create_resource(resource, args)
    case ["delete", resource]:
        delete_resource(resource)
    case ["list"]:
        list_resources()
    case _:
        print(f"Unknown command: {command}")

# Type dispatch
match value:
    case int(x):
        process_int(x)
    case str(s):
        process_string(s)
    case list(items):
        process_list(items)
    case _:
        raise TypeError(f"Unsupported type: {type(value)}")

# State machine
match (state, event):
    case ("idle", "start"):
        return "running"
    case ("running", "pause"):
        return "paused"
    case ("paused", "resume"):
        return "running"
    case ("running" | "paused", "stop"):
        return "idle"
    case _:
        return state  # No transition
```

### Trade-offs

| Pros ✅ | Cons ❌ |
|---------|---------|
| More readable than if/elif | Requires Python 3.10+ |
| Powerful destructuring | Learning curve |
| Type narrowing (type checkers) | Can be verbose for simple cases |
| Exhaustiveness checking | Limited use cases |
| Guards for conditions | - |

### When to Use

| Use ✅ | Don't Use ❌ |
|--------|--------------|
| Dispatch on discrete values | Simple boolean checks |
| Parsing structured data | Range comparisons |
| Multiple related conditions | Single if/else |
| Destructuring sequences/dicts | Complex boolean logic |
| State machines | - |

### Comparison

```python
# ❌ DON'T: Simple boolean
match is_valid:
    case True: do_something()
    case False: do_else()

# ✅ DO: Simple if
if is_valid:
    do_something()
else:
    do_else()

# ✅ DO: Multiple dispatch
match command:
    case "start": start()
    case "stop": stop()
    case "restart": restart()

# ❌ DON'T: Range checks
match temp:
    case t if t < 0: print("cold")
    case t if t < 20: print("cool")

# ✅ DO: Use if/elif
if temp < 0:
    print("cold")
elif temp < 20:
    print("cool")
```

---

## Migration Strategy

### Python 3.9 Projects

```python
# Enable modern syntax
from __future__ import annotations

# ✅ Available
list[int]                    # PEP 585
dict[str, int]              # PEP 585

# ❌ Not available (need 3.10+)
int | str                   # PEP 604 - use Union[int, str]
match/case                  # Pattern matching
```

### Python 3.10 Projects

```python
# ✅ Available
list[int]                   # PEP 585
int | str                   # PEP 604
match/case                  # Pattern matching

# ❌ Not available (need 3.11+)
typing.Self                 # Use TypeVar
```

### Python 3.11 Projects

```python
# ✅ Available
list[int]                   # PEP 585
int | str                   # PEP 604
match/case                  # Pattern matching
typing.Self                 # Self type

# ❌ Not available (need 3.12+)
typing.override             # Just skip decorator
type aliases (PEP 695)      # Use TypeAlias
```

### Python 3.12 Projects

```python
# ✅ All features available
list[int]                   # PEP 585
int | str                   # PEP 604
match/case                  # Pattern matching
typing.Self                 # Self type
typing.override             # Override checking
type Alias = ...            # PEP 695
```

---

## Performance Impact Summary

| Feature | Memory | Speed | When Impact Matters |
|---------|--------|-------|-------------------|
| PEP 585 | None | None | Never (type hints only) |
| PEP 604 | None | None | Never (type hints only) |
| PEP 695 | None | None | Never (type hints only) |
| typing.Self | None | None | Never (type hints only) |
| typing.override | None | None | Never (type hints only) |
| **__slots__** | **-40-60%** | **+10-20%** | **1000+ instances** |
| **cached_property** | **+Minimal** | **+100-1000%** | **Expensive computations** |
| match/case | None | +Slight | Complex dispatch |

---

## Checklist for Modern Python

### Type Hints (3.9+)
- [ ] Replace `List` → `list`
- [ ] Replace `Dict` → `dict`
- [ ] Replace `Set` → `set`
- [ ] Replace `Tuple` → `tuple`

### Union Types (3.10+)
- [ ] Replace `Optional[T]` → `T | None`
- [ ] Replace `Union[A, B]` → `A | B`

### Type Aliases (3.12+)
- [ ] Convert `TypeAlias` → `type`
- [ ] Create domain-specific type aliases

### Self Type (3.11+)
- [ ] Add `Self` to factory methods
- [ ] Add `Self` to builder methods
- [ ] Add `Self` to copy/clone methods

### Override (3.12+)
- [ ] Add `@override` to all method overrides
- [ ] Run type checker (mypy/pyright)

### Performance (All versions)
- [ ] Add `__slots__` to data classes
- [ ] Use `@cached_property` for expensive computations
- [ ] Consider pattern matching for dispatch

### Testing
- [ ] Run `mypy --strict`
- [ ] Run full test suite
- [ ] Check memory usage (before/after)
- [ ] Verify backward compatibility

---

## Recommended Reading

- [PEP 585](https://peps.python.org/pep-0585/) - Type Hinting Generics In Standard Collections
- [PEP 604](https://peps.python.org/pep-0604/) - Allow writing union types as X | Y
- [PEP 695](https://peps.python.org/pep-0695/) - Type Parameter Syntax
- [PEP 673](https://peps.python.org/pep-0673/) - Self Type
- [PEP 698](https://peps.python.org/pep-0698/) - Override Decorator
- [PEP 634-636](https://peps.python.org/pep-0634/) - Structural Pattern Matching
- [Python Data Model - __slots__](https://docs.python.org/3/reference/datamodel.html#slots)
- [functools.cached_property](https://docs.python.org/3/library/functools.html#functools.cached_property)

---

## Quick Decision Guide

```
Need type hints? → Use PEP 585/604 (3.9+/3.10+)
                   ├─ Simple types: list[int], dict[str, int]
                   └─ Unions: int | str | None

Factory methods? → Use Self (3.11+)
                   └─ @classmethod def create(...) -> Self

Method overrides? → Use @override (3.12+)
                    └─ Catches signature mismatches

Many instances? → Use __slots__
                  ├─ Memory: -40-60%
                  └─ Speed: +10-20%

Expensive property? → Use @cached_property (3.8+)
                      └─ Compute once, cache result

Complex dispatch? → Use match/case (3.10+)
                    └─ Cleaner than if/elif
```
