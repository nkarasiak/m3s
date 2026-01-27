"""Plus code (Open Location Code) grid implementation."""

from __future__ import annotations

from typing import Sequence

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class PlusCodeGrid(GridBase):
    """Plus codes (Open Location Code) grid system."""

    name = "pluscode"
    ALPHABET = "23456789CFGHJMPQRVWX"
    BASE = len(ALPHABET)
    GRID_SIZES = [
        20.0,
        1.0,
        0.05,
        0.0025,
        0.000125,
        0.00000625,
        0.0000003125,
        0.000000015625,
    ]

    def __init__(self, precision: int = 4):
        super().__init__(precision)

    def _validate_precision(self) -> None:
        if not 1 <= self.precision <= 7:
            raise InvalidPrecision("Plus code precision must be between 1 and 7")

    @property
    def area_km2(self) -> float:
        size_deg = self.GRID_SIZES[self.precision]
        size_km = size_deg * 111.32
        return size_km * size_km

    def encode(self, lat: float, lon: float) -> str:
        lat = max(-90, min(90, lat))
        lon = ((lon + 180) % 360) - 180
        lat_range = lat + 90
        lon_range = lon + 180
        code = ""
        lat_precision = 20.0
        lon_precision = 20.0
        for i in range(self.precision):
            lat_digit = int(lat_range / lat_precision)
            lon_digit = int(lon_range / lon_precision)
            lat_digit = min(lat_digit, self.BASE - 1)
            lon_digit = min(lon_digit, self.BASE - 1)
            code += self.ALPHABET[lon_digit] + self.ALPHABET[lat_digit]
            lat_range -= lat_digit * lat_precision
            lon_range -= lon_digit * lon_precision
            lat_precision /= self.BASE
            lon_precision /= self.BASE
            if i == 1:
                code += "+"
        return code

    def decode(self, code: str) -> Bbox:
        code = code.replace("+", "").upper()
        lat_range = 0.0
        lon_range = 0.0
        lat_precision = 20.0
        lon_precision = 20.0
        pairs_decoded = 0
        for i in range(0, min(len(code), self.precision * 2), 2):
            if i + 1 >= len(code):
                break
            lon_char = code[i]
            lat_char = code[i + 1]
            if lat_char in self.ALPHABET and lon_char in self.ALPHABET:
                lat_digit = self.ALPHABET.index(lat_char)
                lon_digit = self.ALPHABET.index(lon_char)
                lat_range += lat_digit * lat_precision
                lon_range += lon_digit * lon_precision
                lat_precision /= self.BASE
                lon_precision /= self.BASE
                pairs_decoded += 1
        if pairs_decoded > 0:
            final_lat_precision = lat_precision * self.BASE
            final_lon_precision = lon_precision * self.BASE
        else:
            final_lat_precision = 20.0
            final_lon_precision = 20.0
        south = lat_range - 90
        west = lon_range - 180
        north = south + final_lat_precision
        east = west + final_lon_precision
        return (west, south, east, north)

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        code = self.encode(lat, lon)
        return self.from_id(code)

    def from_id(self, cell_id: str) -> Cell:
        bbox = self.decode(cell_id)
        return Cell(cell_id, self.precision, bbox)

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        west, south, east, north = self.decode(cell.id)
        lat_step = north - south
        lon_step = east - west
        lat_center = (south + north) / 2
        lon_center = (west + east) / 2
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
        step = self.GRID_SIZES[self.precision]
        lat = min_lat
        cells = set()
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                cells.add(self.cell(lat, lon))
                lon += step
            lat += step
        return list(cells)
