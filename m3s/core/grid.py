"""Grid protocol and base class."""

from __future__ import annotations

from typing import Protocol, Sequence

from .cell import Cell
from .errors import InvalidLatitude, InvalidLongitude, InvalidPrecision
from .types import Bbox, CellId


def _validate_lat(lat: float) -> None:
    if not (-90.0 <= lat <= 90.0):
        raise InvalidLatitude(f"Latitude out of range: {lat}")


def _validate_lon(lon: float) -> None:
    if not (-180.0 <= lon <= 180.0):
        raise InvalidLongitude(f"Longitude out of range: {lon}")


def _normalize_bbox(bbox: Bbox) -> Bbox:
    min_lon, min_lat, max_lon, max_lat = bbox
    if min_lon > max_lon or min_lat > max_lat:
        raise ValueError(f"Invalid bbox: {bbox}")
    return bbox


class GridProtocol(Protocol):
    """Grid interface implemented by all grid systems."""

    name: str
    precision: int

    def cell(self, lat: float, lon: float) -> Cell:
        """Return the cell containing the point (lat, lon)."""

    def from_id(self, cell_id: CellId) -> Cell:
        """Return a cell from its identifier."""

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        """Return neighboring cells for the given cell."""

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        """Return all cells intersecting a bounding box."""

    def cover(self, geometry, *, precision: int | None = None) -> Sequence[Cell]:
        """Return all cells intersecting a geometry."""

    def parent(self, cell: Cell) -> Cell | None:
        """Return the parent cell, if supported."""

    def children(self, cell: Cell) -> Sequence[Cell]:
        """Return child cells, if supported."""

    def metrics(self, *, at=None) -> dict[str, float]:
        """Return metrics for the current precision."""

    @property
    def area_km2(self) -> float:
        """Theoretical area of a cell at this precision."""


class GridBase:
    """Base class with shared validation and helpers."""

    name: str = "grid"

    def __init__(self, precision: int):
        self.precision = precision
        self._validate_precision()

    def _validate_precision(self) -> None:
        raise InvalidPrecision("Grid must implement precision validation")

    @staticmethod
    def validate_lat_lon(lat: float, lon: float) -> None:
        _validate_lat(lat)
        _validate_lon(lon)

    @staticmethod
    def normalize_bbox(bbox: Bbox) -> Bbox:
        return _normalize_bbox(bbox)

    def intersects(self, gdf, target_crs: str = "EPSG:4326"):
        from ..ops.intersects import intersects

        return intersects(self, gdf, target_crs=target_crs)

    def cover(self, geometry, *, precision: int | None = None) -> Sequence[Cell]:
        """Return all cells intersecting a geometry."""
        if precision is not None and precision != self.precision:
            grid = self.__class__(precision=precision)
            return grid.cover(geometry)
        if isinstance(geometry, tuple) and len(geometry) == 4:
            return self.cells_in_bbox(geometry)
        try:
            bounds = geometry.bounds
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError("Unsupported geometry for cover()") from exc
        cells = list(self.cells_in_bbox(bounds))
        try:
            return [cell for cell in cells if geometry.intersects(cell.polygon)]
        except Exception:
            return cells

    def parent(self, cell: Cell) -> Cell | None:
        raise NotImplementedError("parent() is not supported for this grid")

    def children(self, cell: Cell) -> Sequence[Cell]:
        raise NotImplementedError("children() is not supported for this grid")

    def metrics(self, *, at=None) -> dict[str, float]:
        # Basic approximation derived from area; grids may override.
        area = self.area_km2
        edge_m = (area**0.5) * 1000.0
        return {"area_km2": area, "size_m": edge_m}

    # Legacy API compatibility helpers
    def get_cell_from_point(self, lat: float, lon: float) -> Cell:
        return self.cell(lat, lon)

    def get_cell_from_identifier(self, identifier: CellId) -> Cell:
        return self.from_id(identifier)

    def get_neighbors(self, cell: Cell) -> Sequence[Cell]:
        return list(self.neighbors(cell))

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> Sequence[Cell]:
        return self.cells_in_bbox((min_lon, min_lat, max_lon, max_lat))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(precision={self.precision})"
