"""
Base classes and interfaces for spatial grids.
"""

from abc import ABC, abstractmethod
from typing import List

import geopandas as gpd
import pyproj
from shapely.geometry import Point, Polygon
from shapely.ops import transform

from .cache import (
    cached_property,
    get_spatial_cache,
)


class GridCell:
    """
    Represents a single grid cell.

    A GridCell contains an identifier, geometric polygon representation,
    and precision level for spatial indexing systems.
    """

    def __init__(self, identifier: str, polygon: Polygon, precision: int):
        self.identifier = identifier
        self.polygon = polygon
        self.precision = precision

    @cached_property
    def area_km2(self) -> float:
        """
        Calculate the area of the grid cell in square kilometers.

        Returns
        -------
        float
            Area of the cell in square kilometers
        """
        return self._calculate_area_km2()

    def _calculate_area_km2(self) -> float:
        """
        Calculate the area of the polygon in square kilometers.

        Uses equal-area projection for accurate area calculation.
        """
        cache = get_spatial_cache()
        cached_area = cache.get_area(self.identifier)
        if cached_area is not None:
            return cached_area

        try:
            # Get the centroid to determine appropriate UTM zone
            centroid = self.polygon.centroid
            lon, lat = centroid.x, centroid.y

            # Check cache for UTM zone first
            cached_utm = cache.get_utm_zone(lat, lon)
            if cached_utm:
                utm_crs = cached_utm
            else:
                # Determine UTM zone
                utm_zone = int((lon + 180) / 6) + 1
                hemisphere = "north" if lat >= 0 else "south"
                utm_crs = f"+proj=utm +zone={utm_zone} +{hemisphere} +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
                cache.put_utm_zone(lat, lon, utm_crs)

            # Transform from WGS84 to UTM
            transformer = pyproj.Transformer.from_crs(
                "EPSG:4326", utm_crs, always_xy=True
            )
            projected_polygon = transform(transformer.transform, self.polygon)

            # Calculate area in square meters, convert to square kilometers
            area_m2 = projected_polygon.area
            area_km2 = area_m2 / 1_000_000  # Convert to km²

            # Cache the result
            cache.put_area(self.identifier, area_km2)
            return area_km2

        except Exception:
            # Fallback: use simple spherical approximation
            # This is less accurate but always works
            bounds = self.polygon.bounds
            min_lon, min_lat, max_lon, max_lat = bounds

            # Approximate area using spherical formula
            # This is a rough approximation for small areas
            lat_diff = max_lat - min_lat
            lon_diff = max_lon - min_lon

            # Earth's radius in km
            R = 6371.0

            # Convert degrees to radians
            lat_rad = (min_lat + max_lat) / 2 * 3.14159 / 180
            lat_diff_rad = lat_diff * 3.14159 / 180
            lon_diff_rad = lon_diff * 3.14159 / 180

            # Approximate area
            area_km2 = R * R * abs(lat_diff_rad * lon_diff_rad * abs(lat_rad))

            # Cache the fallback result too
            cache.put_area(self.identifier, area_km2)
            return area_km2

    def __repr__(self):
        return f"GridCell(id={self.identifier}, precision={self.precision}, area={self.area_km2:.2f}km²)"

    def __eq__(self, other):
        if not isinstance(other, GridCell):
            return False
        return self.identifier == other.identifier

    def __hash__(self):
        return hash(self.identifier)


class BaseGrid(ABC):
    """
    Abstract base class for all grid systems.

    Provides common interface for spatial grid implementations including
    cell retrieval, neighbor finding, and polygon intersection operations.
    """

    def __init__(self, precision: int):
        self.precision = precision

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
            List of neighboring grid cells
        """
        pass

    @abstractmethod
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
            List of grid cells that intersect the bounding box
        """
        pass

    def contains_point(self, polygon: Polygon, lat: float, lon: float) -> bool:
        """
        Check if a point is contained within the polygon.

        Parameters
        ----------
        polygon : Polygon
            A shapely Polygon object
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        bool
            True if the point is contained within the polygon
        """
        point = Point(lon, lat)
        return polygon.contains(point)

    def intersects(
        self, gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:4326"
    ) -> gpd.GeoDataFrame:
        """
        Get all grid cells that intersect with geometries in a GeoDataFrame.

        Automatically handles CRS transformation to WGS84 (EPSG:4326) for grid operations,
        then transforms results back to the original CRS if different.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            A GeoDataFrame containing geometries to intersect with grid cells
        target_crs : str, optional
            Target CRS for grid operations (default: "EPSG:4326")

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with grid cell identifiers, geometries, and original data
        """
        if gdf.empty:
            # Create columns without duplicating 'geometry'
            result_columns = ["cell_id", "precision", "geometry"]
            result_columns.extend([col for col in gdf.columns if col != "geometry"])
            return gpd.GeoDataFrame(columns=result_columns, crs=gdf.crs)

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
                    all_cells.append(
                        {
                            "cell_id": cell.identifier,
                            "precision": cell.precision,
                            "geometry": cell.polygon,
                        }
                    )
                    source_indices.append(idx)

        if not all_cells:
            # Create columns without duplicating 'geometry'
            result_columns = ["cell_id", "precision", "geometry"]
            result_columns.extend([col for col in gdf.columns if col != "geometry"])
            return gpd.GeoDataFrame(columns=result_columns, crs=target_crs)

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
