"""Cell model for grid systems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from shapely.geometry import Polygon, box

from .types import Bbox, CellId, LonLat
from ..ops.area import polygon_area_km2


@dataclass(slots=True)
class Cell:
    """Lightweight grid cell with lazy geometry."""

    id: CellId
    precision: int
    bbox: Bbox
    _coords: Sequence[LonLat] | None = field(default=None, repr=False)
    _polygon: Polygon | None = field(default=None, repr=False)
    _area_km2: float | None = field(default=None, repr=False)

    @property
    def polygon(self) -> Polygon:
        """Return the cell polygon, created lazily."""
        if self._polygon is None:
            if self._coords is not None:
                self._polygon = Polygon(self._coords)
            else:
                min_lon, min_lat, max_lon, max_lat = self.bbox
                self._polygon = box(min_lon, min_lat, max_lon, max_lat)
        return self._polygon

    @property
    def identifier(self) -> CellId:
        """Legacy alias for id."""
        return self.id

    @property
    def area_km2(self) -> float:
        """Area in square kilometers using an equal-area projection."""
        if self._area_km2 is None:
            self._area_km2 = polygon_area_km2(self.polygon)
        return self._area_km2

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cell):
            return False
        return self.id == other.id
