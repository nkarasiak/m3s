"""
Intelligent precision selection for spatial grid systems.

This module provides sophisticated precision selection strategies that help users
choose the optimal precision level for their use case without manual trial-and-error.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from ..base import BaseGrid, nominal_area_km2
from ..geohash import GeohashGrid
from ..registry import GRID_CLASSES

# Name -> grid class. Reuses the canonical registry as the single name->class
# map, plus the ``geohash_int`` alias used by the builder/parameters layer.
# Precision ranges come from each class's MIN_PRECISION/MAX_PRECISION (the
# single source of truth), so AreaCalculator never keeps its own range copy.
_GRID_CLASSES: dict[str, type[BaseGrid]] = {
    **GRID_CLASSES,
    "geohash_int": GeohashGrid,
}


@dataclass
class PrecisionRecommendation:
    """
    Recommendation for grid precision with confidence and explanation.

    Attributes
    ----------
    precision : int
        Recommended precision/resolution level
    confidence : float
        Confidence score (0.0 to 1.0) indicating recommendation quality
    explanation : str
        Human-readable explanation of the recommendation
    actual_area_km2 : Optional[float]
        Actual cell area at recommended precision (for area-based selection)
    actual_cell_count : Optional[int]
        Actual cell count in region (for count-based selection)
    edge_length_m : Optional[float]
        Estimated edge length in meters (for distance-based selection)
    metadata : Optional[Dict]
        Additional metadata about the recommendation
    """

    precision: int
    confidence: float
    explanation: str
    actual_area_km2: Optional[float] = None
    actual_cell_count: Optional[int] = None
    edge_length_m: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


class AreaCalculator:
    """
    Nominal cell-area lookups for precision selection.

    Areas come from the shared core via geodesic sampling
    (:func:`m3s.base.nominal_area_km2`) — the single source of nominal area, so
    this can never drift from ``Grid.area_km2``. Each sampled ``(grid,
    precision)`` value is cached, so after first touch it is effectively an O(1)
    lookup. Passing a ``latitude`` samples the cell there for the true local area
    (used by region-based selection); omitting it uses the canonical 45° nominal.

    The valid precision range comes from the grid class
    (``MIN_PRECISION``/``MAX_PRECISION``), the single source of truth.
    """

    def __init__(self, grid_system: str):
        """
        Initialize area calculator for a specific grid system.

        Parameters
        ----------
        grid_system : str
            Name of the grid system (e.g., 'geohash', 'h3', 's2').
        """
        if grid_system not in _GRID_CLASSES:
            raise ValueError(
                f"Unknown grid system: {grid_system}. "
                f"Valid systems: {', '.join(_GRID_CLASSES)}"
            )
        self.grid_system = grid_system
        self._grid_class = _GRID_CLASSES[grid_system]
        # Range comes from the grid class (single source of truth), so it always
        # matches the grid's own constructor validation.
        self.min_precision, self.max_precision = self._grid_class.precision_range()

    @property
    def area_table(self) -> list[float]:
        """
        Nominal area (km²) at each precision in range, sampled at canonical 45°.

        Derived on demand from the per-precision sampled areas (each cached), so
        it stays consistent with :meth:`get_area` and ``Grid.area_km2``.
        """
        return [
            self.get_area(p) for p in range(self.min_precision, self.max_precision + 1)
        ]

    def get_area(self, precision: int, latitude: Optional[float] = None) -> float:
        """
        Nominal cell area at ``precision``, optionally sampled at ``latitude``.

        Parameters
        ----------
        precision : int
            Precision level.
        latitude : Optional[float]
            Latitude to sample at, for the true local area. Defaults to the
            canonical nominal latitude (45°).

        Returns
        -------
        float
            Cell area in km².
        """
        if not self.min_precision <= precision <= self.max_precision:
            raise ValueError(
                f"Precision {precision} out of range "
                f"[{self.min_precision}, {self.max_precision}] for {self.grid_system}"
            )
        grid = self._grid_class(precision=precision)
        return nominal_area_km2(grid, latitude=latitude)

    def find_precision_for_area(
        self, target_area_km2: float, latitude: Optional[float] = None
    ) -> int:
        """
        Find precision level closest to target area using binary search.

        Parameters
        ----------
        target_area_km2 : float
            Desired cell area in km²
        latitude : Optional[float]
            Latitude for distortion correction

        Returns
        -------
        int
            Precision level with area closest to target
        """
        # Binary search through precision range
        best_precision = self.min_precision
        best_diff = float("inf")

        for precision in range(self.min_precision, self.max_precision + 1):
            area = self.get_area(precision, latitude)
            diff = abs(area - target_area_km2)

            if diff < best_diff:
                best_diff = diff
                best_precision = precision

        return best_precision


class PerformanceProfiler:
    """
    Empirical performance estimates for grid operations.

    Provides timing estimates based on cell counts and operation types
    to support performance-based precision selection.
    """

    # Empirical timing coefficients (ms per operation per cell)
    # Derived from benchmark tests on typical hardware
    OPERATION_COSTS = {
        "point_query": 0.001,  # Very fast
        "neighbor": 0.01,  # Fast
        "intersect": 0.1,  # Moderate
        "contains": 0.05,  # Moderate
        "conversion": 0.5,  # Expensive
        "aggregate": 0.02,  # Moderate
    }

    # Base overhead per operation (ms)
    BASE_OVERHEAD = {
        "point_query": 0.5,
        "neighbor": 1.0,
        "intersect": 5.0,
        "contains": 2.0,
        "conversion": 10.0,
        "aggregate": 3.0,
    }

    def estimate_operation_time(
        self, operation_type: str, cell_count: int, grid_system: str
    ) -> float:
        """
        Estimate operation time in milliseconds.

        Parameters
        ----------
        operation_type : str
            Type of operation ('point_query', 'neighbor', 'intersect', etc.)
        cell_count : int
            Number of cells involved in operation
        grid_system : str
            Grid system name (some systems are faster than others)

        Returns
        -------
        float
            Estimated time in milliseconds
        """
        if operation_type not in self.OPERATION_COSTS:
            operation_type = "intersect"  # Default to moderate cost

        base_time = self.BASE_OVERHEAD[operation_type]
        per_cell_time = self.OPERATION_COSTS[operation_type]

        # System-specific multipliers
        system_multipliers = {
            "h3": 1.0,  # Baseline (highly optimized)
            "s2": 1.0,  # Also highly optimized
            "geohash": 1.2,  # Slightly slower
            "quadkey": 1.1,  # Fast
            "slippy": 1.1,  # Fast
            "mgrs": 1.5,  # UTM conversions add overhead
        }
        multiplier = system_multipliers.get(grid_system, 1.3)

        return base_time + (per_cell_time * cell_count * multiplier)


# Curated use case presets optimized for each grid system
USE_CASE_PRESETS = {
    "geohash": {
        "global": 1,
        "continental": 2,
        "country": 3,
        "region": 4,
        "city": 5,
        "neighborhood": 6,
        "street": 7,
        "building": 8,
        "room": 9,
    },
    "h3": {
        "global": 0,
        "continental": 2,
        "country": 3,
        "region": 5,
        "city": 7,
        "neighborhood": 9,
        "street": 11,
        "building": 13,
        "room": 15,
    },
    "s2": {
        "global": 0,
        "continental": 4,
        "country": 8,
        "region": 12,
        "city": 16,
        "neighborhood": 20,
        "street": 24,
        "building": 28,
        "room": 30,
    },
    "quadkey": {
        "global": 1,
        "continental": 4,
        "country": 7,
        "region": 10,
        "city": 13,
        "neighborhood": 16,
        "street": 19,
        "building": 22,
        "room": 23,
    },
    "slippy": {
        "global": 0,
        "continental": 3,
        "country": 6,
        "region": 9,
        "city": 12,
        "neighborhood": 15,
        "street": 18,
        "building": 20,
        "room": 20,
    },
    "mgrs": {
        "global": 1,
        "continental": 1,
        "country": 2,
        "region": 3,
        "city": 4,
        "neighborhood": 5,
        "street": 6,
        "building": 6,
        "room": 6,
    },
    "csquares": {
        "global": 1,
        "continental": 2,
        "country": 3,
        "region": 4,
        "city": 5,
        "neighborhood": 5,
        "street": 5,
        "building": 5,
        "room": 5,
    },
    "gars": {
        "global": 1,
        "continental": 1,
        "country": 2,
        "region": 3,
        "city": 3,
        "neighborhood": 3,
        "street": 3,
        "building": 3,
        "room": 3,
    },
    "maidenhead": {
        "global": 1,
        "continental": 2,
        "country": 3,
        "region": 4,
        "city": 5,
        "neighborhood": 6,
        "street": 6,
        "building": 6,
        "room": 6,
    },
    "pluscode": {
        "global": 2,
        "continental": 4,
        "country": 6,
        "region": 8,
        "city": 10,
        "neighborhood": 11,
        "street": 12,
        "building": 13,
        "room": 14,
    },
    "eaquad": {  # precision 0-20 -> 1024 km .. ~0.98 m cells
        "global": 0,  # 1024 km
        "continental": 2,  # 256 km
        "country": 3,  # 128 km
        "region": 5,  # 32 km
        "city": 7,  # 8 km
        "neighborhood": 9,  # 2 km
        "street": 12,  # 250 m
        "building": 15,  # ~31 m
        "room": 18,  # ~3.9 m
    },
    "rhealpix": {  # resolution 0-15, aperture 9 (areas /9 per step)
        "global": 0,  # ~9,200 km
        "continental": 2,  # ~1,000 km
        "country": 3,  # ~340 km
        "region": 5,  # ~38 km
        "city": 6,  # ~13 km
        "neighborhood": 8,  # ~1.4 km
        "street": 10,  # ~160 m
        "building": 12,  # ~17 m
        "room": 14,  # ~1.9 m
    },
}


class PrecisionSelector:
    """
    Intelligent precision selection for spatial grid systems.

    Provides 5 strategies for selecting optimal precision:
    1. Area-based: Target specific cell area
    2. Count-based: Target cell count in region
    3. Use-case based: Curated presets for common scenarios
    4. Distance-based: Target edge length
    5. Performance-based: Balance precision vs computation time
    """

    def __init__(self, grid_system: str):
        """
        Initialize precision selector for specific grid system.

        Parameters
        ----------
        grid_system : str
            Name of the grid system (e.g., 'geohash', 'h3', 's2')
        """
        self.grid_system = grid_system
        self.area_calculator = AreaCalculator(grid_system)
        self.performance_profiler = PerformanceProfiler()

    def for_area(
        self,
        target_area_km2: float,
        tolerance: float = 0.3,
        latitude: Optional[float] = None,
    ) -> PrecisionRecommendation:
        """
        Select precision based on target cell area.

        Parameters
        ----------
        target_area_km2 : float
            Desired cell area in km²
        tolerance : float, optional
            Acceptable deviation from target (default: 0.3 = 30%)
        latitude : Optional[float], optional
            Latitude for distortion correction

        Returns
        -------
        PrecisionRecommendation
            Recommendation with confidence and explanation
        """
        precision = self.area_calculator.find_precision_for_area(
            target_area_km2, latitude
        )
        actual_area = self.area_calculator.get_area(precision, latitude)

        deviation = abs(actual_area - target_area_km2) / target_area_km2
        confidence = max(0.0, 1.0 - (deviation / tolerance))

        explanation = (
            f"{self.grid_system.upper()} precision {precision} provides "
            f"{actual_area:.2f} km² cells "
            f"({deviation * 100:.1f}% diff from target {target_area_km2:.2f} km²)"
        )

        return PrecisionRecommendation(
            precision=precision,
            confidence=confidence,
            explanation=explanation,
            actual_area_km2=actual_area,
            metadata={"target_area_km2": target_area_km2, "deviation": deviation},
        )

    def for_region_count(
        self,
        bounds: Tuple[float, float, float, float],
        target_count: int,
        tolerance: float = 0.3,
    ) -> PrecisionRecommendation:
        """
        Select precision to achieve target cell count in region.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box (min_lat, min_lon, max_lat, max_lon)
        target_count : int
            Desired number of cells
        tolerance : float, optional
            Acceptable deviation from target count (default: 0.3 = 30%)

        Returns
        -------
        PrecisionRecommendation
            Recommendation with confidence and explanation
        """
        min_lat, min_lon, max_lat, max_lon = bounds

        # Estimate region area (approximate, assumes small region)
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon
        center_lat = (min_lat + max_lat) / 2

        # Haversine approximation for region area
        lat_km = lat_diff * 111.32  # 1° latitude ≈ 111.32 km
        lon_km = lon_diff * 111.32 * math.cos(math.radians(center_lat))
        region_area_km2 = lat_km * lon_km

        # Pick the precision whose estimated cell count is closest to the
        # target. Optimising the count objective directly is more accurate than
        # going via a per-cell target area, especially for grids with coarse
        # precision steps where the nearest cell area lands far from the count.
        precision = self.area_calculator.min_precision
        estimated_count = 0
        best_diff = float("inf")
        for candidate in range(
            self.area_calculator.min_precision, self.area_calculator.max_precision + 1
        ):
            cell_area = self.area_calculator.get_area(candidate, center_lat)
            count = int(region_area_km2 / cell_area) if cell_area > 0 else 0
            diff = abs(count - target_count)
            if diff < best_diff:
                best_diff = diff
                precision = candidate
                estimated_count = count

        deviation = abs(estimated_count - target_count) / target_count
        confidence = max(0.0, 1.0 - (deviation / tolerance))

        explanation = (
            f"{self.grid_system.upper()} precision {precision} yields "
            f"~{estimated_count} cells in region "
            f"({deviation * 100:.1f}% diff from target {target_count})"
        )

        return PrecisionRecommendation(
            precision=precision,
            confidence=confidence,
            explanation=explanation,
            actual_cell_count=estimated_count,
            metadata={
                "target_count": target_count,
                "region_area_km2": region_area_km2,
                "deviation": deviation,
            },
        )

    def for_use_case(
        self, use_case: str, context: Optional[Dict[str, Any]] = None
    ) -> PrecisionRecommendation:
        """
        Select precision based on curated use case preset.

        Parameters
        ----------
        use_case : str
            Use case name: 'global', 'continental', 'country', 'region',
            'city', 'neighborhood', 'street', 'building', 'room'
        context : Optional[Dict], optional
            Additional context (e.g., {'latitude': 40.7} for polar adjustments)

        Returns
        -------
        PrecisionRecommendation
            Recommendation with high confidence (curated presets)
        """
        valid_use_cases = list(USE_CASE_PRESETS.get(self.grid_system, {}).keys())
        if use_case not in valid_use_cases:
            raise ValueError(
                f"Unknown use case '{use_case}'. Valid options: "
                f"{', '.join(valid_use_cases)}"
            )

        # Clamp the curated preset to the grid's valid range: some presets name
        # a finer level than a coarse grid (e.g. PlusCode/Maidenhead) supports,
        # in which case the finest available precision is used.
        precision = USE_CASE_PRESETS[self.grid_system][use_case]
        precision = max(
            self.area_calculator.min_precision,
            min(self.area_calculator.max_precision, precision),
        )

        # Apply latitude adjustment for polar regions
        latitude = context.get("latitude") if context else None
        if latitude is not None and abs(latitude) > 60:
            # Increase precision near poles due to cell distortion
            precision = min(precision + 1, self.area_calculator.max_precision)

        actual_area = self.area_calculator.get_area(precision, latitude)

        explanation = (
            f"{self.grid_system.upper()} precision {precision} optimized for "
            f"'{use_case}' use case (avg cell area: {actual_area:.2f} km²)"
        )

        return PrecisionRecommendation(
            precision=precision,
            confidence=0.95,  # High confidence for curated presets
            explanation=explanation,
            actual_area_km2=actual_area,
            metadata={"use_case": use_case},
        )

    def for_distance(
        self,
        edge_length_m: float,
        tolerance: float = 0.3,
        latitude: Optional[float] = None,
    ) -> PrecisionRecommendation:
        """
        Select precision based on target edge length.

        Parameters
        ----------
        edge_length_m : float
            Desired edge length in meters
        tolerance : float, optional
            Acceptable deviation from target (default: 0.3 = 30%)
        latitude : Optional[float], optional
            Latitude for distortion correction

        Returns
        -------
        PrecisionRecommendation
            Recommendation with confidence and explanation
        """
        # Convert edge length to area
        # For hexagons: area ≈ (edge_length^2) * 2.598
        # For squares: area = edge_length^2
        # Use geometric mean for mixed systems
        edge_length_km = edge_length_m / 1000.0

        if self.grid_system == "h3":
            # H3 uses hexagons
            target_area_km2 = (edge_length_km**2) * 2.598
        elif self.grid_system in ["s2", "quadkey", "slippy", "csquares"]:
            # Square-ish cells
            target_area_km2 = edge_length_km**2
        else:
            # Conservative estimate for other systems
            target_area_km2 = (edge_length_km**2) * 1.5

        precision = self.area_calculator.find_precision_for_area(
            target_area_km2, latitude
        )
        actual_area = self.area_calculator.get_area(precision, latitude)

        # Estimate actual edge length from area
        if self.grid_system == "h3":
            actual_edge_km = (actual_area / 2.598) ** 0.5
        else:
            actual_edge_km = actual_area**0.5

        actual_edge_m = actual_edge_km * 1000.0

        deviation = abs(actual_edge_m - edge_length_m) / edge_length_m
        confidence = max(0.0, 1.0 - (deviation / tolerance))

        explanation = (
            f"{self.grid_system.upper()} precision {precision} provides "
            f"~{actual_edge_m:.1f}m edges "
            f"({deviation * 100:.1f}% diff from target {edge_length_m:.1f}m)"
        )

        return PrecisionRecommendation(
            precision=precision,
            confidence=confidence,
            explanation=explanation,
            edge_length_m=actual_edge_m,
            metadata={"target_edge_length_m": edge_length_m, "deviation": deviation},
        )

    def for_performance(
        self,
        operation_type: str,
        time_budget_ms: float,
        region_size_km2: float,
    ) -> PrecisionRecommendation:
        """
        Select precision balancing detail vs computation time.

        Parameters
        ----------
        operation_type : str
            Type of operation: 'point_query', 'neighbor', 'intersect', 'contains',
            'conversion', 'aggregate'
        time_budget_ms : float
            Maximum acceptable computation time in milliseconds
        region_size_km2 : float
            Size of region being processed

        Returns
        -------
        PrecisionRecommendation
            Recommendation balancing precision vs performance
        """
        # Try precisions from coarse to fine, find finest within budget
        best_precision = self.area_calculator.min_precision
        best_confidence = 0.0

        for precision in range(
            self.area_calculator.min_precision, self.area_calculator.max_precision + 1
        ):
            cell_area = self.area_calculator.get_area(precision)
            # Sub-resolution cells can sample to ~0 area; treat as effectively
            # unbounded cell count so the budget loop stops at this precision.
            estimated_cells = (
                int(region_size_km2 / cell_area) if cell_area > 0 else 10**12
            )

            estimated_time = self.performance_profiler.estimate_operation_time(
                operation_type, estimated_cells, self.grid_system
            )

            if estimated_time <= time_budget_ms:
                # This precision fits within budget
                best_precision = precision
                # Higher precision within budget = higher confidence
                budget_usage = estimated_time / time_budget_ms
                best_confidence = min(0.95, 0.6 + (1 - budget_usage) * 0.35)
            else:
                # Exceeded budget, stop searching
                break

        actual_area = self.area_calculator.get_area(best_precision)
        estimated_cells = (
            int(region_size_km2 / actual_area) if actual_area > 0 else 10**12
        )
        estimated_time = self.performance_profiler.estimate_operation_time(
            operation_type, estimated_cells, self.grid_system
        )

        explanation = (
            f"{self.grid_system.upper()} precision {best_precision} balances "
            "detail vs performance "
            f"(~{estimated_cells} cells, est. {estimated_time:.1f}ms for "
            f"{operation_type})"
        )

        return PrecisionRecommendation(
            precision=best_precision,
            confidence=best_confidence,
            explanation=explanation,
            metadata={
                "operation_type": operation_type,
                "time_budget_ms": time_budget_ms,
                "estimated_time_ms": estimated_time,
                "estimated_cells": estimated_cells,
            },
        )
