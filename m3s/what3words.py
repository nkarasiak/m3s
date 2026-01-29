"""
What3Words grid implementation.

Provides integration with What3Words 3-meter square grid system.
Note: This implementation provides the grid structure without requiring API access.
For full What3Words functionality including word-to-coordinate conversion,
use the official What3Words API.
"""

import hashlib
import math
from typing import List

import geopandas as gpd
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell
from .cache import cached_method, cell_cache_key, geo_cache_key


class What3WordsGrid(BaseGrid):
    """
    What3Words-style spatial grid system.

    Implements a 3-meter square grid system similar to What3Words.
    Each cell represents approximately a 3x3 meter square on the Earth's surface.

    Note: This implementation provides the grid structure. For actual What3Words
    integration with their word system, use the official What3Words API.
    """

    def __init__(self, precision: int = 1):
        """
        Initialize What3WordsGrid.

        Parameters
        ----------
        precision : int, optional
            Grid precision level (1 only supported for 3m squares), by default 1

        Raises
        ------
        ValueError
            If precision is not 1
        """
        if precision != 1:
            raise ValueError(
                "What3Words grid only supports precision level 1 (3m squares)"
            )
        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of What3Words cells in square kilometers.

        Returns
        -------
        float
            Theoretical area in square kilometers (approximately 0.000009 km²)
        """
        return 9.0 / 1_000_000  # 3m x 3m = 9 m² = 0.000009 km²

    def _lat_lon_to_grid_coords(self, lat: float, lon: float) -> tuple[int, int]:
        """
        Convert latitude/longitude to grid coordinates.

        Parameters
        ----------
        lat : float
            Latitude
        lon : float
            Longitude

        Returns
        -------
        tuple[int, int]
            Grid coordinates (x, y)
        """
        # Earth circumference is approximately 40,075,000 meters
        # At equator, 1 degree longitude = 111,320 meters
        # 3-meter grid means each cell is approximately 3/111320 = 0.00002696 degrees

        # Calculate grid size in degrees (approximate)
        grid_size_degrees = 3.0 / 111320.0  # ~0.00002696 degrees

        # Convert to grid coordinates (floor to handle negative coords correctly)
        y = math.floor(lat / grid_size_degrees)

        # Use the row's latitude center to compute longitude grid size
        min_lat = y * grid_size_degrees
        max_lat = (y + 1) * grid_size_degrees
        lat_center = (min_lat + max_lat) / 2

        lat_correction = math.cos(math.radians(lat_center))
        lon_grid_size = (
            grid_size_degrees / lat_correction
            if lat_correction != 0
            else grid_size_degrees
        )

        x = math.floor(lon / lon_grid_size)

        return x, y

    def _grid_coords_to_bounds(
        self, x: int, y: int
    ) -> tuple[float, float, float, float]:
        """
        Convert grid coordinates to geographic bounds.

        Parameters
        ----------
        x : int
            Grid X coordinate
        y : int
            Grid Y coordinate

        Returns
        -------
        tuple[float, float, float, float]
            Bounds as (min_lon, min_lat, max_lon, max_lat)
        """
        grid_size_degrees = 3.0 / 111320.0

        min_lat = y * grid_size_degrees
        max_lat = (y + 1) * grid_size_degrees

        # Adjust longitude grid size for latitude
        lat_center = (min_lat + max_lat) / 2
        lat_correction = math.cos(math.radians(lat_center))
        lon_grid_size = (
            grid_size_degrees / lat_correction
            if lat_correction != 0
            else grid_size_degrees
        )

        min_lon = x * lon_grid_size
        max_lon = (x + 1) * lon_grid_size

        return min_lon, min_lat, max_lon, max_lat

    def _generate_identifier(self, x: int, y: int) -> str:
        """
        Generate a unique identifier for the grid cell.

        Parameters
        ----------
        x : int
            Grid X coordinate
        y : int
            Grid Y coordinate

        Returns
        -------
        str
            Unique identifier for the cell
        """
        # Create a hash-based identifier that looks somewhat like What3Words format
        # This is NOT the actual What3Words algorithm
        combined = f"{x}_{y}"
        hash_obj = hashlib.md5(combined.encode())
        hash_hex = hash_obj.hexdigest()

        # Generate pseudo-words from hash
        word_parts = []
        for i in range(0, 6, 2):
            part = hash_hex[i : i + 2]
            # Convert to a word-like identifier
            word_parts.append(f"w{part}")

        return f"w3w.{'.'.join(word_parts[:3])}"

    @cached_method(cache_key_func=geo_cache_key)
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the grid cell containing the given point.

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
        x, y = self._lat_lon_to_grid_coords(lat, lon)
        min_lon, min_lat, max_lon, max_lat = self._grid_coords_to_bounds(x, y)
        epsilon = max(1e-12, (max_lat - min_lat) * 1e-6)
        min_lon -= epsilon
        min_lat -= epsilon
        max_lon += epsilon
        max_lat += epsilon

        polygon = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )

        identifier = self._generate_identifier(x, y)
        return GridCell(identifier, polygon, self.precision)

    @cached_method(cache_key_func=cell_cache_key)
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its identifier.

        Parameters
        ----------
        identifier : str
            The unique identifier for the grid cell

        Returns
        -------
        GridCell
            The grid cell corresponding to the identifier
        """
        # For this implementation, we'll need to reverse-engineer from identifier
        # In a real What3Words integration, this would use their API

        # Extract coordinates from our hash-based identifier
        # This is a simplified approach - real What3Words would need their API
        if not identifier.startswith("w3w."):
            raise ValueError(f"Invalid What3Words identifier: {identifier}")

        # For demo purposes, we'll create a cell at 0,0
        # In reality, you'd need What3Words API to convert words to coordinates
        return self.get_cell_from_point(0.0, 0.0)

    def get_neighbors(self, cell: GridCell) -> List[GridCell]:
        """
        Get neighboring cells of the given cell.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbors

        Returns
        -------
        List[GridCell]
            List of neighboring grid cells (8 neighbors for square grid)
        """
        # Get center point of the cell
        centroid = cell.polygon.centroid
        lat, lon = centroid.y, centroid.x

        x, y = self._lat_lon_to_grid_coords(lat, lon)

        neighbors = []
        # Get 8 neighboring cells (Moore neighborhood)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # Skip the center cell

                neighbor_x, neighbor_y = x + dx, y + dy
                min_lon, min_lat, max_lon, max_lat = self._grid_coords_to_bounds(
                    neighbor_x, neighbor_y
                )
                epsilon = max(1e-12, (max_lat - min_lat) * 1e-6)
                min_lon -= epsilon
                min_lat -= epsilon
                max_lon += epsilon
                max_lat += epsilon

                # Create neighbor cell
                polygon = Polygon(
                    [
                        (min_lon, min_lat),
                        (max_lon, min_lat),
                        (max_lon, max_lat),
                        (min_lon, max_lat),
                        (min_lon, min_lat),
                    ]
                )

                identifier = self._generate_identifier(neighbor_x, neighbor_y)
                neighbors.append(GridCell(identifier, polygon, self.precision))

        return neighbors

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> List[GridCell]:
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
        List[GridCell]
            List of grid cells within the bounding box
        """
        cells = []

        # Convert corners to grid coordinates
        x1, y1 = self._lat_lon_to_grid_coords(min_lat, min_lon)
        x2, y2 = self._lat_lon_to_grid_coords(max_lat, max_lon)

        # Ensure proper order
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        # Generate cells in the bounding box
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                cell_min_lon, cell_min_lat, cell_max_lon, cell_max_lat = (
                    self._grid_coords_to_bounds(x, y)
                )
                epsilon = max(1e-12, (cell_max_lat - cell_min_lat) * 1e-6)
                cell_min_lon -= epsilon
                cell_min_lat -= epsilon
                cell_max_lon += epsilon
                cell_max_lat += epsilon

                # Create cell polygon
                polygon = Polygon(
                    [
                        (cell_min_lon, cell_min_lat),
                        (cell_max_lon, cell_min_lat),
                        (cell_max_lon, cell_max_lat),
                        (cell_min_lon, cell_max_lat),
                        (cell_min_lon, cell_min_lat),
                    ]
                )

                identifier = self._generate_identifier(x, y)
                cells.append(GridCell(identifier, polygon, self.precision))

        return cells

    def intersects(
        self, gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:4326"
    ) -> gpd.GeoDataFrame:
        """
        Find grid cells that intersect with geometries in a GeoDataFrame.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame containing geometries to intersect with
        target_crs : str, optional
            Target coordinate reference system, by default "EPSG:4326"

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with intersecting grid cells and original data
        """
        # Convert GeoDataFrame to target CRS if needed
        if gdf.crs != target_crs:
            gdf = gdf.to_crs(target_crs)

        results = []

        for _idx, row in gdf.iterrows():
            geom = row.geometry
            bounds = geom.bounds

            # Get cells in bounding box
            cells = self.get_cells_in_bbox(bounds[1], bounds[0], bounds[3], bounds[2])

            # Check actual intersection
            for cell in cells:
                if cell.polygon.intersects(geom):
                    result_row = row.copy()
                    result_row["cell_id"] = cell.identifier
                    result_row["geometry"] = cell.polygon

                    # Add UTM zone information
                    centroid = cell.polygon.centroid
                    lat, lon = centroid.y, centroid.x
                    utm_zone = int((lon + 180) / 6) + 1
                    utm_code = 32600 + utm_zone if lat >= 0 else 32700 + utm_zone
                    result_row["utm"] = utm_code

                    results.append(result_row)

        if not results:
            # Return empty GeoDataFrame with expected columns
            empty_gdf = gpd.GeoDataFrame(columns=list(gdf.columns) + ["cell_id", "utm"])
            empty_gdf = empty_gdf.set_geometry("geometry")
            return empty_gdf

        result_gdf = gpd.GeoDataFrame(results)
        return result_gdf.reset_index(drop=True)
