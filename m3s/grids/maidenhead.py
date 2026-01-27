"""Maidenhead grid implementation."""

from __future__ import annotations

from typing import Sequence

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class MaidenheadGrid(GridBase):
    """Maidenhead Locator grid system."""

    name = "maidenhead"

    def __init__(self, precision: int = 3):
        super().__init__(precision)

    def _validate_precision(self) -> None:
        if not 1 <= self.precision <= 4:
            raise InvalidPrecision("Maidenhead precision must be between 1 and 4")

    @property
    def area_km2(self) -> float:
        lon_step, lat_step = self._steps()
        lon_km = lon_step * 111.32
        lat_km = lat_step * 111.32
        return lon_km * lat_km

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        code = self._encode(lat, lon)
        return self.from_id(code)

    def from_id(self, cell_id: str) -> Cell:
        min_lat, min_lon, max_lat, max_lon = self._decode(cell_id)
        return Cell(cell_id, self.precision, (min_lon, min_lat, max_lon, max_lat))

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        min_lat, min_lon, max_lat, max_lon = self._decode(cell.id)
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
        lon_step, lat_step = self._steps()
        cells = set()
        lat = min_lat - lat_step
        while lat <= max_lat + lat_step:
            lon = min_lon - lon_step
            while lon <= max_lon + lon_step:
                cells.add(self.cell(lat, lon))
                lon += lon_step
            lat += lat_step
        return list(cells)

    def _steps(self) -> tuple[float, float]:
        if self.precision == 1:
            return 20.0, 10.0
        if self.precision == 2:
            return 2.0, 1.0
        if self.precision == 3:
            return 2.0 / 24.0, 1.0 / 24.0
        return 2.0 / 240.0, 1.0 / 240.0

    def _encode(self, lat: float, lon: float) -> str:
        lon = lon + 180
        lat = lat + 90
        field = chr(int(lon // 20) + ord("A")) + chr(int(lat // 10) + ord("A"))
        square = str(int((lon % 20) // 2)) + str(int((lat % 10) // 1))
        subsquare = ""
        if self.precision >= 3:
            subsquare = chr(int(((lon % 2) / 2) * 24) + ord("a")) + chr(
                int(((lat % 1) / 1) * 24) + ord("a")
            )
        ext = ""
        if self.precision >= 4:
            ext = str(int(((lon % (2 / 24)) / (2 / 24)) * 10)) + str(
                int(((lat % (1 / 24)) / (1 / 24)) * 10)
            )
        return field + square + subsquare + ext

    def _decode(self, code: str) -> tuple[float, float, float, float]:
        code = code.strip()
        lon = (ord(code[0].upper()) - ord("A")) * 20
        lat = (ord(code[1].upper()) - ord("A")) * 10
        lon += int(code[2]) * 2
        lat += int(code[3]) * 1
        size_lon = 2.0
        size_lat = 1.0
        if len(code) >= 6:
            lon += (ord(code[4].lower()) - ord("a")) * (2 / 24)
            lat += (ord(code[5].lower()) - ord("a")) * (1 / 24)
            size_lon = 2 / 24
            size_lat = 1 / 24
        if len(code) >= 8:
            lon += int(code[6]) * (2 / 240)
            lat += int(code[7]) * (1 / 240)
            size_lon = 2 / 240
            size_lat = 1 / 240
        min_lon = lon - 180
        min_lat = lat - 90
        return min_lat, min_lon, min_lat + size_lat, min_lon + size_lon
