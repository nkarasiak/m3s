# Python Modernization Skill (2025-2026 Edition)

**Purpose**: Quick reference for applying modern Python features and performance optimizations.

**Updated**: February 2026 with Python 3.13+ and 3.14 features

---

## Version Support & Timeline

| Version | Released | EOL | Status | Key Features |
|---------|----------|-----|--------|--------------|
| **3.14** | Oct 2025 | Oct 2030 | Latest | Free-threading (PEP 779), PEP 649/750/734, JIT in binaries, zstd compression |
| **3.13** | Oct 2024 | Oct 2029 | Stable | Experimental JIT, Free-threading, 5-15% faster |
| **3.12** | Oct 2023 | Oct 2028 | Stable | `@override`, `type` aliases |
| **3.11** | Oct 2022 | Oct 2027 | Maintenance | `Self` type, 25% faster |
| 3.10 | Oct 2021 | Oct 2026 | Maintenance | `match/case`, `\|` unions |

**Note**: Python adopts calendar versioning (CalVer) in 2026. After 3.14, next version is **Python 3.26** (skips 3.15-3.25).

---

## 🎓 Modern Python Philosophy (2026)

> **"Professionals write code to make it boring"**

- **Predictable over clever**: Refactor-friendly Python beats clever one-liners
- **Readable over terse**: Code is read more often than it is written
- **Simple over complex**: Minimum complexity needed for current task
- **Boring is beautiful**: Maintainable code accumulates less technical debt

**In Practice**: Three similar lines > premature abstraction. Don't design for hypothetical futures. Only validate at system boundaries.

---

## Type Hints - Apply Always (Zero Cost)

### Modern Syntax

| Old Syntax | New Syntax | Version |
|------------|------------|---------|
| `List[T]`, `Dict[K,V]`, `Set[T]` | `list[T]`, `dict[K,V]`, `set[T]` | 3.9+ |
| `Optional[T]`, `Union[A,B]` | `T \| None`, `A \| B` | 3.10+ |
| `TypeAlias` | `type Alias = ...` | 3.12+ |
| `-> "ClassName"` | `-> Self` | 3.11+ |
| No decorator | `@override` | 3.12+ |

### Future Imports (Essential for All New Code)

```python
from __future__ import annotations  # PEP 649 - Deferred evaluation

class Node:
    def __init__(self, value: int, parent: Node | None = None):  # No quotes!
        self.value = value
        self.parent = parent
```

**Benefits**: Faster imports, reduced memory, no forward reference quotes, better IDE support.

**Advanced**: PEP 821 (TypedDict unpacking in Callable, Draft 2026), PEP 673/674 (Enhanced static analysis, 3.13+)

---

## Performance - Apply Selectively (Measure First)

### __slots__ & cached_property

| Feature | Impact | Apply When | Skip When |
|---------|--------|------------|-----------|
| **`__slots__`** | -40-60% memory, +10-20% speed | 1000+ instances, fixed attrs | Dynamic attrs, <100 instances |
| **`@cached_property`** | +100-1000% speed | Expensive computation (>1ms) | Value changes, <1ms computation |

**Pattern**: `__slots__ = ('attr1', 'attr2', '__dict__')` (include `__dict__` for `@cached_property`)

---

## 💾 Modern Dataclass Pattern (2026)

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True, frozen=True, kw_only=True)  # Modern best practice
class Point:
    x: float
    y: float

# Benefits:
# - slots=True: 10-30% memory reduction
# - frozen=True: Immutability (hashable, thread-safe)
# - kw_only=True: Prevents positional argument bugs
```

**Trade-off**: 2.4× slower instantiation (frozen), 3× slower (with slots), but faster access + memory savings.

**Rule**: Use `@dataclass(slots=True, frozen=True, kw_only=True)` by default for Python 3.10+.

---

## 📝 Code Style & Quality (PEP 8 + 2026)

### Naming (PEP 8)
- **Functions/Variables**: `snake_case` (`calculate_area`, `user_count`)
- **Classes**: `PascalCase` (`GridCell`, `DataProcessor`)
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_SIZE`)
- **Private**: `_leading_underscore` (`_internal_func`)

### Modern Tooling Stack

