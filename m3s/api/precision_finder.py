"""
Intelligent precision selection for grid systems.

Provides algorithms to automatically determine optimal precision levels
based on geometries, target areas, and use cases.
"""

import math
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

if TYPE_CHECKING:
    from .grid_wrapper import GridWrapper


class PrecisionFinder:
    """
    Find optimal precision for geometries and use cases.

    Provides intelligent precision selection based on coverage optimization,
    target cell counts, and predefined use cases.

    Parameters
    ----------
    grid_wrapper : GridWrapper
        Reference to parent grid wrapper
    """

    # Use case to target area mapping (in km²)
    USE_CASE_AREAS = {
        "building": (0.001, 0.01),  # Individual buildings
        "block": (0.01, 0.1),  # City blocks
        "neighborhood": (1.0, 10.0),  # Neighborhoods
        "city": (100.0, 1000.0),  # Cities
        "region": (10000.0, 100000.0),  # States/provinces
        "country": (100000.0, 1000000.0),  # Countries
    }

    def __init__(self, grid_wrapper: "GridWrapper"):
        """Initialize precision finder with grid wrapper."""
        self._grid = grid_wrapper
        self._cache: Dict[str, int] = {}

    def for_geometries(
        self,
        geometries: Union[Polygon, MultiPolygon, gpd.GeoDataFrame, List[Polygon]],
        method: Union[str, int] = "auto",
    ) -> int:
        """
        Find optimal precision for geometries.

        Parameters
        ----------
        geometries : Union[Polygon, MultiPolygon, gpd.GeoDataFrame, List[Polygon]]
            Input geometries
        method : Union[str, int], optional
            Selection method:
            - 'auto': Minimize coverage variance (default, best quality)
            - 'less': Fewer, larger cells
            - 'more': More, smaller cells
            - 'balanced': Balance coverage quality and cell count
            - int (e.g., 100): Target specific cell count

        Returns
        -------
        int
            Optimal precision level
        """
        # Convert input to unified format
        geometry = self._normalize_geometries(geometries)
        if geometry is None or geometry.is_empty:
            return self._grid._default_precision

        # Calculate geometry properties
        geom_area = self._calculate_area_km2(geometry)
        if geom_area == 0:
            return self._grid._default_precision

        # Get candidate precisions to test
        candidates = self._get_candidate_precisions(geom_area, method)

        # OPTIMIZATION: For very large areas that would produce many cells,
        # use fast approximation instead of testing all candidates
        estimated = self._estimate_precision_for_area(geom_area)
        test_grid = self._grid._get_grid(estimated)
        test_cell = test_grid.get_cell_from_point(0, 0)
        estimated_cells = (
            int(geom_area / test_cell.area_km2) if test_cell.area_km2 > 0 else 0
        )

        # If estimated cells > 10000, use fast path (skip expensive coverage testing)
        if estimated_cells > 10000:
            if isinstance(method, int):
                # Still try to match target count
                return self._find_precision_for_count_fast(geometry, method, candidates)
            else:
                # Use area-based approximation
                if method == "less":
                    return max(candidates[0], estimated - 1)
                elif method == "more":
                    return min(candidates[-1], estimated + 1)
                else:  # auto, balanced
                    return estimated

        # Normal path for smaller areas
        if isinstance(method, int):
            # Target specific cell count
            return self._find_precision_for_count(geometry, method, candidates)
        elif method == "auto":
            # Minimize coverage variance (user preference)
            return self._find_precision_minimize_variance(geometry, candidates)
        elif method == "less":
            # Prefer fewer, larger cells
            return self._find_precision_fewer_cells(geometry, candidates)
        elif method == "more":
            # Prefer more, smaller cells
            return self._find_precision_more_cells(geometry, candidates)
        elif method == "balanced":
            # Balance coverage and count
            return self._find_precision_balanced(geometry, candidates)
        else:
            raise ValueError(
                f"Invalid method: {method}. "
                "Use 'auto', 'less', 'more', 'balanced', or integer count."
            )

    def for_area(self, target_km2: float, tolerance: float = 0.2) -> int:
        """
        Find precision closest to target cell area.

        Parameters
        ----------
        target_km2 : float
            Target cell area in square kilometers
        tolerance : float, optional
            Acceptable relative error (default: 0.2 = 20%)

        Returns
        -------
        int
            Precision with cell area closest to target
        """
        # Test all valid precisions for this grid system
        min_precision, max_precision = self._grid._get_precision_range()

        best_precision = min_precision
        best_error = float("inf")

        for precision in range(min_precision, max_precision + 1):
            # Get typical cell area at this precision
            test_cell = self._grid._get_grid(precision).get_cell_from_point(0, 0)
            cell_area = test_cell.area_km2

            # Calculate relative error
            error = abs(cell_area - target_km2) / target_km2

            if error < best_error:
                best_error = error
                best_precision = precision

            # Stop if within tolerance
            if error <= tolerance:
                break

        return best_precision

    def for_use_case(self, use_case: str) -> int:
        """
        Find precision for predefined use case.

        Parameters
        ----------
        use_case : str
            Use case name: 'building', 'block', 'neighborhood', 'city',
            'region', or 'country'

        Returns
        -------
        int
            Recommended precision for use case

        Raises
        ------
        ValueError
            If use case not recognized
        """
        if use_case not in self.USE_CASE_AREAS:
            raise ValueError(
                f"Unknown use case: {use_case}. "
                f"Valid cases: {', '.join(self.USE_CASE_AREAS.keys())}"
            )

        # Get target area range for use case
        min_area, max_area = self.USE_CASE_AREAS[use_case]
        target_area = math.sqrt(min_area * max_area)  # Geometric mean

        return self.for_area(target_area, tolerance=0.3)

    # Internal helper methods

    def _normalize_geometries(
        self, geometries: Union[Polygon, MultiPolygon, gpd.GeoDataFrame, List[Polygon]]
    ) -> Optional[Polygon]:
        """Convert various geometry inputs to single Polygon/MultiPolygon."""
        if isinstance(geometries, (Polygon, MultiPolygon)):
            return geometries
        elif isinstance(geometries, gpd.GeoDataFrame):
            if len(geometries) == 0:
                return None
            return unary_union(geometries.geometry)
        elif isinstance(geometries, list):
            if len(geometries) == 0:
                return None
            return unary_union(geometries)
        else:
            raise TypeError(
                f"Unsupported geometry type: {type(geometries)}. "
                "Use Polygon, MultiPolygon, GeoDataFrame, or List[Polygon]."
            )

    def _calculate_area_km2(self, geometry: Union[Polygon, MultiPolygon]) -> float:
        """Calculate geometry area in km²."""
        # Simple approximation using bounds
        bounds = geometry.bounds
        min_lon, min_lat, max_lon, max_lat = bounds

        # Earth's radius in km
        R = 6371.0

        # Convert to radians
        lat_rad = math.radians((min_lat + max_lat) / 2)
        lat_diff_rad = math.radians(max_lat - min_lat)
        lon_diff_rad = math.radians(max_lon - min_lon)

        # Approximate area
        area_km2 = R * R * abs(lat_diff_rad * lon_diff_rad * math.cos(lat_rad))

        return max(area_km2, 0.001)  # Minimum 0.001 km²

    def _get_candidate_precisions(
        self, geom_area: float, method: Union[str, int]
    ) -> List[int]:
        """Get list of candidate precisions to test."""
        min_precision, max_precision = self._grid._get_precision_range()

        # Estimate optimal precision based on area
        estimated = self._estimate_precision_for_area(geom_area)
        estimated = max(min_precision, min(max_precision, estimated))

        # Test range around estimated precision
        # OPTIMIZATION: Reduce test range from 3-4 to 2 levels for performance
        if isinstance(method, int) or method in ["auto", "balanced"]:
            # Test narrower range for count-based and quality methods
            test_range = 2  # Changed from 3
        elif method == "less":
            # Bias toward lower precisions (larger cells)
            test_range = 1  # Changed from 2
            estimated = max(min_precision, estimated - 1)
        else:  # method == "more"
            # Bias toward higher precisions (smaller cells)
            test_range = 1  # Changed from 2
            estimated = min(max_precision, estimated + 1)

        candidates = []
        for offset in range(-test_range, test_range + 1):
            p = estimated + offset
            if min_precision <= p <= max_precision:
                candidates.append(p)

        return sorted(candidates)

    def _estimate_precision_for_area(self, geom_area: float) -> int:
        """Estimate precision based on geometry area."""
        # Rough heuristic: target ~100 cells for the geometry
        target_cell_area = geom_area / 100

        # Binary search for precision
        min_p, max_p = self._grid._get_precision_range()

        while min_p < max_p:
            mid = (min_p + max_p) // 2
            test_cell = self._grid._get_grid(mid).get_cell_from_point(0, 0)

            if test_cell.area_km2 > target_cell_area:
                min_p = mid + 1
            else:
                max_p = mid

        return min_p

    def _find_precision_minimize_variance(
        self, geometry: Union[Polygon, MultiPolygon], candidates: List[int]
    ) -> int:
        """
        Find precision that minimizes coverage variance.

        This is the default 'auto' method based on user preference.
        """
        geom_area = self._calculate_area_km2(geometry)
        target_count = max(10, int(math.sqrt(geom_area) * 10))

        best_precision = candidates[0]
        best_score = float("inf")

        for precision in candidates:
            # Fast path: skip expensive geometry unions when the estimated
            # cell count is large. This keeps precision selection responsive.
            estimated_cells = self._estimate_cell_count(geom_area, precision)
            if estimated_cells > 50:
                count_deviation = abs(estimated_cells - target_count) / max(
                    target_count, 1
                )
                variance_score = count_deviation
                if variance_score < best_score:
                    best_score = variance_score
                    best_precision = precision
                continue

            # Get cells for this precision
            cells = self._get_cells_for_geometry(geometry, precision)
            if not cells:
                continue

            # Calculate coverage metrics
            cell_union = unary_union([c.polygon for c in cells])

            # Overlap (excess coverage)
            try:
                excess_geom = cell_union.difference(geometry)
                excess_area = self._calculate_area_km2(excess_geom)
            except Exception:
                excess_area = 0

            # Gap (missing coverage)
            try:
                gap_geom = geometry.difference(cell_union)
                gap_area = self._calculate_area_km2(gap_geom)
            except Exception:
                gap_area = 0

            # Cell count deviation
            cell_count = len(cells)
            count_deviation = abs(cell_count - target_count) / max(target_count, 1)

            # Calculate variance score
            # User preference: minimize variance (optimize for uniform coverage)
            overlap_ratio = excess_area / geom_area
            gap_ratio = gap_area / geom_area

            variance_score = (
                overlap_ratio * 0.3  # Penalize excess coverage
                + gap_ratio * 0.5  # Penalize gaps (more important)
                + count_deviation * 0.2  # Slight preference for target count
            )

            if variance_score < best_score:
                best_score = variance_score
                best_precision = precision

        return best_precision

    def _find_precision_fewer_cells(
        self, geometry: Union[Polygon, MultiPolygon], candidates: List[int]
    ) -> int:
        """Find precision with fewer, larger cells (10-50 cells)."""
        target_count = 30  # Middle of 10-50 range

        best_precision = candidates[0]
        best_deviation = float("inf")

        geom_area = self._calculate_area_km2(geometry)
        for precision in candidates:
            estimated = self._estimate_cell_count(geom_area, precision)
            if estimated > 50:
                count = estimated
            else:
                cells = self._get_cells_for_geometry(geometry, precision)
                count = len(cells)

            # Prefer counts in 10-50 range, bias toward lower end
            if count < 10:
                deviation = 10 - count
            elif count > 50:
                deviation = count - 50
            else:
                deviation = abs(count - target_count)

            if deviation < best_deviation:
                best_deviation = deviation
                best_precision = precision

        return best_precision

    def _find_precision_more_cells(
        self, geometry: Union[Polygon, MultiPolygon], candidates: List[int]
    ) -> int:
        """Find precision with more, smaller cells (200-1000 cells)."""
        target_count = 500  # Middle of 200-1000 range

        best_precision = candidates[-1]  # Start with highest precision
        best_deviation = float("inf")

        geom_area = self._calculate_area_km2(geometry)
        for precision in reversed(candidates):  # Test from high to low
            estimated = self._estimate_cell_count(geom_area, precision)
            if estimated > 50:
                count = estimated
            else:
                cells = self._get_cells_for_geometry(geometry, precision)
                count = len(cells)

            # Prefer counts in 200-1000 range, bias toward higher end
            if count < 200:
                deviation = 200 - count
            elif count > 1000:
                deviation = count - 1000
            else:
                deviation = abs(count - target_count)

            if deviation < best_deviation:
                best_deviation = deviation
                best_precision = precision

        return best_precision

    def _find_precision_balanced(
        self, geometry: Union[Polygon, MultiPolygon], candidates: List[int]
    ) -> int:
        """Find precision balancing coverage quality and cell count."""
        geom_area = self._calculate_area_km2(geometry)
        target_count = max(10, int(math.sqrt(geom_area) * 10))

        best_precision = candidates[0]
        best_score = float("inf")

        for precision in candidates:
            estimated_cells = self._estimate_cell_count(geom_area, precision)
            if estimated_cells > 50:
                count_deviation = abs(estimated_cells - target_count) / max(
                    target_count, 1
                )
                balanced_score = count_deviation
                if balanced_score < best_score:
                    best_score = balanced_score
                    best_precision = precision
                continue

            cells = self._get_cells_for_geometry(geometry, precision)
            if not cells:
                continue

            # Calculate coverage metrics
            cell_union = unary_union([c.polygon for c in cells])

            try:
                excess_area = self._calculate_area_km2(cell_union.difference(geometry))
                gap_area = self._calculate_area_km2(geometry.difference(cell_union))
            except Exception:
                excess_area = 0
                gap_area = 0

            cell_count = len(cells)
            count_deviation = abs(cell_count - target_count) / max(target_count, 1)

            # Balanced score: equal weights
            overlap_ratio = excess_area / geom_area
            gap_ratio = gap_area / geom_area

            balanced_score = (
                overlap_ratio * 0.33 + gap_ratio * 0.33 + count_deviation * 0.33
            )

            if balanced_score < best_score:
                best_score = balanced_score
                best_precision = precision

        return best_precision

    def _find_precision_for_count(
        self,
        geometry: Union[Polygon, MultiPolygon],
        target_count: int,
        candidates: List[int],
    ) -> int:
        """Find precision closest to target cell count."""
        best_precision = candidates[0]
        best_deviation = float("inf")

        geom_area = self._calculate_area_km2(geometry)
        for precision in candidates:
            estimated = self._estimate_cell_count(geom_area, precision)
            if estimated > 50:
                count = estimated
            else:
                cells = self._get_cells_for_geometry(geometry, precision)
                count = len(cells)
            deviation = abs(count - target_count)

            if deviation < best_deviation:
                best_deviation = deviation
                best_precision = precision

        return best_precision

    def _find_precision_for_count_fast(
        self,
        geometry: Union[Polygon, MultiPolygon],
        target_count: int,
        candidates: List[int],
    ) -> int:
        """Fast precision finding based on area estimation (for large geometries)."""
        geom_area = self._calculate_area_km2(geometry)
        target_cell_area = geom_area / target_count

        best_precision = candidates[0]
        best_error = float("inf")

        for precision in candidates:
            test_cell = self._grid._get_grid(precision).get_cell_from_point(0, 0)
            cell_area = test_cell.area_km2
            error = abs(cell_area - target_cell_area)

            if error < best_error:
                best_error = error
                best_precision = precision

        return best_precision

    def _estimate_cell_count(self, geom_area: float, precision: int) -> int:
        """Estimate number of cells for geometry area at precision."""
        try:
            test_cell = self._grid._get_grid(precision).get_cell_from_point(0, 0)
            if test_cell.area_km2 <= 0:
                return 0
            return int(geom_area / test_cell.area_km2)
        except Exception:
            return 0

    def _get_cells_for_geometry(
        self, geometry: Union[Polygon, MultiPolygon], precision: int
    ) -> List[Any]:
        """Get cells intersecting geometry at given precision."""
        # Convert geometry to GeoDataFrame
        gdf = gpd.GeoDataFrame({"geometry": [geometry]}, crs="EPSG:4326")

        # Get grid and find intersecting cells
        grid = self._grid._get_grid(precision)
        result_gdf = grid.intersects(gdf, use_spatial_index=False)

        # Convert to list of cells
        from ..base import GridCell

        cells = []
        for row in result_gdf.itertuples(index=False):
            cell = GridCell(
                identifier=row.cell_id, polygon=row.geometry, precision=row.precision
            )
            cells.append(cell)

        return cells
