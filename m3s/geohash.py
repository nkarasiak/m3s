"""
Geohash grid implementation.
"""

from typing import Any, override

import m3s_core
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell, cell_from_core
from .cache import cached_method, cell_cache_key, geo_cache_key
from .projection_utils import get_utm_epsg_code


class GeohashGrid(BaseGrid):
    """
    Geohash-based spatial grid system.

    Implements the Geohash spatial indexing system using base-32
    encoding to create hierarchical rectangular grid cells.
    """

    MIN_PRECISION = 1
    MAX_PRECISION = 12
    DEFAULT_PRECISION = 5

    def __init__(self, precision: int = 5):
        """
        Initialize GeohashGrid.

        Parameters
        ----------
        precision : int, optional
            Geohash precision level (1-12), by default 5.
            Higher values mean smaller cells.

        Raises
        ------
        ValueError
            If precision is not between 1 and 12
        """
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"Geohash precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )
        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of Geohash cells at this precision.

        Returns
        -------
        float
            Theoretical area in square kilometers for cells at this precision
        """
        # Approximate area calculation based on geohash precision
        # These are approximate areas as geohash cells vary by latitude
        # Values are for mid-latitudes (~45°)
        areas = {
            1: 5009400.0,  # ~5M km² (continent scale)
            2: 1252350.0,  # ~1.25M km²
            3: 156540.0,  # ~156k km²
            4: 39135.0,  # ~39k km² (country scale)
            5: 4892.0,  # ~4.9k km²
            6: 1223.0,  # ~1.2k km² (state scale)
            7: 153.0,  # ~153 km²
            8: 38.0,  # ~38 km² (city scale)
            9: 4.8,  # ~4.8 km²
            10: 1.2,  # ~1.2 km² (neighborhood scale)
            11: 0.15,  # ~0.15 km²
            12: 0.037,  # ~0.037 km² (building scale)
        }
        return areas.get(self.precision, 4892.0)  # Default to precision 5

    @cached_method(cache_key_func=geo_cache_key)
    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the geohash cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        GridCell
            The geohash grid cell containing the specified point
        """
        return cell_from_core(m3s_core.gh_cell_from_point(lat, lon, self.precision))

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a geohash cell from its identifier.

        Parameters
        ----------
        identifier : str
            The geohash string identifier

        Returns
        -------
        GridCell
            The geohash grid cell with rectangular geometry
        """
        return cell_from_core(m3s_core.gh_cell_from_id(identifier))

    @cached_method(cache_key_func=cell_cache_key)
    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring geohash cells.

        Parameters
        ----------
        cell : GridCell
            The geohash cell for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring geohash cells
        """
        return [cell_from_core(n) for n in m3s_core.gh_neighbors(cell.identifier)]

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """Get all geohash cells within the given bounding box."""
        cells = set()  # Use set to avoid duplicates

        lat_step = self._get_lat_step()
        lon_step = self._get_lon_step()

        # Extend the sampling area to catch cells that intersect the boundary
        # but whose centers might be outside the bbox
        lat_margin = lat_step * 1.5
        lon_margin = lon_step * 1.5

        extended_min_lat = min_lat - lat_margin
        extended_max_lat = max_lat + lat_margin
        extended_min_lon = min_lon - lon_margin
        extended_max_lon = max_lon + lon_margin

        # Use denser sampling to ensure we don't miss cells
        dense_lat_step = lat_step / 3
        dense_lon_step = lon_step / 3

        # Cap total sample points to keep runtime bounded at high precision.
        lat_range = extended_max_lat - extended_min_lat
        lon_range = extended_max_lon - extended_min_lon
        lat_steps = max(2, int(lat_range / dense_lat_step))
        lon_steps = max(2, int(lon_range / dense_lon_step))
        total_points = (lat_steps + 1) * (lon_steps + 1)
        max_points = 4000
        if total_points > max_points:
            scale = (max_points / total_points) ** 0.5
            if scale > 0:
                dense_lat_step /= scale
                dense_lon_step /= scale

        lat = extended_min_lat
        while lat <= extended_max_lat:
            lon = extended_min_lon
            while lon <= extended_max_lon:
                try:
                    cell = self.get_cell_from_point(lat, lon)
                    # Check if cell actually intersects with the original bbox
                    bbox_polygon = Polygon(
                        [
                            (min_lon, min_lat),
                            (max_lon, min_lat),
                            (max_lon, max_lat),
                            (min_lon, max_lat),
                            (min_lon, min_lat),
                        ]
                    )
                    if cell.polygon.intersects(bbox_polygon):
                        cells.add(cell)
                except Exception:
                    # Skip invalid geohash cells at boundary conditions
                    pass
                lon += dense_lon_step
            lat += dense_lat_step

        return list(set(cells))

    def _get_lat_step(self) -> float:
        """Get approximate latitude step for the current precision."""
        lat_bits = (self.precision * 5 + 1) // 2
        return 180.0 / (2**lat_bits)

    def _get_lon_step(self) -> float:
        """Get approximate longitude step for the current precision."""
        lon_bits = (self.precision * 5) // 2
        return 360.0 / (2**lon_bits)

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get the 32 child cells one precision level finer.

        Geohash is natively hierarchical: a child is the parent identifier with
        one more base-32 character appended, and the 32 children exactly tile
        the parent.

        Parameters
        ----------
        cell : GridCell
            Parent cell.

        Returns
        -------
        list[GridCell]
            The 32 children, or an empty list if already at the finest
            precision (12).
        """
        if len(cell.identifier) >= self.MAX_PRECISION:
            return []
        return [cell_from_core(c) for c in m3s_core.gh_children(cell.identifier)]

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get the parent cell one precision level coarser.

        Parameters
        ----------
        cell : GridCell
            Child cell.

        Returns
        -------
        GridCell
            The parent cell (identifier with the last character dropped).

        Raises
        ------
        ValueError
            If the cell is already at the coarsest precision (1).
        """
        if len(cell.identifier) <= self.MIN_PRECISION:
            raise ValueError(
                "Cell has no parent (already at the coarsest geohash precision)"
            )
        return cell_from_core(m3s_core.gh_parent(cell.identifier))

    def expand_cell(self, cell: GridCell) -> list[GridCell]:
        """
        Expand a geohash cell to higher precision cells contained within it.

        Thin wrapper over :meth:`get_children` that returns the cell unchanged
        when it is already at the finest precision.

        Args:
            cell: The cell to expand

        Returns
        -------
            List of higher precision cells
        """
        children = self.get_children(cell)
        return children if children else [cell]

    @override
    def _get_additional_columns(self, cell: GridCell) -> dict[str, Any]:
        """
        Add UTM zone column for Geohash cells.

        Parameters
        ----------
        cell : GridCell
            The grid cell to extract UTM data from

        Returns
        -------
        dict
            Dictionary with 'utm' column
        """
        if not cell.identifier or cell.polygon.is_empty:
            return {}

        centroid = cell.polygon.centroid
        utm_epsg = get_utm_epsg_code(centroid.y, centroid.x)
        return {"utm": utm_epsg}
