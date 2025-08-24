"""
Geohash grid implementation.
"""

from typing import List

import geopandas as gpd
from shapely.geometry import Polygon

from . import _geohash as geohash
from .base import BaseGrid, GridCell
from .cache import cached_method, cell_cache_key, geo_cache_key


class GeohashGrid(BaseGrid):
    """
    Geohash-based spatial grid system.

    Implements the Geohash spatial indexing system using base-32
    encoding to create hierarchical rectangular grid cells.
    """

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
        if not 1 <= precision <= 12:
            raise ValueError("Geohash precision must be between 1 and 12")
        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of Geohash cells at this precision in square kilometers.

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
        geohash_str = geohash.encode(lat, lon, precision=self.precision)
        return self.get_cell_from_identifier(geohash_str)

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
        bbox = geohash.bbox(identifier)
        min_lat, min_lon, max_lat, max_lon = bbox

        polygon = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )

        return GridCell(identifier, polygon, len(identifier))

    @cached_method(cache_key_func=cell_cache_key)
    def get_neighbors(self, cell: GridCell) -> List[GridCell]:
        """
        Get neighboring geohash cells.

        Parameters
        ----------
        cell : GridCell
            The geohash cell for which to find neighbors

        Returns
        -------
        List[GridCell]
            List of neighboring geohash cells
        """
        neighbor_hashes = geohash.neighbors(cell.identifier)
        return [
            self.get_cell_from_identifier(neighbor_hash)
            for neighbor_hash in neighbor_hashes
        ]

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> List[GridCell]:
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
                except:
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

    def expand_cell(self, cell: GridCell) -> List[GridCell]:
        """
        Expand a geohash cell to higher precision cells contained within it.

        Args:
            cell: The cell to expand

        Returns
        -------
            List of higher precision cells
        """
        if len(cell.identifier) >= 12:
            return [cell]

        expanded_cells = []
        base32 = "0123456789bcdefghjkmnpqrstuvwxyz"

        for char in base32:
            new_identifier = cell.identifier + char
            try:
                expanded_cells.append(self.get_cell_from_identifier(new_identifier))
            except:
                pass

        return expanded_cells

    def _get_utm_epsg_from_coords(self, lat: float, lon: float) -> int:
        """
        Get the best UTM EPSG code for given coordinates.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        int
            EPSG code for the appropriate UTM zone
        """
        # Calculate UTM zone number
        zone_number = int((lon + 180) / 6) + 1

        # Handle special cases for Norway and Svalbard
        if 56 <= lat < 64 and 3 <= lon < 12:
            zone_number = 32
        elif 72 <= lat < 84 and lon >= 0:
            if lon < 9:
                zone_number = 31
            elif lon < 21:
                zone_number = 33
            elif lon < 33:
                zone_number = 35
            elif lon < 42:
                zone_number = 37

        # Determine hemisphere and construct EPSG code
        if lat >= 0:
            return 32600 + zone_number  # Northern hemisphere
        else:
            return 32700 + zone_number  # Southern hemisphere

    def intersects(
        self, gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:4326"
    ) -> gpd.GeoDataFrame:
        """
        Get all grid cells that intersect with geometries in a GeoDataFrame.

        For Geohash grids, includes an additional 'utm' column with the best UTM CRS
        for each geohash cell based on its centroid.

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
                    # Get cell centroid for UTM calculation
                    centroid = cell.polygon.centroid
                    utm_epsg = self._get_utm_epsg_from_coords(centroid.y, centroid.x)

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
