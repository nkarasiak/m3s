"""
Modern fluent API for M3S spatial grid systems.

This module provides a modern, unified interface for working with all 12 grid systems
through intelligent precision selection, fluent builder patterns, and type-safe results.
"""

from .builder import GridBuilder
from .comparator import MultiGridComparator
from .precision import (
    AreaCalculator,
    PerformanceProfiler,
    PrecisionRecommendation,
    PrecisionSelector,
)
from .results import GridQueryResult

__all__ = [
    "GridBuilder",
    "PrecisionSelector",
    "PrecisionRecommendation",
    "AreaCalculator",
    "PerformanceProfiler",
    "GridQueryResult",
    "MultiGridComparator",
]
