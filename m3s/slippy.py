"""
Slippy Map Tiling grid implementation for M3S.

Slippy Map Tiles are the standard web mapping tiles used by OpenStreetMap,
Google Maps, and most web mapping services. They use a Web Mercator projection
(EPSG:3857) and a quadtree-like z/x/y coordinate system.
"""

from typing import override

import m3s_core
from shapely.geometry import Polygon

from .base import (
    CoreBackedGrid,
    GridCell,
    cell_from_core,
    cells_from_core_packed,
)


class SlippyGrid(CoreBackedGrid):
    """
    Slippy Map Tiling grid implementation.

    Based on the standard web map tile system used by OpenStreetMap, Google Maps,
    and other web mapping services. Uses Web Mercator projection (EPSG:3857) with
    256×256 pixel tiles organized in a z/x/y coordinate system.

    Attributes
    ----------
    precision : int
        Precision (zoom) level (0-22), where higher values provide smaller tiles
    """

    KEY = "sl"
    GRID_NAME = "Slippy"
    MIN_PRECISION = 0
    MAX_PRECISION = 22
    DEFAULT_PRECISION = 12

    def __init__(self, precision: int = 12):
        """
        Initialize Slippy Map Tiling grid.

        Parameters
        ----------
        precision : int, optional
            Precision (zoom) level (0-22), by default 12.
            Precision 0: 1 tile covering the world
            Precision 1: 2×2 = 4 tiles
            Precision 10: 1024×1024 = ~1M tiles (~40km tiles)
            Precision 15: 32768×32768 = ~1B tiles (~1.2km tiles)
            Precision 18: 262144×262144 tiles (~150m tiles)
        """
        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of Slippy Map tiles.

        At this zoom level, returns the area in square kilometers.

        Returns
        -------
        float
            Theoretical area in square kilometers for tiles at this zoom level
        """
        # Slippy tiles are squares in Web Mercator projection
        # At zoom level z, there are 2^z × 2^z tiles

        # Earth's circumference in Web Mercator projection (at equator)
        earth_circumference_km = 40075.0

        # Number of tiles at this zoom level
        tiles_per_side = 2**self.precision

        # Size of each tile
        tile_size_km = earth_circumference_km / tiles_per_side

        # Area (square)
        return float(tile_size_km * tile_size_km)

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a tile from its z/x/y identifier.

        Parameters
        ----------
        identifier : str
            The tile identifier in "z/x/y" format

        Returns
        -------
        GridCell
            The tile corresponding to the identifier
        """
        try:
            return cell_from_core(m3s_core.sl_cell_from_id(identifier))
        except Exception as e:
            raise ValueError(f"Invalid Slippy tile identifier: {identifier}") from e

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get child tiles at the next zoom level.

        Parameters
        ----------
        cell : GridCell
            Parent tile

        Returns
        -------
        list[GridCell]
            List of 4 child tiles
        """
        if self.precision >= 22:
            return []  # No children at maximum zoom

        try:
            return cells_from_core_packed(m3s_core.sl_children(cell.identifier))
        except ValueError:
            return []

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get parent tile at the previous zoom level.

        Parameters
        ----------
        cell : GridCell
            Child tile

        Returns
        -------
        GridCell
            Parent tile

        Raises
        ------
        ValueError
            If the tile is already at the coarsest zoom level (0).
        """
        if self.precision <= 0:
            raise ValueError("Tile has no parent (already at zoom 0)")

        return cell_from_core(m3s_core.sl_parent(cell.identifier))

    def get_covering_cells(
        self, polygon: Polygon, max_cells: int = 100
    ) -> list[GridCell]:
        """
        Get Slippy Map tiles that cover the given polygon.

        Parameters
        ----------
        polygon : Polygon
            Shapely polygon to cover
        max_cells : int
            Maximum number of tiles to return

        Returns
        -------
        list[GridCell]
            List of tiles covering the polygon
        """
        # Use bounding box approach for Slippy tiles
        bounds = polygon.bounds
        min_lon, min_lat, max_lon, max_lat = bounds

        candidate_tiles = self.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        # Filter tiles that actually intersect the polygon
        intersecting_tiles = [
            tile for tile in candidate_tiles if tile.polygon.intersects(polygon)
        ]

        # Limit to max_cells
        return intersecting_tiles[:max_cells]

    def __repr__(self) -> str:
        return f"SlippyGrid(precision={self.precision})"
