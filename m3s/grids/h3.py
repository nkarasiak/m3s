"""H3 grid implementation."""

from __future__ import annotations

import functools
from math import cos, radians
from typing import Sequence

import h3

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


@functools.lru_cache(maxsize=8192)
def _cell_from_id(identifier: str) -> Cell:
    boundary = h3.cell_to_boundary(identifier)
    coords = [(lng, lat) for lat, lng in boundary]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    bbox = (min(lons), min(lats), max(lons), max(lats))
    return Cell(identifier, h3.get_resolution(identifier), bbox, _coords=coords)


class H3Grid(GridBase):
    """H3-based hexagonal spatial grid system."""

    name = "h3"

    def __init__(self, resolution: int | None = None, *, precision: int | None = None):
        if precision is not None and resolution is not None:
            raise ValueError("Use either precision or resolution, not both")
        if precision is None:
            precision = resolution if resolution is not None else 7
        self.precision = precision
        self.resolution = precision
        self._validate_precision()

    def _validate_precision(self) -> None:
        if not 0 <= self.precision <= 15:
            raise InvalidPrecision("H3 resolution must be between 0 and 15")

    @property
    def area_km2(self) -> float:
        try:
            return h3.average_hexagon_area(self.precision, unit="km^2")
        except Exception:
            areas = {
                0: 4357449.43,
                1: 609788.44,
                2: 86801.78,
                3: 12393.43,
                4: 1770.35,
                5: 252.9,
                6: 36.13,
                7: 5.16,
                8: 0.737,
                9: 0.105,
                10: 0.015,
                11: 0.002,
                12: 0.0003,
                13: 0.00004,
                14: 0.000006,
                15: 0.0000009,
            }
            return areas.get(self.precision, 5.16)

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        identifier = h3.latlng_to_cell(lat, lon, self.precision)
        return _cell_from_id(identifier)

    def from_id(self, cell_id: str) -> Cell:
        return _cell_from_id(cell_id)

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        indices = h3.grid_disk(cell.id, 1)
        indices = [idx for idx in indices if idx != cell.id]
        return [_cell_from_id(idx) for idx in indices]

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)
        bbox_poly = None
        bbox_coords = [
            (min_lat, min_lon),
            (min_lat, max_lon),
            (max_lat, max_lon),
            (max_lat, min_lon),
        ]
        poly = h3.LatLngPoly(bbox_coords)
        indices = []
        used_center_fill = False
        try:
            indices = h3.polygon_to_cells(poly, self.precision, contain="overlap")
        except TypeError:
            try:
                indices = h3.polygon_to_cells(poly, self.precision)
                used_center_fill = True
            except Exception:
                indices = []
        except Exception:
            indices = []

        if not indices:
            try:
                indices = h3.h3shape_to_cells_experimental(
                    poly, self.precision, contain="overlap"
                )
            except Exception:
                indices = []

        if indices:
            if used_center_fill:
                # Expand bbox by ~1 edge length to capture overlapping cells.
                try:
                    edge_km = h3.edge_length(self.precision, unit="km")
                except Exception:
                    edge_km = 5.0
                lat_pad = edge_km / 110.574
                lon_pad = edge_km / (111.320 * max(cos(radians((min_lat + max_lat) / 2)), 0.01))
                expanded = h3.LatLngPoly(
                    [
                        (min_lat - lat_pad, min_lon - lon_pad),
                        (min_lat - lat_pad, max_lon + lon_pad),
                        (max_lat + lat_pad, max_lon + lon_pad),
                        (max_lat + lat_pad, min_lon - lon_pad),
                    ]
                )
                try:
                    indices = h3.polygon_to_cells(expanded, self.precision)
                except Exception:
                    pass
            if bbox_poly is None:
                from shapely.geometry import box

                bbox_poly = box(min_lon, min_lat, max_lon, max_lat)
            cells = [_cell_from_id(idx) for idx in indices]
            return [cell for cell in cells if cell.polygon.intersects(bbox_poly)]

        return self._cells_in_bbox_fallback(min_lat, min_lon, max_lat, max_lon)

    def _cells_in_bbox_fallback(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> Sequence[Cell]:
        cells = set()
        try:
            edge_km = h3.edge_length(self.precision, unit="km")
        except Exception:
            edge_km = 5.0
        lat_step = edge_km / 110.574
        lat_mid = (min_lat + max_lat) / 2
        lon_step = edge_km / (111.320 * max(cos(radians(lat_mid)), 0.01))

        lat = min_lat - lat_step
        while lat <= max_lat + lat_step:
            lon = min_lon - lon_step
            while lon <= max_lon + lon_step:
                cells.add(self.cell(lat, lon))
                lon += lon_step
            lat += lat_step

        return list(cells)
