"""Geohash grid implementation."""

from __future__ import annotations

import functools
import math
from typing import Sequence

import geopandas as gpd
from shapely.prepared import prep

from .. import _geohash as geohash
from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


@functools.lru_cache(maxsize=8192)
def _cell_from_id(identifier: str) -> Cell:
    min_lat, min_lon, max_lat, max_lon = geohash.bbox(identifier)
    bbox = (min_lon, min_lat, max_lon, max_lat)
    return Cell(identifier, len(identifier), bbox)


class GeohashGrid(GridBase):
    """Geohash-based spatial grid system."""

    name = "geohash"

    def __init__(self, precision: int = 5):
        super().__init__(precision)

    def _validate_precision(self) -> None:
        if not 1 <= self.precision <= 12:
            raise InvalidPrecision("Geohash precision must be between 1 and 12")

    @property
    def area_km2(self) -> float:
        areas = {
            1: 5009400.0,
            2: 1252350.0,
            3: 156540.0,
            4: 39135.0,
            5: 4892.0,
            6: 1223.0,
            7: 153.0,
            8: 38.0,
            9: 4.8,
            10: 1.2,
            11: 0.15,
            12: 0.037,
        }
        return areas.get(self.precision, 4892.0)

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        identifier = geohash.encode(lat, lon, precision=self.precision)
        return _cell_from_id(identifier)

    def from_id(self, cell_id: str) -> Cell:
        return _cell_from_id(cell_id)

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        return [_cell_from_id(n) for n in geohash.neighbors(cell.id)]

    def intersects(self, gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:4326"):
        """Optimized intersection for geohash grids avoiding global cell polygon builds."""
        from ..ops.intersects import _empty_result

        if gdf.empty:
            return _empty_result(gdf, gdf.crs or target_crs)

        original_crs = gdf.crs
        if original_crs is None:
            raise ValueError("GeoDataFrame CRS must be defined")

        gdf_transformed = gdf.to_crs(target_crs) if original_crs != target_crs else gdf
        geometries = gdf_transformed.geometry
        valid_mask = geometries.notna() & ~geometries.is_empty
        if not bool(valid_mask.any()):
            return _empty_result(gdf, target_crs)

        non_geom_cols = [col for col in gdf.columns if col != "geometry"]
        valid_indices = valid_mask.to_numpy().nonzero()[0]
        valid_geometries = geometries.array[valid_mask.to_numpy()]
        non_geom_values = None
        if non_geom_cols:
            non_geom_values = gdf.iloc[valid_indices][non_geom_cols].to_numpy()

        rows = []
        rows_append = rows.append

        for i, geometry in enumerate(valid_geometries):
            prepared = prep(geometry)
            min_lon, min_lat, max_lon, max_lat = geometry.bounds
            for cell in self.cells_in_bbox((min_lon, min_lat, max_lon, max_lat)):
                if prepared.intersects(cell.polygon):
                    row = {
                        "cell_id": cell.id,
                        "precision": cell.precision,
                        "geometry": cell.polygon,
                    }
                    if non_geom_values is not None:
                        for col, value in zip(non_geom_cols, non_geom_values[i]):
                            row[col] = value
                    rows_append(row)

        if not rows:
            return _empty_result(gdf, target_crs)

        result = gpd.GeoDataFrame(rows, crs=target_crs)
        if original_crs != target_crs:
            result = result.to_crs(original_crs)
        return result

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)

        total_bits = self.precision * 5
        lon_bits = (total_bits + 1) // 2
        lat_bits = total_bits // 2
        lat_cells = 1 << lat_bits
        lon_cells = 1 << lon_bits
        lat_step = 180.0 / lat_cells
        lon_step = 360.0 / lon_cells

        min_lat_i = int(math.floor((min_lat + 90.0) / lat_step)) - 1
        max_lat_i = int(math.floor((max_lat + 90.0) / lat_step)) + 1
        min_lon_i = int(math.floor((min_lon + 180.0) / lon_step)) - 1
        max_lon_i = int(math.floor((max_lon + 180.0) / lon_step)) + 1

        if min_lat_i < 0:
            min_lat_i = 0
        if min_lon_i < 0:
            min_lon_i = 0
        max_lat_allowed = lat_cells - 1
        max_lon_allowed = lon_cells - 1
        if max_lat_i > max_lat_allowed:
            max_lat_i = max_lat_allowed
        if max_lon_i > max_lon_allowed:
            max_lon_i = max_lon_allowed

        cells: list[Cell] = []
        append_cell = cells.append
        base32 = _BASE32
        precision = self.precision

        for lat_i in range(min_lat_i, max_lat_i + 1):
            cell_min_lat = -90.0 + lat_i * lat_step
            cell_max_lat = cell_min_lat + lat_step
            if cell_max_lat < min_lat or cell_min_lat > max_lat:
                continue
            for lon_i in range(min_lon_i, max_lon_i + 1):
                cell_min_lon = -180.0 + lon_i * lon_step
                cell_max_lon = cell_min_lon + lon_step
                if cell_max_lon < min_lon or cell_min_lon > max_lon:
                    continue

                chars = []
                ch = 0
                for bit_index in range(total_bits):
                    if (bit_index & 1) == 0:
                        shift = lon_bits - 1 - (bit_index >> 1)
                        ch = (ch << 1) | ((lon_i >> shift) & 1)
                    else:
                        shift = lat_bits - 1 - (bit_index >> 1)
                        ch = (ch << 1) | ((lat_i >> shift) & 1)
                    if (bit_index % 5) == 4:
                        chars.append(base32[ch])
                        ch = 0

                identifier = "".join(chars)
                append_cell(
                    Cell(
                        identifier,
                        precision,
                        (cell_min_lon, cell_min_lat, cell_max_lon, cell_max_lat),
                    )
                )

        return cells

    def _lat_step(self) -> float:
        lat_bits = (self.precision * 5 + 1) // 2
        return 180.0 / (2**lat_bits)

    def _lon_step(self) -> float:
        lon_bits = (self.precision * 5) // 2
        return 360.0 / (2**lon_bits)
