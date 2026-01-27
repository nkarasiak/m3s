"""S2 grid implementation."""

from __future__ import annotations

import warnings
from typing import Sequence

import s2sphere

from ..core.cell import Cell
from ..core.errors import InvalidPrecision
from ..core.grid import GridBase
from ..core.types import Bbox


class S2Grid(GridBase):
    """S2 grid system."""

    name = "s2"

    def __init__(self, level: int | None = None, *, precision: int | None = None):
        if precision is not None and level is not None:
            raise ValueError("Use either precision or level, not both")
        if precision is None:
            if level is None:
                raise ValueError("S2Grid requires a precision/level")
            precision = level
        super().__init__(precision)
        self.level = precision

    def _validate_precision(self) -> None:
        if not 0 <= self.precision <= 30:
            raise InvalidPrecision("S2 level must be between 0 and 30")

    @property
    def area_km2(self) -> float:
        earth_surface_km2 = 510_072_000.0
        total_cells = 6 * (4**self.level)
        return earth_surface_km2 / total_cells

    def _cell_coords(self, cell_id: s2sphere.CellId) -> tuple[list[tuple[float, float]], Bbox]:
        cell = s2sphere.Cell(cell_id)
        coords = []
        for i in range(4):
            vertex = cell.get_vertex(i)
            lat_lng = s2sphere.LatLng.from_point(vertex)
            coords.append((lat_lng.lng().degrees, lat_lng.lat().degrees))
        coords.append(coords[0])
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return coords, (min(lons), min(lats), max(lons), max(lats))

    def cell(self, lat: float, lon: float) -> Cell:
        self.validate_lat_lon(lat, lon)
        lat_lng = s2sphere.LatLng.from_degrees(lat, lon)
        cell_id = s2sphere.CellId.from_lat_lng(lat_lng).parent(self.level)
        coords, bbox = self._cell_coords(cell_id)
        return Cell(cell_id.to_token(), self.level, bbox, _coords=coords)

    def from_id(self, cell_id: str) -> Cell:
        try:
            s2_id = s2sphere.CellId.from_token(cell_id)
        except Exception as exc:
            raise ValueError(f"Invalid S2 cell token: {cell_id}") from exc
        coords, bbox = self._cell_coords(s2_id)
        return Cell(cell_id, s2_id.level(), bbox, _coords=coords)

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
        try:
            cell_id = s2sphere.CellId.from_token(cell.id)
        except Exception:
            return []
        neighbors: dict[str, Cell] = {}
        for neighbor_id in cell_id.get_edge_neighbors():
            if neighbor_id is None:
                continue
            coords, bbox = self._cell_coords(neighbor_id)
            token = neighbor_id.to_token()
            neighbors[token] = Cell(token, neighbor_id.level(), bbox, _coords=coords)
        for i in range(4):
            for vertex_neighbor_id in cell_id.get_vertex_neighbors(i):
                if vertex_neighbor_id is None:
                    continue
                if vertex_neighbor_id.level() != self.level:
                    continue
                coords, bbox = self._cell_coords(vertex_neighbor_id)
                token = vertex_neighbor_id.to_token()
                neighbors.setdefault(token, Cell(token, self.level, bbox, _coords=coords))
        return list(neighbors.values())

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)
        try:
            rect = s2sphere.LatLngRect(
                s2sphere.LatLng.from_degrees(min_lat, min_lon),
                s2sphere.LatLng.from_degrees(max_lat, max_lon),
            )
            coverer = s2sphere.RegionCoverer()
            coverer.min_level = self.level
            coverer.max_level = self.level
            coverer.max_cells = 1000
            covering = coverer.get_covering(rect)
            cells = []
            for cell_id in covering:
                coords, cbbox = self._cell_coords(cell_id)
                cells.append(Cell(cell_id.to_token(), self.level, cbbox, _coords=coords))
            return cells
        except Exception as exc:
            warnings.warn(f"Failed to get S2 covering: {exc}", stacklevel=2)
            return []

    def get_children(self, cell: Cell) -> Sequence[Cell]:
        """Legacy helper returning child S2 cells."""
        try:
            cell_id = s2sphere.CellId.from_token(cell.id)
        except Exception:
            return []
        if cell_id.level() >= 30:
            return []
        child_level = cell_id.level() + 1
        children: list[Cell] = []
        for child in cell_id.children(child_level):
            coords, bbox = self._cell_coords(child)
            children.append(Cell(child.to_token(), child_level, bbox, _coords=coords))
        return children

    def get_parent(self, cell: Cell) -> Cell | None:
        """Legacy helper returning parent S2 cell."""
        try:
            cell_id = s2sphere.CellId.from_token(cell.id)
        except Exception:
            return None
        if cell_id.level() == 0:
            return None
        parent = cell_id.parent(cell_id.level() - 1)
        coords, bbox = self._cell_coords(parent)
        return Cell(parent.to_token(), parent.level(), bbox, _coords=coords)

    def parent(self, cell: Cell) -> Cell | None:
        return self.get_parent(cell)

    def children(self, cell: Cell) -> Sequence[Cell]:
        return self.get_children(cell)
