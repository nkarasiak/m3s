"""Quadkey grid implementation."""

from __future__ import annotations

import math
from typing import Sequence

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class QuadkeyGrid(GridBase):
    """Quadkey grid (Bing Maps)."""

    name = "quadkey"

    def __init__(self, level: int | None = None, *, precision: int | None = None):
        if precision is not None and level is not None:
            raise ValueError("Use either precision or level, not both")
        if precision is None:
            if level is None:
                raise ValueError("QuadkeyGrid requires a precision/level")
            precision = level
        super().__init__(precision)
        self.level = precision

    def _validate_precision(self) -> None:
        if not 1 <= self.precision <= 23:
            raise InvalidPrecision("Quadkey level must be between 1 and 23")

    @property
    def area_km2(self) -> float:
        earth_circumference_km = 40075.0
        tiles_per_side = 2**self.level
        tile_size_km = earth_circumference_km / tiles_per_side
        return tile_size_km * tile_size_km

    def _lat_lon_to_pixel_xy(self, lat: float, lon: float) -> tuple[int, int]:
        lat = max(-85.05112878, min(85.05112878, lat))
        lat_rad = lat * math.pi / 180
        lon_rad = lon * math.pi / 180
        map_size = 256 << self.level
        x = (lon_rad + math.pi) / (2 * math.pi)
        y = (math.pi - math.log(math.tan(math.pi / 4 + lat_rad / 2))) / (
            2 * math.pi
        )
        pixel_x = int(x * map_size)
        pixel_y = int(y * map_size)
        pixel_x = max(0, min(map_size - 1, pixel_x))
        pixel_y = max(0, min(map_size - 1, pixel_y))
        return pixel_x, pixel_y

    @staticmethod
    def _pixel_xy_to_tile_xy(pixel_x: int, pixel_y: int) -> tuple[int, int]:
        return pixel_x // 256, pixel_y // 256

    def _tile_xy_to_quadkey(self, tile_x: int, tile_y: int) -> str:
        quadkey = []
        for i in range(self.level, 0, -1):
            digit = 0
            mask = 1 << (i - 1)
            if tile_x & mask:
                digit += 1
            if tile_y & mask:
                digit += 2
            quadkey.append(str(digit))
        return "".join(quadkey)

    def _quadkey_to_tile_xy(self, quadkey: str) -> tuple[int, int]:
        tile_x = tile_y = 0
        level = len(quadkey)
        for i in range(level):
            bit = level - i
            mask = 1 << (bit - 1)
            digit = int(quadkey[i])
            if digit & 1:
                tile_x |= mask
            if digit & 2:
                tile_y |= mask
        return tile_x, tile_y

    def _tile_xy_to_lat_lon_bounds(self, tile_x: int, tile_y: int) -> Bbox:
        map_size = 256 << self.level

        def pixel_to_lat_lon(px: int, py: int) -> tuple[float, float]:
            x = px / map_size - 0.5
            y = 0.5 - py / map_size
            lon = x * 360
            lat = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi
            return lat, lon

        min_pixel_x = tile_x * 256
        max_pixel_x = (tile_x + 1) * 256
        min_pixel_y = tile_y * 256
        max_pixel_y = (tile_y + 1) * 256
        min_lat, min_lon = pixel_to_lat_lon(min_pixel_x, max_pixel_y)
        max_lat, max_lon = pixel_to_lat_lon(max_pixel_x, min_pixel_y)
        return (min_lon, min_lat, max_lon, max_lat)

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        px, py = self._lat_lon_to_pixel_xy(lat, lon)
        tile_x, tile_y = self._pixel_xy_to_tile_xy(px, py)
        quadkey = self._tile_xy_to_quadkey(tile_x, tile_y)
        return Cell(quadkey, self.level, self._tile_xy_to_lat_lon_bounds(tile_x, tile_y))

    def from_id(self, cell_id: str) -> Cell:
        if len(cell_id) != self.level:
            raise ValueError(f"Quadkey level mismatch: expected {self.level}")
        tile_x, tile_y = self._quadkey_to_tile_xy(cell_id)
        max_coord = 2**self.level
        if not (0 <= tile_x < max_coord and 0 <= tile_y < max_coord):
            raise ValueError("Invalid quadkey tile coordinates")
        return Cell(cell_id, self.level, self._tile_xy_to_lat_lon_bounds(tile_x, tile_y))

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        try:
            tile_x, tile_y = self._quadkey_to_tile_xy(cell.id)
        except Exception:
            return []
        max_coord = 2**self.level
        neighbors: list[Cell] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                new_y = tile_y + dy
                if not (0 <= new_y < max_coord):
                    continue
                new_x = (tile_x + dx) % max_coord
                quadkey = self._tile_xy_to_quadkey(new_x, new_y)
                neighbors.append(Cell(quadkey, self.level, self._tile_xy_to_lat_lon_bounds(new_x, new_y)))
        return neighbors

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)
        px1, py1 = self._lat_lon_to_pixel_xy(max_lat, min_lon)
        px2, py2 = self._lat_lon_to_pixel_xy(min_lat, max_lon)
        x1, y1 = self._pixel_xy_to_tile_xy(px1, py1)
        x2, y2 = self._pixel_xy_to_tile_xy(px2, py2)
        x_min, x_max = sorted((x1, x2))
        y_min, y_max = sorted((y1, y2))
        cells: list[Cell] = []
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                quadkey = self._tile_xy_to_quadkey(x, y)
                cells.append(Cell(quadkey, self.level, self._tile_xy_to_lat_lon_bounds(x, y)))
        return cells

    def get_quadkey_bounds(self, quadkey: str) -> Bbox:
        """Legacy helper returning bounds for a quadkey."""
        return self.from_id(quadkey).bbox

    def get_children(self, cell: Cell) -> Sequence[Cell]:
        """Legacy helper returning child quadkey cells."""
        parent_id = cell.id
        if not parent_id:
            return []
        children: list[Cell] = []
        for digit in ("0", "1", "2", "3"):
            child_id = f"{parent_id}{digit}"
            child_grid = QuadkeyGrid(precision=len(child_id))
            child_cell = child_grid.from_id(child_id)
            children.append(child_cell)
        return children

    def get_parent(self, cell: Cell) -> Cell | None:
        """Legacy helper returning parent quadkey cell."""
        parent_id = cell.id[:-1]
        if not parent_id:
            return None
        parent_grid = QuadkeyGrid(precision=len(parent_id))

    def parent(self, cell: Cell) -> Cell | None:
        return self.get_parent(cell)

    def children(self, cell: Cell) -> Sequence[Cell]:
        return self.get_children(cell)
        return parent_grid.from_id(parent_id)
