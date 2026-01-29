"""
Multi-grid comparison utilities for analyzing different grid systems.

Enables simultaneous querying and analysis across multiple grid systems
to understand their relative characteristics and coverage patterns.
"""

from typing import Dict, List, Tuple

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

from ..base import GridCell
from .builder import GridBuilder
from .parameters import ParameterNormalizer
from .precision import AreaCalculator


class MultiGridComparator:
    """
    Compare and analyze multiple grid systems simultaneously.

    Provides utilities for querying the same location across different
    grid systems, comparing coverage characteristics, and analyzing
    precision equivalence.

    Examples
    --------
    >>> comparator = MultiGridComparator([
    ...     ('geohash', 5),
    ...     ('h3', 7),
    ...     ('s2', 10)
    ... ])
    >>> results = comparator.query_all(40.7128, -74.0060)
    >>> df = comparator.compare_coverage((40.7, -74.1, 40.8, -73.9))
    """

    def __init__(self, grid_configs: List[Tuple[str, int]]):
        """
        Initialize comparator with grid system configurations.

        Parameters
        ----------
        grid_configs : List[Tuple[str, int]]
            List of (grid_system, precision) tuples to compare
        """
        self.grid_configs = grid_configs
        self._validate_configs()

    def _validate_configs(self) -> None:
        """Validate all grid configurations."""
        for system, precision in self.grid_configs:
            ParameterNormalizer.validate_precision(system, precision)

    def query_all(self, latitude: float, longitude: float) -> Dict[str, GridCell]:
        """
        Query same point across all configured grid systems.

        Parameters
        ----------
        latitude : float
            Latitude in decimal degrees
        longitude : float
            Longitude in decimal degrees

        Returns
        -------
        Dict[str, GridCell]
            Map of grid_system -> GridCell at that location
        """
        results = {}

        for system, precision in self.grid_configs:
            result = (
                GridBuilder.for_system(system)
                .with_precision(precision)
                .at_point(latitude, longitude)
                .execute()
            )
            results[system] = result.single

        return results

    def query_all_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
    ) -> Dict[str, List[GridCell]]:
        """
        Query bounding box across all configured grid systems.

        Parameters
        ----------
        min_lat : float
            Minimum latitude
        min_lon : float
            Minimum longitude
        max_lat : float
            Maximum latitude
        max_lon : float
            Maximum longitude

        Returns
        -------
        Dict[str, List[GridCell]]
            Map of grid_system -> list of cells in bbox
        """
        results = {}

        for system, precision in self.grid_configs:
            result = (
                GridBuilder.for_system(system)
                .with_precision(precision)
                .in_bbox(min_lat, min_lon, max_lat, max_lon)
                .execute()
            )
            results[system] = result.many

        return results

    def compare_coverage(
        self,
        bounds: Tuple[float, float, float, float],
    ) -> pd.DataFrame:
        """
        Compare coverage characteristics across grid systems for a region.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box (min_lat, min_lon, max_lat, max_lon)

        Returns
        -------
        pd.DataFrame
            Comparison table with columns: system, precision, cell_count,
            total_area_km2, avg_cell_size_km2, coverage_efficiency
        """
        min_lat, min_lon, max_lat, max_lon = bounds

        rows = []
        for system, precision in self.grid_configs:
            result = (
                GridBuilder.for_system(system)
                .with_precision(precision)
                .in_bbox(min_lat, min_lon, max_lat, max_lon)
                .execute()
            )

            cells = result.many
            cell_count = len(cells)

            if cell_count > 0:
                total_area = sum(cell.area_km2 for cell in cells)
                avg_area = total_area / cell_count
            else:
                total_area = 0.0
                avg_area = 0.0

            # Calculate region area for coverage efficiency
            # Haversine approximation
            import math

            center_lat = (min_lat + max_lat) / 2
            lat_km = (max_lat - min_lat) * 111.32
            lon_km = (max_lon - min_lon) * 111.32 * math.cos(math.radians(center_lat))
            region_area = lat_km * lon_km

            coverage_efficiency = (total_area / region_area) if region_area > 0 else 0.0

            rows.append(
                {
                    "system": system,
                    "precision": precision,
                    "cell_count": cell_count,
                    "total_area_km2": total_area,
                    "avg_cell_size_km2": avg_area,
                    "region_area_km2": region_area,
                    "coverage_efficiency": coverage_efficiency,
                }
            )

        return pd.DataFrame(rows)

    def analyze_precision_equivalence(self) -> pd.DataFrame:
        """
        Analyze area-based precision equivalence across all systems.

        Returns
        -------
        pd.DataFrame
            Table showing which precisions are approximately equivalent
            across grid systems based on average cell area
        """
        rows = []

        for system, precision in self.grid_configs:
            calc = AreaCalculator(system)
            area = calc.get_area(precision)

            # Find equivalent precisions in other systems
            equivalents = ParameterNormalizer.get_equivalent_precisions(
                system, precision
            )

            row = {
                "system": system,
                "precision": precision,
                "area_km2": area,
            }

            # Add equivalent precisions for each system
            for other_system, equiv_precision in equivalents.items():
                if other_system != system:
                    row[f"equiv_{other_system}"] = equiv_precision

            rows.append(row)

        return pd.DataFrame(rows)

    def compare_point_coverage(
        self, latitude: float, longitude: float
    ) -> gpd.GeoDataFrame:
        """
        Visualize how different grid systems cover the same point.

        Parameters
        ----------
        latitude : float
            Latitude in decimal degrees
        longitude : float
            Longitude in decimal degrees

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with one row per grid system showing cell geometries
        """
        results = self.query_all(latitude, longitude)

        rows = []
        for system, cell in results.items():
            precision = next(p for s, p in self.grid_configs if s == system)
            rows.append(
                {
                    "system": system,
                    "precision": precision,
                    "identifier": cell.identifier,
                    "area_km2": cell.area_km2,
                    "geometry": cell.polygon,
                }
            )

        gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

        # Add the query point as well
        point_row = {
            "system": "query_point",
            "precision": None,
            "identifier": f"({latitude}, {longitude})",
            "area_km2": 0.0,
            "geometry": Point(longitude, latitude),
        }
        point_gdf = gpd.GeoDataFrame([point_row], geometry="geometry", crs="EPSG:4326")

        return pd.concat([gdf, point_gdf], ignore_index=True)

    def get_summary_statistics(self) -> pd.DataFrame:
        """
        Get summary statistics for all configured grid systems.

        Returns
        -------
        pd.DataFrame
            Summary statistics including avg cell area, precision range, etc.
        """
        rows = []

        for system, precision in self.grid_configs:
            calc = AreaCalculator(system)
            area = calc.get_area(precision)
            min_p, max_p = ParameterNormalizer.get_range(system)

            # Estimate edge length (approximate)
            edge_length_km = area**0.5  # Rough estimate

            rows.append(
                {
                    "system": system,
                    "precision": precision,
                    "avg_area_km2": area,
                    "approx_edge_km": edge_length_km,
                    "min_precision": min_p,
                    "max_precision": max_p,
                    "precision_description": ParameterNormalizer.describe_precision(
                        system, precision
                    ),
                }
            )

        return pd.DataFrame(rows)

    def find_optimal_precision_for_area(self, target_area_km2: float) -> pd.DataFrame:
        """
        Find optimal precision in each grid system for target area.

        Parameters
        ----------
        target_area_km2 : float
            Target cell area in km²

        Returns
        -------
        pd.DataFrame
            Recommendations for each grid system
        """
        from .precision import PrecisionSelector

        rows = []

        # Get all unique grid systems from configs
        systems = list(set(system for system, _ in self.grid_configs))

        for system in systems:
            selector = PrecisionSelector(system)
            rec = selector.for_area(target_area_km2)

            rows.append(
                {
                    "system": system,
                    "recommended_precision": rec.precision,
                    "actual_area_km2": rec.actual_area_km2,
                    "confidence": rec.confidence,
                    "explanation": rec.explanation,
                }
            )

        return pd.DataFrame(rows)

    def visualize_coverage(
        self,
        bounds: Tuple[float, float, float, float],
        max_cells_per_system: int = 100,
    ) -> gpd.GeoDataFrame:
        """
        Create visualization-ready GeoDataFrame showing all grid coverages.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box (min_lat, min_lon, max_lat, max_lon)
        max_cells_per_system : int, optional
            Limit cells per system to avoid overwhelming visualizations

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with all cells from all systems
        """
        min_lat, min_lon, max_lat, max_lon = bounds

        all_cells = []

        for system, precision in self.grid_configs:
            result = (
                GridBuilder.for_system(system)
                .with_precision(precision)
                .in_bbox(min_lat, min_lon, max_lat, max_lon)
                .limit(max_cells_per_system)
                .execute()
            )

            for cell in result.many:
                all_cells.append(
                    {
                        "system": system,
                        "precision": precision,
                        "identifier": cell.identifier,
                        "area_km2": cell.area_km2,
                        "geometry": cell.polygon,
                    }
                )

        gdf = gpd.GeoDataFrame(all_cells, geometry="geometry", crs="EPSG:4326")

        # Add bounding box for reference
        bbox_geom = box(min_lon, min_lat, max_lon, max_lat)
        bbox_row = {
            "system": "bbox",
            "precision": None,
            "identifier": "query_region",
            "area_km2": 0.0,
            "geometry": bbox_geom,
        }
        bbox_gdf = gpd.GeoDataFrame([bbox_row], geometry="geometry", crs="EPSG:4326")

        return pd.concat([gdf, bbox_gdf], ignore_index=True)

    def __repr__(self) -> str:
        """Return string representation."""
        configs = ", ".join(f"{sys}@{prec}" for sys, prec in self.grid_configs)
        return f"MultiGridComparator([{configs}])"
