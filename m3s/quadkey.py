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

from .base import BaseGrid, GridCell, cell_from_core


class QuadkeyGrid(BaseGrid):
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
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"Quadkey precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )

        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of Quadkey tiles at this level in square kilometers.

        Returns
        -------
        float
            Theoretical area in square kilometers for tiles at this level
        """
        # Quadkey tiles are squares in Web Mercator projection
        # At each level, tiles are half the size in each dimension
        # Level 1: 2×2 tiles, Level 2: 4×4 tiles, etc.

        # Earth's circumference in Web Mercator projection
        earth_circumference_km = 40075.0  # At equator

        # Number of tiles at this level (2^level × 2^level)
        tiles_per_side = 2**self.precision

        # Size of each tile
        tile_size_km = earth_circumference_km / tiles_per_side

        # Area (square)
        return tile_size_km * tile_size_km

    def _lat_lon_to_pixel_xy(self, lat: float, lon: float) -> tuple[int, int]:
        """
        Convert latitude/longitude to pixel XY coordinates.

        Parameters
        ----------
        lat : float
            Latitude in degrees
        lon : float
            Longitude in degrees

        Returns
        -------
        tuple
            Pixel X and Y coordinates
        """
        # Clip latitude to valid range
        lat = max(-85.05112878, min(85.05112878, lat))

        # Convert to radians
        lat_rad = lat * math.pi / 180
        lon_rad = lon * math.pi / 180

        # Map size at this zoom level
        map_size = 256 << self.precision

        # Convert to pixel coordinates
        x = (lon_rad + math.pi) / (2 * math.pi)
        y = (math.pi - math.log(math.tan(math.pi / 4 + lat_rad / 2))) / (2 * math.pi)

        pixel_x = int(x * map_size)
        pixel_y = int(y * map_size)

        # Clip to valid range
        pixel_x = max(0, min(map_size - 1, pixel_x))
        pixel_y = max(0, min(map_size - 1, pixel_y))

        return pixel_x, pixel_y

    def _pixel_xy_to_tile_xy(self, pixel_x: int, pixel_y: int) -> tuple[int, int]:
        """
        Convert pixel XY coordinates to tile XY coordinates.

        Parameters
        ----------
        pixel_x : int
            Pixel X coordinate
        pixel_y : int
            Pixel Y coordinate

        Returns
        -------
        tuple
            Tile X and Y coordinates
        """
        tile_x = pixel_x // 256
        tile_y = pixel_y // 256
        return tile_x, tile_y

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

    def _tile_xy_to_quadkey(self, tile_x: int, tile_y: int) -> str:
        """
        Convert tile XY coordinates to quadkey.

        Parameters
        ----------
        tile_x : int
            Tile X coordinate
        tile_y : int
            Tile Y coordinate

        Returns
        -------
        str
            Quadkey string
        """
        quadkey = []

        for i in range(self.precision, 0, -1):
            digit = 0
            mask = 1 << (i - 1)

            if (tile_x & mask) != 0:
                digit += 1
            if (tile_y & mask) != 0:
                digit += 2

            quadkey.append(str(digit))

        return "".join(quadkey)

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

    def _tile_xy_to_lat_lon_bounds(
        self, tile_x: int, tile_y: int
    ) -> tuple[float, float, float, float]:
        """
        Convert tile XY coordinates to latitude/longitude bounds.

        Parameters
        ----------
        tile_x : int
            Tile X coordinate
        tile_y : int
            Tile Y coordinate

        Returns
        -------
        tuple
            Bounds as (min_lat, min_lon, max_lat, max_lon)
        """
        map_size = 256 << self.precision

        # Calculate pixel coordinates for tile bounds
        min_pixel_x = tile_x * 256
        max_pixel_x = (tile_x + 1) * 256
        min_pixel_y = tile_y * 256
        max_pixel_y = (tile_y + 1) * 256

        # Convert to lat/lon using class method
        min_lat, min_lon = self._pixel_to_lat_lon(min_pixel_x, max_pixel_y, map_size)
        max_lat, max_lon = self._pixel_to_lat_lon(max_pixel_x, min_pixel_y, map_size)

        return min_lat, min_lon, max_lat, max_lon

    def _create_tile_polygon(self, tile_x: int, tile_y: int) -> Polygon:
        """
        Create a polygon for the given tile coordinates.

        Parameters
        ----------
        tile_x : int
            Tile X coordinate
        tile_y : int
            Tile Y coordinate

        Returns
        -------
        Polygon
            Shapely polygon representing the tile bounds
        """
        min_lat, min_lon, max_lat, max_lon = self._tile_xy_to_lat_lon_bounds(
            tile_x, tile_y
        )

        return Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )

    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the quadkey cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        GridCell
            The grid cell containing the specified point
        """
        return cell_from_core(m3s_core.qk_cell_from_point(lat, lon, self.precision))

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

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring cells of the given cell.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring grid cells (up to 8 neighbors)
        """
        return [cell_from_core(n) for n in m3s_core.qk_neighbors(cell.identifier)]

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

        return [cell_from_core(c) for c in m3s_core.qk_children(cell.identifier)]

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

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Get all grid cells within the given bounding box.

        Parameters
        ----------
        min_lat : float
            Minimum latitude of bounding box
        min_lon : float
            Minimum longitude of bounding box
        max_lat : float
            Maximum latitude of bounding box
        max_lon : float
            Maximum longitude of bounding box

        Returns
        -------
        list[GridCell]
            List of grid cells that intersect the bounding box
        """
        # Convert corners to tile coordinates
        min_pixel_x, max_pixel_y = self._lat_lon_to_pixel_xy(min_lat, min_lon)
        max_pixel_x, min_pixel_y = self._lat_lon_to_pixel_xy(max_lat, max_lon)

        min_tile_x, max_tile_y = self._pixel_xy_to_tile_xy(min_pixel_x, max_pixel_y)
        max_tile_x, min_tile_y = self._pixel_xy_to_tile_xy(max_pixel_x, min_pixel_y)

        cells = []

        for tile_x in range(min_tile_x, max_tile_x + 1):
            for tile_y in range(min_tile_y, max_tile_y + 1):
                # Check if tile is within valid range
                max_tile = (1 << self.precision) - 1
                if 0 <= tile_x <= max_tile and 0 <= tile_y <= max_tile:
                    quadkey = self._tile_xy_to_quadkey(tile_x, tile_y)
                    polygon = self._create_tile_polygon(tile_x, tile_y)
                    cells.append(GridCell(quadkey, polygon, self.precision))

        return cells

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

    def __repr__(self):
        return f"QuadkeyGrid(precision={self.precision})"