| Tool | Purpose | Priority |
|------|---------|----------|
| **Black** | Code formatter (line length: 88) | ⭐⭐⭐ Essential |
| **Ruff** | Fast linter (replaces flake8, isort) | ⭐⭐⭐ Essential |
| **mypy** | Static type checker (`--strict` mode) | ⭐⭐⭐ Essential |
| **pytest** | Testing framework | ⭐⭐⭐ Essential |

**Config (pyproject.toml)**:
```toml
[tool.black]
line-length = 88
target-version = ["py314"]

[tool.ruff]
line-length = 88
target-version = "py314"
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "C4", "SIM"]

[tool.mypy]
python_version = "3.14"
strict = true
disallow_untyped_defs = true
```

### Anti-Patterns to Avoid

| ❌ Anti-Pattern | ✅ Best Practice |
|----------------|------------------|
| `from module import *` | `from module import specific_func` |
| `def f(x=[]):` | `def f(x=None): x = x or []` |
| `except:` | `except Exception:` or specific |
| `except (ValueError,):` | `except ValueError:` (PEP 758, 3.14+) |
| `len(x) == 0` | `not x` |
| `type(x) == int` | `isinstance(x, int)` |
| Deep nesting (>3 levels) | Early returns, helper functions |
| `return` in `finally` block | Avoid (SyntaxError in 3.14+, PEP 765) |

---

## Modern Python Idioms (2026)

| Pattern | Example | Version |
|---------|---------|---------|
| **Future imports** | `from __future__ import annotations` | 3.11+ |
| **Pathlib** | `Path("dir") / "file.txt"` | 3.4+ |
| **F-strings** | `f"Value: {x:.2f}"` | 3.6+ |
| **Walrus** | `if (n := len(items)) > 10:` | 3.8+ |
| **Match/case** | `match val: case "x": ...` | 3.10+ |
| **Zstandard** | `import compression.zstd` | 3.14+ |

**Python 3.14+ Specifics**:
```python
# Zstandard compression (faster than gzip)
import compression.zstd as zstd
compressed = zstd.compress(data, level=3)

# Template strings for SQL injection prevention (PEP 750)
from typing import LiteralString
def execute_query(query: LiteralString) -> None:
    cursor.execute(query)  # Type checker ensures literal string
```

---

## 🚀 Python 3.13-3.14 Features

### Free-Threaded Mode / No-GIL (3.13+, Experimental)

| Aspect | Details |
|--------|---------|
| **Enable** | Build with `--disable-gil` or use `python3.13t` |
| **Performance** | 2.2× (3.13) → 3.1× (3.14) for CPU-bound multi-threaded |
| **Single-thread cost** | ~40% slower (3.13) → ~5-10% slower (3.14) |
| **Best for** | CPU-intensive parallel workloads (4+ cores) |
| **Avoid** | I/O-bound tasks, single-threaded code |

### JIT Compiler (3.13+, Production in 3.14)

| Platform | 3.13 | 3.14 |
|----------|------|------|
| **macOS/Windows** | Custom build (`--enable-experimental-jit`) | **Included in official binaries (no setup!)** |
| **Linux** | Custom build | Custom build (wait for 3.26 for official support) |

**Performance**: 5-15% general, up to 30% computation-heavy tasks.

**Recommendation for Linux**: Unless critical need, **wait for Python 3.26** for production JIT support rather than custom builds.

### Python 3.14 Key Features (PEPs)

| Feature | PEP | Use Case |
|---------|-----|----------|
| **Free-Threading Official** | 779 | Multi-core CPU tasks |
| **Deferred Annotations** | 649 | Large codebases (faster imports) |
| **Template Strings** | 750 | SQL queries, HTML (safer interpolation) |
| **Sub-Interpreters** | 734 | Plugin systems, sandboxing |
| **Zstandard Compression** | 784 | High-performance compression |
| **Exception Syntax** | 758 | `except` without brackets |
| **Finally Restrictions** | 765 | Disallow return/break/continue in finally |
| **Emscripten Support** | 776 | WebAssembly targets |

---

## ⚡ CPU Performance (2025 Benchmarks)

### Compilation Tools

| Tool | Speedup | Best For |
|------|---------|----------|
| **Codon** | >90% | Scientific computing |
| **PyPy** | >90% | Long-running apps |
| **Numba** | >90% | NumPy-heavy code |
| **Mypyc** | ~20× | Type-annotated code |
| **Cython** | Variable | Math-intensive loops |
| **Python 3.14 JIT** | 5-30% | General (macOS/Windows) |

