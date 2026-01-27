"""MGRS grid implementation."""

from __future__ import annotations

import math
from typing import Sequence

import mgrs
from pyproj import Transformer
from shapely.geometry import Polygon

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class MGRSGrid(GridBase):
    """MGRS (Military Grid Reference System) grid system."""

    name = "mgrs"

    def __init__(self, precision: int = 1):
        super().__init__(precision)
        self._mgrs = mgrs.MGRS()

    def _validate_precision(self) -> None:
        if not 0 <= self.precision <= 5:
            raise InvalidPrecision("MGRS precision must be between 0 and 5")

    @property
    def area_km2(self) -> float:
        grid_size = self._grid_size_m()
        return (grid_size * grid_size) / 1_000_000

    def _grid_size_m(self) -> float:
        sizes = {0: 100000, 1: 10000, 2: 1000, 3: 100, 4: 10, 5: 1}
        return sizes[self.precision]

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        mgrs_id = self._mgrs.toMGRS(lat, lon, MGRSPrecision=self.precision)
        return self.from_id(mgrs_id)

    def from_id(self, cell_id: str) -> Cell:
        try:
            lat, lon = self._mgrs.toLatLon(cell_id)
        except Exception as exc:
            raise ValueError(f"Invalid MGRS id: {cell_id}") from exc
        polygon = self._create_polygon(cell_id, lat, lon, self._grid_size_m())
        min_lon, min_lat, max_lon, max_lat = polygon.bounds
        return Cell(cell_id, self.precision, (min_lon, min_lat, max_lon, max_lat))

    def _create_polygon(
        self, mgrs_id: str, center_lat: float, center_lon: float, grid_size: float
    ) -> Polygon:
        utm_zone = self._utm_epsg_from_mgrs(mgrs_id)
        transformer_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{utm_zone}")
        transformer_to_wgs84 = Transformer.from_crs(f"EPSG:{utm_zone}", "EPSG:4326")
        center_x, center_y = transformer_to_utm.transform(center_lat, center_lon)
        half = grid_size / 2
        corners_utm = [
            (center_x - half, center_y - half),
            (center_x + half, center_y - half),
            (center_x + half, center_y + half),
            (center_x - half, center_y + half),
            (center_x - half, center_y - half),
        ]
        corners = []
        for x, y in corners_utm:
            lat, lon = transformer_to_wgs84.transform(x, y)
            corners.append((lon, lat))
        return Polygon(corners)

    def _utm_epsg_from_mgrs(self, mgrs_id: str) -> int:
        zone_letter = mgrs_id[:3]
        zone_number = int(zone_letter[:2])
        hemisphere_letter = zone_letter[2]
        if hemisphere_letter in "CDEFGHJKLM":
            return 32700 + zone_number
        return 32600 + zone_number

    def _grid_size_to_degrees(self, lat: float) -> float:
        grid_size_m = self._grid_size_m()
        lat_deg_per_m = 1.0 / 111320.0
        lat_clamped = max(-89.9, min(89.9, lat))
        cos_lat = max(0.001, math.cos(math.radians(lat_clamped)))
        return grid_size_m * lat_deg_per_m

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        try:
            lat, lon = self._mgrs.toLatLon(cell.id)
        except Exception:
            return []
        grid_size_deg = self._grid_size_to_degrees(lat)
        coords = [
            (lat + grid_size_deg, lon),
            (lat - grid_size_deg, lon),
            (lat, lon + grid_size_deg),
            (lat, lon - grid_size_deg),
            (lat + grid_size_deg, lon + grid_size_deg),
            (lat + grid_size_deg, lon - grid_size_deg),
            (lat - grid_size_deg, lon + grid_size_deg),
            (lat - grid_size_deg, lon - grid_size_deg),
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
        cells = set()
        grid_size_deg = self._grid_size_to_degrees((min_lat + max_lat) / 2)
        margin = grid_size_deg * 1.5
        extended_min_lat = min_lat - margin
        extended_max_lat = max_lat + margin
        extended_min_lon = min_lon - margin
        extended_max_lon = max_lon + margin
        bbox_polygon = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )
        bbox_width = extended_max_lon - extended_min_lon
        bbox_height = extended_max_lat - extended_min_lat
        lat_samples = max(10, min(50, int(bbox_height / grid_size_deg) * 3 + 5))
        lon_samples = max(10, min(50, int(bbox_width / grid_size_deg) * 3 + 5))
        lat_step = bbox_height / lat_samples if lat_samples > 1 else bbox_height
        lon_step = bbox_width / lon_samples if lon_samples > 1 else bbox_width
        for i in range(lat_samples + 1):
            for j in range(lon_samples + 1):
                lat = extended_min_lat + (i * lat_step)
                lon = extended_min_lon + (j * lon_step)
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    cell = self.cell(lat, lon)
                    cell_bbox = cell.bbox
                    cell_polygon = Polygon(
                        [
                            (cell_bbox[0], cell_bbox[1]),
                            (cell_bbox[2], cell_bbox[1]),
                            (cell_bbox[2], cell_bbox[3]),
                            (cell_bbox[0], cell_bbox[3]),
                            (cell_bbox[0], cell_bbox[1]),
                        ]
                    )
                    if cell_polygon.intersects(bbox_polygon):
                        cells.add(cell)
        return list(cells)
