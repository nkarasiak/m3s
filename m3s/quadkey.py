"""
Quadkey spatial grid implementation for M3S.

Quadkey is Microsoft's Bing Maps tile system that uses a hierarchical
quadtree to divide the world into tiles. Each tile is identified by a
string of digits (0, 1, 2, 3) representing the quadrant path from root.
"""

import math
from typing import override

import m3s_core
from shapely.geometry import Polygon

from .base import (
    CoreBackedGrid,
    GridCell,
    cell_from_core,
    cells_from_core_packed,
)


class QuadkeyGrid(CoreBackedGrid):
    """
    Quadkey spatial grid implementation.

    Based on Microsoft's Bing Maps tile system, this grid uses a quadtree
    to hierarchically divide the world into square tiles. Each tile is
    identified by a quadkey string where each digit (0-3) represents
    the quadrant chosen at each level of the tree.

    Attributes
    ----------
    precision : int
        Precision (zoom) level of the quadkey tiles (1-23)
    """

    KEY = "qk"
    GRID_NAME = "Quadkey"
    MIN_PRECISION = 1
    MAX_PRECISION = 23
    DEFAULT_PRECISION = 12

    def __init__(self, precision: int = 12):
        """
        Initialize Quadkey grid.

        Parameters
        ----------
        precision : int, optional
            Precision level for quadkey tiles (1-23), by default 12.
        """
        super().__init__(precision)

    def _pixel_to_lat_lon(self, px: int, py: int, map_size: int) -> tuple[float, float]:
        """
        Convert pixel coordinates to latitude/longitude.

        Parameters
        ----------
        px : int
            Pixel X coordinate
        py : int
            Pixel Y coordinate
        map_size : int
            Map size at current zoom level (256 << level)

        Returns
        -------
        tuple
            (latitude, longitude) in degrees
        """
        x = px / map_size - 0.5
        y = 0.5 - py / map_size

        lon = x * 360
        lat = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi

        return lat, lon

    def _quadkey_to_tile_xy(self, quadkey: str) -> tuple[int, int]:
        """
        Convert quadkey to tile XY coordinates.

        Parameters
        ----------
        quadkey : str
            Quadkey string

        Returns
        -------
        tuple
            Tile X and Y coordinates
        """
        tile_x = tile_y = 0
        level = len(quadkey)

        for i in range(level):
            bit = level - i
            mask = 1 << (bit - 1)
            digit = int(quadkey[i])

            if digit & 1:
                tile_x |= mask
            if digit & 2:
                tile_y |= mask

        return tile_x, tile_y

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its quadkey identifier.

        Parameters
        ----------
        identifier : str
            The quadkey identifier

        Returns
        -------
        GridCell
            The grid cell corresponding to the identifier
        """
        if len(identifier) != self.precision:
            raise ValueError(
                "Quadkey length "
                f"{len(identifier)} does not match grid level {self.precision}"
            )

        # Validate quadkey contains only digits 0-3
        if not all(c in "0123" for c in identifier):
            raise ValueError("Quadkey must contain only digits 0, 1, 2, 3")

        return cell_from_core(m3s_core.qk_cell_from_id(identifier))

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get child cells at the next zoom level.

        Parameters
        ----------
        cell : GridCell
            Parent cell

        Returns
        -------
        list[GridCell]
            List of 4 child cells
        """
        if self.precision >= self.MAX_PRECISION:
            return []  # No children at maximum level

        return cells_from_core_packed(m3s_core.qk_children(cell.identifier))

    def _create_tile_polygon_for_level(
        self, tile_x: int, tile_y: int, level: int
    ) -> Polygon:
        """
        Create a polygon for the given tile coordinates at a specific level.

        Parameters
        ----------
        tile_x : int
            Tile X coordinate
        tile_y : int
            Tile Y coordinate
        level : int
            Zoom level

        Returns
        -------
        Polygon
            Shapely polygon representing the tile bounds
        """
        map_size = 256 << level

        # Calculate pixel coordinates for tile bounds
        min_pixel_x = tile_x * 256
        max_pixel_x = (tile_x + 1) * 256
        min_pixel_y = tile_y * 256
        max_pixel_y = (tile_y + 1) * 256

        # Convert to lat/lon using class method
        min_lat, min_lon = self._pixel_to_lat_lon(min_pixel_x, max_pixel_y, map_size)
        max_lat, max_lon = self._pixel_to_lat_lon(max_pixel_x, min_pixel_y, map_size)

        return Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get parent cell at the previous zoom level.

        Parameters
        ----------
        cell : GridCell
            Child cell

        Returns
        -------
        GridCell
            Parent cell
        """
        if len(cell.identifier) <= self.MIN_PRECISION:
            raise ValueError("Cell has no parent (already at root level)")

        return cell_from_core(m3s_core.qk_parent(cell.identifier))

    def get_quadkey_bounds(self, quadkey: str) -> tuple[float, float, float, float]:
        """
        Get the latitude/longitude bounds of a quadkey.

        Parameters
        ----------
        quadkey : str
            Quadkey identifier

        Returns
        -------
        tuple
            Bounds as (min_lat, min_lon, max_lat, max_lon)
        """
        tile_x, tile_y = self._quadkey_to_tile_xy(quadkey)
        level = len(quadkey)

        map_size = 256 << level

        # Calculate pixel coordinates for tile bounds
        min_pixel_x = tile_x * 256
        max_pixel_x = (tile_x + 1) * 256
        min_pixel_y = tile_y * 256
        max_pixel_y = (tile_y + 1) * 256

        # Convert to lat/lon using class method
        min_lat, min_lon = self._pixel_to_lat_lon(min_pixel_x, max_pixel_y, map_size)
        max_lat, max_lon = self._pixel_to_lat_lon(max_pixel_x, min_pixel_y, map_size)

        return min_lat, min_lon, max_lat, max_lon

    def __repr__(self) -> str:
        return f"QuadkeyGrid(precision={self.precision})"