### Decision Tree

```
Need speed improvement?
├─ NumPy/scientific → Numba or Codon
├─ Type-annotated → Mypyc
├─ Math loops → Cython
├─ Multi-threaded CPU → Python 3.14 free-threading
└─ General → Upgrade to Python 3.14+ (JIT included on macOS/Windows)
```

---

## 🎯 2026 Recommendations

### For New Projects

| Requirement | Recommendation |
|-------------|----------------|
| **Python version** | 3.14 (or 3.13 minimum) |
| **Future imports** | `from __future__ import annotations` |
| **Data classes** | `@dataclass(slots=True, frozen=True, kw_only=True)` |
| **Type hints** | 100% coverage with `mypy --strict` |
| **Performance** | Profile first → Numba/Mypyc/Cython if needed |
| **Multi-core CPU** | Consider free-threading (3.14+, experimental) |

### Migration Priority

1. **High**: Upgrade to Python 3.14+ (5-15% free speedup, JIT on macOS/Windows)
2. **Medium**: Add `from __future__ import annotations` + `slots=True` to dataclasses
3. **Low**: Enable JIT on Linux (custom build) only if critical; otherwise wait for 3.26
4. **Experimental**: Try free-threading for CPU-parallel workloads

---

## Refactoring Phases

| Phase | Tasks | Priority |
|-------|-------|----------|
| **1. Type Hints** | Replace typing imports, use built-in generics, add `from __future__ import annotations` | ⭐⭐⭐ Do First |
| **2. Self/Override** | Add `Self` to factories, `@override` to overrides | ⭐⭐⭐ Essential |
| **3. Performance** | Add `__slots__`/`@cached_property`, benchmark | ⭐⭐ If Needed |
| **4. Pattern Matching** | Convert if/elif chains | ⭐ Optional |

---

## Quick Reference

### Essential Patterns

```python
# Modern dataclass (2026)
@dataclass(slots=True, frozen=True, kw_only=True)
class Point:
    x: float
    y: float

# Factory method
@classmethod
def create() -> Self:
    return cls()

# Override decorator
@override
def method(self) -> None:
    super().method()

# Pattern matching (3+ branches)
match command:
    case "start": handle_start()
    case "stop": handle_stop()
    case _: handle_unknown()
```

### Skip Conditions

| Feature | Skip When |
|---------|-----------|
| **`__slots__`** | <100 instances, dynamic attrs, plugins |
| **`@cached_property`** | Value changes, <1ms computation |
| **`match/case`** | Boolean conditions, 1-2 branches |
| **Free-threading** | I/O-bound, single-threaded |

---

## Key Rules (2026 Edition)

### Code Style
1. **Black + Ruff + mypy** on pre-commit hooks
2. **NumPy docstrings** for scientific packages
3. **100% type hints** on public API with `mypy --strict`

### Type Safety
4. **`from __future__ import annotations`** in all new 3.11+ code
5. **Modern syntax**: `list[T]`, `T | None`, `type Alias = ...`
6. **`Self`** for factories/builders (3.11+)
7. **`@override`** for method overrides (3.12+)

### Memory & Performance
8. **`@dataclass(slots=True, frozen=True, kw_only=True)`** by default (3.10+)
9. **Generators** for large datasets (`yield` vs `return list`)
10. **Python 3.14+**: JIT included on macOS/Windows (free 5-15% boost)
11. **Profile before optimizing**: Use `cProfile`, then Numba/Mypyc if needed

### Modern Patterns
12. **Pathlib** over `os.path`
13. **F-strings** over `.format()` or `%`
14. **Context managers** (`with`) for resources
15. **Early returns** to avoid deep nesting (max 3 levels)

---

## Golden Rules

- **Code Style**: Black + Ruff + mypy on every commit
- **Type Safety**: `from __future__ import annotations` + 100% coverage + `mypy --strict`
- **Performance**: Upgrade to 3.14+ first (JIT free on macOS/Windows!), profile before compiling
- **Memory**: `@dataclass(slots=True, frozen=True, kw_only=True)` saves 10-30%
- **Philosophy**: "Make it boring" - predictable code beats clever code

**Linux Users**: For JIT, wait for Python 3.26 rather than custom builds unless critical need.
