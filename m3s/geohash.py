"""
Geohash grid implementation.
"""

from typing import Any, override

import m3s_core

from .base import (
    CoreBackedGrid,
    GridCell,
    cell_from_core,
    cells_from_core_packed,
)
from .cache import cached_method, cell_cache_key, geo_cache_key
from .projection_utils import get_utm_epsg_code


class GeohashGrid(CoreBackedGrid):
    """
    Geohash-based spatial grid system.

    Implements the Geohash spatial indexing system using base-32
    encoding to create hierarchical rectangular grid cells.
    """

    KEY = "gh"
    GRID_NAME = "Geohash"
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
        return cells_from_core_packed(m3s_core.gh_neighbors(cell.identifier))

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
        return cells_from_core_packed(m3s_core.gh_children(cell.identifier))

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
