"""GARS grid implementation."""

from __future__ import annotations

from typing import Sequence

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class GARSGrid(GridBase):
    """GARS grid system."""

    name = "gars"

    def __init__(self, precision: int = 1):
        super().__init__(precision)

    def _validate_precision(self) -> None:
        if not 1 <= self.precision <= 3:
            raise InvalidPrecision("GARS precision must be between 1 and 3")

    @property
    def area_km2(self) -> float:
        sizes = {1: 0.5, 2: 0.25, 3: 1.0 / 12.0}
        size_deg = sizes[self.precision]
        size_km = size_deg * 111.32
        return size_km * size_km

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        code = self._encode(lat, lon, self.precision)
        return self.from_id(code)

    def from_id(self, cell_id: str) -> Cell:
        min_lat, min_lon, max_lat, max_lon = self._decode(cell_id, self.precision)
        return Cell(cell_id, self.precision, (min_lon, min_lat, max_lon, max_lat))

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        try:
            min_lat, min_lon, max_lat, max_lon = self._decode(cell.id)
        except Exception:
            return []
        lat_step = max_lat - min_lat
        lon_step = max_lon - min_lon
        lat_center = (min_lat + max_lat) / 2
        lon_center = (min_lon + max_lon) / 2
        neighbors = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                lat = lat_center + dy * lat_step
                lon = lon_center + dx * lon_step
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    neighbor = self.cell(lat, lon)
                    if neighbor.id != cell.id:
                        neighbors.append(neighbor)
        return neighbors

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)
        sizes = {1: 0.5, 2: 0.25, 3: 1.0 / 12.0}
        step = sizes[self.precision]
        eps = 1e-12
        min_row = int((min_lat + 90.0) / step)
        max_row = int(((max_lat - eps) + 90.0) / step)
        min_col = int((min_lon + 180.0) / step)
        max_col = int(((max_lon - eps) + 180.0) / step)
        cells = set()
        for row in range(min_row, max_row + 1):
            lat = -90.0 + (row + 0.5) * step
            for col in range(min_col, max_col + 1):
                lon = -180.0 + (col + 0.5) * step
                cells.add(self.cell(lat, lon))
        return list(cells)

    def _encode(self, lat: float, lon: float, precision: int) -> str:
        lon = (lon + 180) % 360
        lat = lat + 90
        lon_band = int(lon / 0.5) + 1
        lat_band = int(lat / 0.5) + 1
        code = f"{lon_band:03d}{lat_band:03d}"
        if precision == 1:
            return code
        quad = self._subquadrant(lat, lon, precision)
        return f"{code}{quad}"

    def _subquadrant(self, lat: float, lon: float, precision: int) -> str:
        lat_mod = (lat % 0.5) / 0.5
        lon_mod = (lon % 0.5) / 0.5
        if precision == 2:
            row = 1 if lat_mod < 0.5 else 2
            col = 1 if lon_mod < 0.5 else 2
            return f"{row}{col}"
        row = min(6, int(lat_mod * 6) + 1)
        col = min(6, int(lon_mod * 6) + 1)
        return f"{row}{col}"

    def _decode(
        self, identifier: str, precision: int | None = None
    ) -> tuple[float, float, float, float]:
        lon_band = int(identifier[0:3]) - 1
        lat_band = int(identifier[3:6]) - 1
        min_lon = lon_band * 0.5 - 180
        min_lat = lat_band * 0.5 - 90
        max_lon = min_lon + 0.5
        max_lat = min_lat + 0.5
        if len(identifier) >= 8:
            sub = identifier[6:8]
            row = int(sub[0]) - 1
            col = int(sub[1]) - 1
            if precision is None:
                precision = self.precision
            size = 0.5 / (2 if precision == 2 else 6)
            min_lon += col * size
            min_lat += row * size
            max_lon = min_lon + size
            max_lat = min_lat + size
        return min_lat, min_lon, max_lat, max_lon
