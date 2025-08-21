"""
MGRS (Military Grid Reference System) grid implementation.
"""

import math
from typing import List

import geopandas as gpd
import mgrs
from pyproj import Transformer
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell


class MGRSGrid(BaseGrid):
    """
    MGRS-based spatial grid system.

    Implements the Military Grid Reference System (MGRS) for creating
    uniform square grid cells based on UTM projections.
    """

    def __init__(self, precision: int = 1):
        """
        Initialize MGRSGrid.

        Parameters
        ----------
        precision : int, optional
            MGRS precision level (0-5), by default 1.

            Precision levels:
                0 = 100km grid
                1 = 10km grid
                2 = 1km grid
                3 = 100m grid
                4 = 10m grid
                5 = 1m grid

        Raises
        ------
        ValueError
            If precision is not between 0 and 5
        """
        if not 0 <= precision <= 5:
            raise ValueError("MGRS precision must be between 0 and 5")
        super().__init__(precision)
        self.mgrs_converter = mgrs.MGRS()

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of MGRS cells at this precision in square kilometers.

        Returns
        -------
        float
            Theoretical area in square kilometers for cells at this precision
        """
        # MGRS cells are square grids with well-defined sizes
        grid_size_m = self._get_grid_size()  # Get size in meters
        area_m2 = grid_size_m * grid_size_m  # Square area
        return area_m2 / 1_000_000  # Convert to km²

    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """Get the MGRS cell containing the given point."""
        mgrs_str = self.mgrs_converter.toMGRS(lat, lon, MGRSPrecision=self.precision)
        return self.get_cell_from_identifier(mgrs_str)

    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """Get an MGRS cell from its identifier."""
        try:
            lat, lon = self.mgrs_converter.toLatLon(identifier)

            grid_size = self._get_grid_size()

            polygon = self._create_mgrs_polygon(identifier, lat, lon, grid_size)

            return GridCell(identifier, polygon, self.precision)
        except Exception as e:
            raise ValueError(f"Invalid MGRS identifier: {identifier}") from e

    def _create_mgrs_polygon(
        self, mgrs_id: str, center_lat: float, center_lon: float, grid_size: float
    ) -> Polygon:
        """Create a polygon for an MGRS cell."""
        utm_zone = self._get_utm_zone_from_mgrs(mgrs_id)

        transformer_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{utm_zone}")
        transformer_to_wgs84 = Transformer.from_crs(f"EPSG:{utm_zone}", "EPSG:4326")

        center_x, center_y = transformer_to_utm.transform(center_lat, center_lon)

        half_size = grid_size / 2

        corners_utm = [
            (center_x - half_size, center_y - half_size),
            (center_x + half_size, center_y - half_size),
            (center_x + half_size, center_y + half_size),
            (center_x - half_size, center_y + half_size),
            (center_x - half_size, center_y - half_size),
        ]

        corners_wgs84 = []
        for x, y in corners_utm:
            lat, lon = transformer_to_wgs84.transform(x, y)
            corners_wgs84.append((lon, lat))

        return Polygon(corners_wgs84)

    def _get_utm_zone_from_mgrs(self, mgrs_id: str) -> int:
        """Get UTM zone EPSG code from MGRS identifier."""
        zone_letter = mgrs_id[:3]
        zone_number = int(zone_letter[:2])
        hemisphere_letter = zone_letter[2]

        if hemisphere_letter in "CDEFGHJKLM":
            return 32700 + zone_number
        else:
            return 32600 + zone_number

    def _get_grid_size(self) -> float:
        """Get grid size in meters for the current precision."""
        sizes = {0: 100000, 1: 10000, 2: 1000, 3: 100, 4: 10, 5: 1}
        return sizes[self.precision]

    def get_neighbors(self, cell: GridCell) -> List[GridCell]:
        """Get neighboring MGRS cells."""
        try:
            lat, lon = self.mgrs_converter.toLatLon(cell.identifier)
            grid_size_deg = self._grid_size_to_degrees(lat)

            neighbor_coords = [
                (lat + grid_size_deg, lon),
                (lat - grid_size_deg, lon),
                (lat, lon + grid_size_deg),
                (lat, lon - grid_size_deg),
                (lat + grid_size_deg, lon + grid_size_deg),
                (lat + grid_size_deg, lon - grid_size_deg),
                (lat - grid_size_deg, lon + grid_size_deg),
                (lat - grid_size_deg, lon - grid_size_deg),
            ]

            neighbors = []
            for n_lat, n_lon in neighbor_coords:
                try:
                    if -90 <= n_lat <= 90 and -180 <= n_lon <= 180:
                        neighbor_cell = self.get_cell_from_point(n_lat, n_lon)
                        if neighbor_cell.identifier != cell.identifier:
                            neighbors.append(neighbor_cell)
                except:
                    pass

            return list(set(neighbors))
        except:
            return []

    def _grid_size_to_degrees(self, lat: float) -> float:
        """Convert grid size from meters to approximate degrees."""
        grid_size_m = self._get_grid_size()

        lat_deg_per_m = 1.0 / 111320.0

        # Clamp latitude to avoid division by zero at poles
        lat_clamped = max(-89.9, min(89.9, lat))
        cos_lat = math.cos(math.radians(lat_clamped))

        # Ensure cos_lat is not zero (additional safety)
        cos_lat = max(0.001, cos_lat)

        1.0 / (111320.0 * cos_lat)

        return grid_size_m * lat_deg_per_m

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> List[GridCell]:
        """Get all MGRS cells within the given bounding box."""
        cells = set()  # Use set to avoid duplicates

        # For large grids, use a denser sampling pattern to ensure we don't miss cells
        grid_size_deg = self._grid_size_to_degrees((min_lat + max_lat) / 2)

        # Extend the sampling area to catch cells that intersect the boundary
        # but whose centers might be outside the bbox
        margin = grid_size_deg * 1.5

        extended_min_lat = min_lat - margin
        extended_max_lat = max_lat + margin
        extended_min_lon = min_lon - margin
        extended_max_lon = max_lon + margin

        # Use smaller step size for sampling, especially for large grid cells
        bbox_width = extended_max_lon - extended_min_lon
        bbox_height = extended_max_lat - extended_min_lat

        # Ensure we sample densely enough to catch boundary intersections
        lat_samples = max(10, min(50, int(bbox_height / grid_size_deg) * 3 + 5))
        lon_samples = max(10, min(50, int(bbox_width / grid_size_deg) * 3 + 5))

        lat_step = bbox_height / lat_samples if lat_samples > 1 else bbox_height
        lon_step = bbox_width / lon_samples if lon_samples > 1 else bbox_width

        # Create bbox polygon for intersection testing
        bbox_polygon = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )

        # Sample points across the extended bounding box
        for i in range(lat_samples + 1):
            for j in range(lon_samples + 1):
                lat = extended_min_lat + (i * lat_step)
                lon = extended_min_lon + (j * lon_step)

                try:
                    cell = self.get_cell_from_point(lat, lon)
                    # Check if cell actually intersects with the original bbox
                    if cell.polygon.intersects(bbox_polygon):
                        cells.add(cell)
                except Exception:
                    # Skip points that can't be converted to MGRS
                    pass

        return list(cells)

    def intersects(
        self, gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:4326"
    ) -> gpd.GeoDataFrame:
        """
        Get all grid cells that intersect with geometries in a GeoDataFrame.

        For MGRS grids, includes an additional 'utm' column with the best UTM CRS
        for each MGRS cell.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            A GeoDataFrame containing geometries to intersect with grid cells
        target_crs : str, optional
            Target CRS for grid operations (default: "EPSG:4326")

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with grid cell identifiers, UTM codes, geometries, and original data
        """
        if gdf.empty:
            empty_columns = ["cell_id", "precision", "utm", "geometry"] + [
                col for col in gdf.columns if col != "geometry"
            ]
            return gpd.GeoDataFrame(columns=empty_columns)

        original_crs = gdf.crs

        # Transform to target CRS if needed
        if original_crs is None:
            raise ValueError("GeoDataFrame CRS must be defined")

        if original_crs != target_crs:
            gdf_transformed = gdf.to_crs(target_crs)
        else:
            gdf_transformed = gdf.copy()

        # Collect all intersecting cells with source geometry indices
        all_cells = []
        source_indices = []

        for idx, geometry in enumerate(gdf_transformed.geometry):
            if geometry is not None and not geometry.is_empty:
                bounds = geometry.bounds
                min_lon, min_lat, max_lon, max_lat = bounds
                candidate_cells = self.get_cells_in_bbox(
                    min_lat, min_lon, max_lat, max_lon
                )
                intersecting_cells = [
                    cell
                    for cell in candidate_cells
                    if cell.polygon.intersects(geometry)
                ]
                for cell in intersecting_cells:
                    utm_epsg = self._get_utm_zone_from_mgrs(cell.identifier)
                    all_cells.append(
                        {
                            "cell_id": cell.identifier,
                            "precision": cell.precision,
                            "utm": utm_epsg,
                            "geometry": cell.polygon,
                        }
                    )
                    source_indices.append(idx)

        if not all_cells:
            empty_columns = ["cell_id", "precision", "utm", "geometry"] + [
                col for col in gdf.columns if col != "geometry"
            ]
            return gpd.GeoDataFrame(columns=empty_columns)

        # Create result GeoDataFrame
        result_gdf = gpd.GeoDataFrame(all_cells, crs=target_crs)

        # Add original data for each intersecting cell
        for col in gdf.columns:
            if col != "geometry":
                result_gdf[col] = [gdf.iloc[idx][col] for idx in source_indices]

        # Transform back to original CRS if different
        if original_crs != target_crs:
            result_gdf = result_gdf.to_crs(original_crs)

        return result_gdf
