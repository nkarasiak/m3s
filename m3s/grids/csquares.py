"""C-squares grid implementation."""

from __future__ import annotations

from typing import Sequence

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class CSquaresGrid(GridBase):
    """C-squares grid system."""

    name = "csquares"

    def __init__(self, precision: int = 3):
        super().__init__(precision)

    def _validate_precision(self) -> None:
        if not 1 <= self.precision <= 5:
            raise InvalidPrecision("C-squares precision must be between 1 and 5")

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        code = self._encode(lat, lon, self.precision)
        return self.from_id(code)

    def from_id(self, cell_id: str) -> Cell:
        min_lat, min_lon, max_lat, max_lon = self._decode(cell_id)
        precision = self._precision_from_id(cell_id)
        return Cell(cell_id, precision, (min_lon, min_lat, max_lon, max_lat))

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        try:
            min_lat, min_lon, max_lat, max_lon = self._decode(cell.id)
        except Exception:
            return []
        lat_step = max_lat - min_lat
        lon_step = max_lon - min_lon
        coords = [
            (min_lat + lat_step, min_lon),
            (min_lat - lat_step, min_lon),
            (min_lat, min_lon + lon_step),
            (min_lat, min_lon - lon_step),
            (min_lat + lat_step, min_lon + lon_step),
            (min_lat + lat_step, min_lon - lon_step),
            (min_lat - lat_step, min_lon + lon_step),
            (min_lat - lat_step, min_lon - lon_step),
        ]
        neighbors = []
        for n_lat, n_lon in coords:
            if -90 <= n_lat <= 90 and -180 <= n_lon <= 180:
                neighbor = self.cell(n_lat, n_lon)
                if neighbor.id != cell.id:
                    neighbors.append(neighbor)
        return list({n.id: n for n in neighbors}.values())

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)
        cell_size = self._cell_size(self.precision)
        margin = cell_size * 0.5
        lat = max(-90, min_lat - margin)
        max_lat = min(90, max_lat + margin)
        lon = max(-180, min_lon - margin)
        max_lon = min(180, max_lon + margin)
        cells = set()
        while lat < max_lat:
            lon = max(-180, min_lon - margin)
            while lon < max_lon:
                cells.add(self.cell(lat, lon))
                lon += cell_size
            lat += cell_size
        return list(cells)

    def _encode(self, lat: float, lon: float, precision: int) -> str:
        lat = max(-90, min(90, lat))
        lon = max(-180, min(180, lon))
        lat_sign = "1" if lat >= 0 else "7"
        lon_sign = "1" if lon >= 0 else "7"
        lat_abs = abs(lat)
        lon_abs = abs(lon)
        code = f"{lat_sign}{lon_sign}{int(lat_abs):02d}{int(lon_abs):03d}"
        if precision == 1:
            return code
        cell_size = self._cell_size(precision)
        lat_frac = int((lat_abs % 1) / cell_size)
        lon_frac = int((lon_abs % 1) / cell_size)
        return f"{code}:{lat_frac:02d}{lon_frac:02d}"

    def _decode(self, identifier: str) -> tuple[float, float, float, float]:
        parts = identifier.split(":")
        base = parts[0]
        lat_sign = 1 if base[0] == "1" else -1
        lon_sign = 1 if base[1] == "1" else -1
        lat_base = int(base[2:4])
        lon_base = int(base[4:7])
        precision = self._precision_from_id(identifier)
        cell_size = self._cell_size(precision)
        lat = lat_sign * lat_base
        lon = lon_sign * lon_base
        if precision > 1 and len(parts) > 1:
            lat_offset = int(parts[1][:2]) * cell_size
            lon_offset = int(parts[1][2:]) * cell_size
            lat += lat_offset * lat_sign
            lon += lon_offset * lon_sign
        min_lat = lat
        min_lon = lon
        max_lat = lat + cell_size * lat_sign
        max_lon = lon + cell_size * lon_sign
        if min_lat > max_lat:
            min_lat, max_lat = max_lat, min_lat
        if min_lon > max_lon:
            min_lon, max_lon = max_lon, min_lon
        return min_lat, min_lon, max_lat, max_lon

    def _precision_from_id(self, identifier: str) -> int:
        return 1 if ":" not in identifier else 3

    def _cell_size(self, precision: int) -> float:
        sizes = {1: 10.0, 2: 5.0, 3: 1.0, 4: 0.5, 5: 0.1}
        return sizes[precision]
