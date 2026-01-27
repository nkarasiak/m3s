"""Slippy Map tiles grid implementation."""

from __future__ import annotations

import math
from typing import Sequence

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class SlippyGrid(GridBase):
    """Slippy Map tile grid system (z/x/y)."""

    name = "slippy"

    def __init__(self, zoom: int | None = None, *, precision: int | None = None):
        if precision is not None and zoom is not None:
            raise ValueError("Use either precision or zoom, not both")
        if precision is None:
            if zoom is None:
                raise ValueError("SlippyGrid requires a precision/zoom")
            precision = zoom
        super().__init__(precision)
        self.zoom = precision

    def _validate_precision(self) -> None:
        if not 0 <= self.precision <= 22:
            raise InvalidPrecision("Slippy zoom level must be between 0 and 22")

    @property
    def area_km2(self) -> float:
        earth_circumference_km = 40075.0
        tiles_per_side = 2**self.zoom
        tile_size_km = earth_circumference_km / tiles_per_side
        return tile_size_km * tile_size_km

    def _deg2num(self, lat: float, lon: float) -> tuple[int, int]:
        lat_rad = math.radians(lat)
        n = 2.0**self.zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    def _num2deg(self, x: int, y: int) -> Bbox:
        n = 2.0**self.zoom
        lon_min = x / n * 360.0 - 180.0
        lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
        lon_max = (x + 1) / n * 360.0 - 180.0
        lat_min = math.degrees(
            math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
        )
        return (lon_min, lat_min, lon_max, lat_max)

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        x, y = self._deg2num(lat, lon)
        identifier = f"{self.zoom}/{x}/{y}"
        bbox = self._num2deg(x, y)
        return Cell(identifier, self.zoom, bbox)

    def from_id(self, cell_id: str) -> Cell:
        try:
            z, x, y = map(int, cell_id.split("/"))
        except Exception as exc:
            raise ValueError(f"Invalid Slippy tile id: {cell_id}") from exc
        if z != self.zoom:
            raise ValueError(f"Zoom mismatch: expected {self.zoom}, got {z}")
        max_coord = 2**z
        if not (0 <= x < max_coord and 0 <= y < max_coord):
            raise ValueError(f"Invalid tile coordinates for zoom {z}")
        bbox = self._num2deg(x, y)
        return Cell(cell_id, z, bbox)

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        try:
            z, x, y = map(int, cell.id.split("/"))
        except Exception:
            return []
        max_coord = 2**z
        neighbors: list[Cell] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                new_y = y + dy
                if not (0 <= new_y < max_coord):
                    continue
                new_x = (x + dx) % max_coord
                neighbor_id = f"{z}/{new_x}/{new_y}"
                bbox = self._num2deg(new_x, new_y)
                neighbors.append(Cell(neighbor_id, z, bbox))
        return neighbors

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)
        x1, y1 = self._deg2num(max_lat, min_lon)
        x2, y2 = self._deg2num(min_lat, max_lon)
        x_min, x_max = sorted((x1, x2))
        y_min, y_max = sorted((y1, y2))
        cells: list[Cell] = []
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                cell_id = f"{self.zoom}/{x}/{y}"
                cells.append(Cell(cell_id, self.zoom, self._num2deg(x, y)))
        return cells
