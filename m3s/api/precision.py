"""
Intelligent precision selection for spatial grid systems.

This module provides sophisticated precision selection strategies that help users
choose the optimal precision level for their use case without manual trial-and-error.
"""

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


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
    metadata: Optional[Dict] = None

    def __post_init__(self):
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


class AreaCalculator:
    """
    Precomputed area lookup tables for fast precision selection.

    This class provides O(1) area lookups for all grid systems with optional
    latitude-based corrections for systems with significant distortion.
    """

    # Precomputed average cell areas in km² for each grid system
    # Values derived from grid system specifications and empirical testing
    AREA_TABLES = {
        "geohash": [  # precision 1-12
            5003.771,
            625.471,
            78.184,
            19.546,
            2.443,
            0.610,
            0.152,
            0.019,
            0.0048,
            0.0012,
            0.00030,
            0.000074,
        ],
        "h3": [  # resolution 0-15
            4357449.416,
            609788.441,
            86801.780,
            12392.264,
            1770.323,
            252.903,
            36.129,
            5.161,
            0.737,
            0.105,
            0.015,
            0.002,
            0.0003,
            0.00005,
            0.000007,
            0.000001,
        ],
        "s2": [  # level 0-30, approximate average
            85011012.19,
            21252753.05,
            5313188.26,
            1328297.07,
            332074.27,
            83018.57,
            20754.64,
            5188.66,
            1297.17,
            324.29,
            81.07,
            20.27,
            5.07,
            1.27,
            0.32,
            0.08,
            0.02,
            0.005,
            0.001,
            0.0003,
            0.00008,
            0.00002,
            0.000005,
            0.000001,
            0.00000032,
            0.00000008,
            0.00000002,
            0.000000005,
            0.000000001,
            0.00000000032,
            0.00000000008,
        ],
        "quadkey": [  # level 1-23
            127516118.0,
            31879029.5,
            7969757.38,
            1992439.34,
            498109.84,
            124527.46,
            31131.86,
            7782.97,
            1945.74,
            486.43,
            121.61,
            30.40,
            7.60,
            1.90,
            0.47,
            0.12,
            0.03,
            0.007,
            0.002,
            0.0005,
            0.0001,
            0.00003,
            0.000008,
        ],
        "slippy": [  # zoom 0-20 (same as quadkey)
            510072000.0,
            127518000.0,
            31879500.0,
            7969875.0,
            1992469.0,
            498117.0,
            124529.0,
            31132.0,
            7783.0,
            1946.0,
            486.5,
            121.6,
            30.4,
            7.6,
            1.9,
            0.475,
            0.119,
            0.030,
            0.007,
            0.002,
            0.0005,
        ],
        "geohash_int": [  # Same as geohash for now
            5003.771,
            625.471,
            78.184,
            19.546,
            2.443,
            0.610,
            0.152,
            0.019,
            0.0048,
            0.0012,
            0.00030,
            0.000074,
        ],
        "mgrs": [  # 1m to 100km grid squares
            10000.0,  # 100km
            100.0,  # 10km
            1.0,  # 1km
            0.01,  # 100m
            0.0001,  # 10m
            0.000001,  # 1m
        ],
        "csquares": [  # C-squares resolutions
            2827433.39,  # 10° × 10°
            282743.34,  # 1° × 1°
            2827.43,  # 0.1° × 0.1°
            28.27,  # 0.01° × 0.01°
            0.28,  # 0.001° × 0.001°
        ],
        "gars": [  # GARS resolutions
            155400.0,  # 30' × 30'
            6475.0,  # 15' × 15'
            269.8,  # 5' × 5'
        ],
        "maidenhead": [  # Maidenhead locator precision 1-8
            2000000.0,  # 10° × 20° (2 chars)
            200000.0,  # 1° × 2° (4 chars)
            5000.0,  # 2.5' × 5' (6 chars)
            125.0,  # 0.625' × 1.25' (8 chars)
            3.125,  # 0.0625' × 0.125' (10 chars)
            0.078,  # 0.00625' × 0.0125' (12 chars)
        ],
        "pluscode": [  # Plus Codes precision 2-15
            24900000.0,  # 2 digits
            2490000.0,  # 4 digits
            249000.0,  # 6 digits
            24900.0,  # 8 digits
            3113.0,  # 10 digits (standard)
            389.0,  # 11 digits
            48.6,  # 12 digits
            6.1,  # 13 digits
            0.76,  # 14 digits
            0.095,  # 15 digits
        ],
        "what3words": [  # 3m × 3m fixed
            0.000009,  # 3m × 3m
        ],
        "a5": [  # A5 pentagonal DGGS resolution 0-15
            73800000.0,  # res 0
            10540000.0,  # res 1
            1506000.0,  # res 2
            215000.0,  # res 3
            30700.0,  # res 4
            4390.0,  # res 5
            627.0,  # res 6
            89.6,  # res 7
            12.8,  # res 8
            1.83,  # res 9
            0.261,  # res 10
            0.0373,  # res 11
            0.00533,  # res 12
            0.000762,  # res 13
            0.000109,  # res 14
            0.0000155,  # res 15
        ],
    }

    # Valid precision ranges for each grid system
    PRECISION_RANGES = {
        "geohash": (1, 12),
        "h3": (0, 15),
        "s2": (0, 30),
        "quadkey": (1, 23),
        "slippy": (0, 20),
        "geohash_int": (1, 12),
        "mgrs": (1, 6),
        "csquares": (1, 5),
        "gars": (1, 3),
        "maidenhead": (1, 6),
        "pluscode": (2, 15),
        "what3words": (1, 1),
        "a5": (0, 15),
    }

    def __init__(self, grid_system: str):
        """
        Initialize area calculator for specific grid system.

        Parameters
        ----------
        grid_system : str
            Name of the grid system (e.g., 'geohash', 'h3', 's2')
        """
        if grid_system not in self.AREA_TABLES:
            raise ValueError(
                f"Unknown grid system: {grid_system}. "
                f"Valid systems: {', '.join(self.AREA_TABLES.keys())}"
            )
        self.grid_system = grid_system
        self.area_table = self.AREA_TABLES[grid_system]
        self.min_precision, self.max_precision = self.PRECISION_RANGES[grid_system]

    def get_area(self, precision: int, latitude: Optional[float] = None) -> float:
        """
        Get cell area at given precision with optional latitude correction.

        Parameters
        ----------
        precision : int
            Precision level
        latitude : Optional[float]
            Latitude for distortion correction (used for Geohash, MGRS)

        Returns
        -------
        float
            Cell area in km²
        """
        if not self.min_precision <= precision <= self.max_precision:
            raise ValueError(
                f"Precision {precision} out of range "
                f"[{self.min_precision}, {self.max_precision}] for {self.grid_system}"
            )

        # Get base area from lookup table
        idx = precision - self.min_precision
        if idx >= len(self.area_table):
            # Extrapolate for very high precisions
            idx = len(self.area_table) - 1
            scale = 4 ** (precision - (self.min_precision + idx))
            base_area = self.area_table[idx] / scale
        else:
            base_area = self.area_table[idx]

        # Apply latitude correction for systems with significant distortion
        if latitude is not None and self.grid_system in [
            "geohash",
            "geohash_int",
            "mgrs",
        ]:
            # Cells shrink in area at higher latitudes due to meridian convergence
            # Simple cosine correction (approximate)
            lat_rad = math.radians(latitude)
            correction = math.cos(lat_rad)
            return base_area * correction

        return base_area

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
            "a5": 2.0,  # Python implementation, slower
            "what3words": 3.0,  # API calls required
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
    "a5": {
        "global": 0,
        "continental": 2,
        "country": 4,
        "region": 6,
        "city": 8,
        "neighborhood": 10,
        "street": 12,
        "building": 14,
        "room": 15,
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
    "what3words": {
        "global": 1,
        "continental": 1,
        "country": 1,
        "region": 1,
        "city": 1,
        "neighborhood": 1,
        "street": 1,
        "building": 1,
        "room": 1,
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
            f"{actual_area:.2f} km² cells ({deviation * 100:.1f}% diff from target {target_area_km2:.2f} km²)"
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

        # Target area per cell
        target_area_per_cell = region_area_km2 / target_count

        # Find precision for that area
        precision = self.area_calculator.find_precision_for_area(
            target_area_per_cell, center_lat
        )
        actual_area = self.area_calculator.get_area(precision, center_lat)

        # Estimate actual cell count
        estimated_count = int(region_area_km2 / actual_area)

        deviation = abs(estimated_count - target_count) / target_count
        confidence = max(0.0, 1.0 - (deviation / tolerance))

        explanation = (
            f"{self.grid_system.upper()} precision {precision} yields ~{estimated_count} cells "
            f"in region ({deviation * 100:.1f}% diff from target {target_count})"
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
        self, use_case: str, context: Optional[Dict] = None
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
                f"Unknown use case '{use_case}'. Valid options: {', '.join(valid_use_cases)}"
            )

        precision = USE_CASE_PRESETS[self.grid_system][use_case]

        # Apply latitude adjustment for polar regions
        latitude = context.get("latitude") if context else None
        if latitude is not None and abs(latitude) > 60:
            # Increase precision near poles due to cell distortion
            precision = min(precision + 1, self.area_calculator.max_precision)

        actual_area = self.area_calculator.get_area(precision, latitude)

        explanation = (
            f"{self.grid_system.upper()} precision {precision} optimized for '{use_case}' use case "
            f"(avg cell area: {actual_area:.2f} km²)"
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
        elif self.grid_system == "a5":
            # Pentagons: area ≈ (edge_length^2) * 1.72
            target_area_km2 = (edge_length_km**2) * 1.72
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
        elif self.grid_system == "a5":
            actual_edge_km = (actual_area / 1.72) ** 0.5
        else:
            actual_edge_km = actual_area**0.5

        actual_edge_m = actual_edge_km * 1000.0

        deviation = abs(actual_edge_m - edge_length_m) / edge_length_m
        confidence = max(0.0, 1.0 - (deviation / tolerance))

        explanation = (
            f"{self.grid_system.upper()} precision {precision} provides ~{actual_edge_m:.1f}m edges "
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
            estimated_cells = int(region_size_km2 / cell_area)

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
        estimated_cells = int(region_size_km2 / actual_area)
        estimated_time = self.performance_profiler.estimate_operation_time(
            operation_type, estimated_cells, self.grid_system
        )

        explanation = (
            f"{self.grid_system.upper()} precision {best_precision} balances detail vs performance "
            f"(~{estimated_cells} cells, est. {estimated_time:.1f}ms for {operation_type})"
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
