"""What3Words-style grid implementation."""

from __future__ import annotations

import hashlib
import math
from typing import Sequence

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class What3WordsGrid(GridBase):
    """3m x 3m grid approximation of What3Words."""

    name = "what3words"

    def __init__(self, precision: int = 1):
        super().__init__(precision)

    def _validate_precision(self) -> None:
        if self.precision != 1:
            raise InvalidPrecision("What3Words grid supports precision=1 only")

    @property
    def area_km2(self) -> float:
        return 9.0 / 1_000_000

    def _grid_size_degrees(self) -> float:
        return 3.0 / 111320.0

    def _lat_lon_to_grid_coords(self, lat: float, lon: float) -> tuple[int, int]:
        grid_size = self._grid_size_degrees()
        lat_correction = math.cos(math.radians(lat))
        lon_grid_size = grid_size / lat_correction if lat_correction != 0 else grid_size
        x = int(lon / lon_grid_size)
        y = int(lat / grid_size)
        return x, y

    def _grid_coords_to_bounds(self, x: int, y: int) -> Bbox:
        grid_size = self._grid_size_degrees()
        min_lat = y * grid_size
        max_lat = (y + 1) * grid_size
        lat_center = (min_lat + max_lat) / 2
        lat_correction = math.cos(math.radians(lat_center))
        lon_grid_size = grid_size / lat_correction if lat_correction != 0 else grid_size
        min_lon = x * lon_grid_size
        max_lon = (x + 1) * lon_grid_size
        return (min_lon, min_lat, max_lon, max_lat)

    def _generate_identifier(self, x: int, y: int) -> str:
        combined = f"{x}_{y}"
        hash_hex = hashlib.md5(combined.encode()).hexdigest()
        parts = []
        for i in range(0, 6, 2):
            parts.append(f"w{hash_hex[i:i+2]}")
        return f"w3w.{'.'.join(parts[:3])}"

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        x, y = self._lat_lon_to_grid_coords(lat, lon)
        bbox = self._grid_coords_to_bounds(x, y)
        identifier = self._generate_identifier(x, y)
        return Cell(identifier, self.precision, bbox)

    def from_id(self, cell_id: str) -> Cell:
        raise ValueError("What3Words identifiers are not reversible without API")

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        return []

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)
        grid_size = self._grid_size_degrees()
        cells = set()
        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                cells.add(self.cell(lat, lon))
                lon += grid_size
            lat += grid_size
        return list(cells)
