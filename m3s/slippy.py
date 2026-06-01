"""
Slippy Map Tiling grid implementation for M3S.

Slippy Map Tiles are the standard web mapping tiles used by OpenStreetMap,
Google Maps, and most web mapping services. They use a Web Mercator projection
(EPSG:3857) and a quadtree-like z/x/y coordinate system.
"""

import math
from typing import override

from shapely.geometry import Polygon

from .base import BaseGrid, GridCell


class SlippyGrid(BaseGrid):
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
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"Slippy precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )

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
        return tile_size_km * tile_size_km

    def _deg2num(self, lat: float, lon: float) -> tuple[int, int]:
        """
        Convert latitude/longitude to tile numbers.

        Parameters
        ----------
        lat : float
            Latitude in degrees
        lon : float
            Longitude in degrees

        Returns
        -------
        tuple
            Tile X and Y coordinates
        """
        lat_rad = math.radians(lat)
        n = 2.0**self.precision

        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

        return x, y

    def _num2deg(self, x: int, y: int) -> tuple[float, float, float, float]:
        """
        Convert tile numbers to bounding box coordinates.

        Parameters
        ----------
        x : int
            Tile X coordinate
        y : int
            Tile Y coordinate

        Returns
        -------
        tuple
            Bounding box as (min_lon, min_lat, max_lon, max_lat)
        """
        n = 2.0**self.precision

        lon_min = x / n * 360.0 - 180.0
        lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))

        lon_max = (x + 1) / n * 360.0 - 180.0
        lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))

        return lon_min, lat_min, lon_max, lat_max

    def _create_tile_polygon(self, x: int, y: int) -> Polygon:
        """
        Create a Shapely polygon for a tile.

        Parameters
        ----------
        x : int
            Tile X coordinate
        y : int
            Tile Y coordinate

        Returns
        -------
        Polygon
            Polygon representing the tile boundary
        """
        min_lon, min_lat, max_lon, max_lat = self._num2deg(x, y)

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
        Get the Slippy Map tile containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        GridCell
            The tile containing the specified point
        """
        x, y = self._deg2num(lat, lon)

        # Create tile identifier in z/x/y format
        identifier = f"{self.precision}/{x}/{y}"

        polygon = self._create_tile_polygon(x, y)

        return GridCell(identifier, polygon, self.precision)

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
            parts = identifier.split("/")
            if len(parts) != 3:
                raise ValueError("Invalid format")

            z, x, y = map(int, parts)

            if z != self.precision:
                raise ValueError(
                    f"Zoom level mismatch: expected {self.precision}, got {z}"
                )

            # Validate tile coordinates
            max_coord = 2**z
            if not (0 <= x < max_coord and 0 <= y < max_coord):
                raise ValueError(f"Invalid tile coordinates for zoom {z}")

            polygon = self._create_tile_polygon(x, y)

            return GridCell(identifier, polygon, z)
        except Exception as e:
            raise ValueError(f"Invalid Slippy tile identifier: {identifier}") from e

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring tiles of the given tile.

        Parameters
        ----------
        cell : GridCell
            The tile for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring tiles (up to 8 neighbors)
        """
        try:
            parts = cell.identifier.split("/")
            z, x, y = map(int, parts)

            neighbors = []
            max_coord = 2**z

            # Check all 8 surrounding tiles
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue  # Skip the tile itself

                    new_x = x + dx
                    new_y = y + dy

                    # Check boundaries (tiles wrap around horizontally but not
                    # vertically).
                    if 0 <= new_y < max_coord:
                        # Handle horizontal wrapping
                        new_x = new_x % max_coord

                        neighbor_id = f"{z}/{new_x}/{new_y}"
                        neighbor_polygon = self._create_tile_polygon(new_x, new_y)
                        neighbors.append(GridCell(neighbor_id, neighbor_polygon, z))

            return neighbors
        except Exception:
            return []

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
            parts = cell.identifier.split("/")
            z, x, y = map(int, parts)

            children = []
            child_zoom = z + 1

            # Each tile has 4 children at the next zoom level
            for dx in [0, 1]:
                for dy in [0, 1]:
                    child_x = x * 2 + dx
                    child_y = y * 2 + dy

                    child_id = f"{child_zoom}/{child_x}/{child_y}"
                    child_polygon = self._create_tile_polygon(child_x, child_y)
                    children.append(GridCell(child_id, child_polygon, child_zoom))

            return children
        except Exception:
            return []

    def get_parent(self, cell: GridCell) -> GridCell | None:
        """
        Get parent tile at the previous zoom level.

        Parameters
        ----------
        cell : GridCell
            Child tile

        Returns
        -------
        GridCell | None
            Parent tile, or None if already at zoom 0
        """
        if self.precision <= 0:
            return None

        try:
            parts = cell.identifier.split("/")
            z, x, y = map(int, parts)

            parent_zoom = z - 1
            parent_x = x // 2
            parent_y = y // 2

            parent_id = f"{parent_zoom}/{parent_x}/{parent_y}"
            parent_polygon = self._create_tile_polygon(parent_x, parent_y)

            return GridCell(parent_id, parent_polygon, parent_zoom)
        except Exception:
            return None

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Get all tiles within the given bounding box.

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
            List of tiles that intersect the bounding box
        """
        try:
            # Get tile coordinates for corners
            x_min, y_max = self._deg2num(max_lat, min_lon)  # Note: y is flipped
            x_max, y_min = self._deg2num(min_lat, max_lon)

            # Ensure we have valid ranges
            max_coord = 2**self.precision
            x_min = max(0, min(x_min, max_coord - 1))
            x_max = max(0, min(x_max, max_coord - 1))
            y_min = max(0, min(y_min, max_coord - 1))
            y_max = max(0, min(y_max, max_coord - 1))

            # Handle case where coordinates are swapped
            if x_min > x_max:
                x_min, x_max = x_max, x_min
            if y_min > y_max:
                y_min, y_max = y_max, y_min

            tiles = []

            # Generate all tiles in the bounding box
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    tile_id = f"{self.precision}/{x}/{y}"
                    polygon = self._create_tile_polygon(x, y)
                    tiles.append(GridCell(tile_id, polygon, self.precision))

            return tiles
        except Exception:
            return []

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

    def __repr__(self):
        return f"SlippyGrid(precision={self.precision})"
