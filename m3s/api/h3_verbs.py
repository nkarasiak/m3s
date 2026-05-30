"""
h3-py vocabulary layer for m3s grid systems.

``H3VerbsMixin`` gives every backend singleton (``m3s.H3``, ``m3s.S2``, …) the
verb *names* and *capabilities* of the `h3-py` library — ``latlng_to_cell``,
``cell_to_boundary``, ``grid_disk``, ``cell_to_parent``, … — while keeping m3s's
object model: cell-producing verbs return :class:`GridCell` /
:class:`GridCellCollection` rather than bare string ids. Verbs accept either a
``GridCell`` or an id ``str``. The existing ``from_*`` API is untouched.

The mixin delegates to the wrapped ``*Grid`` instances through the host
:class:`GridWrapper` (``_get_grid`` / ``_get_precision_range``) and the backend
hooks defined on :class:`m3s.base.BaseGrid` (``identifier_to_precision``,
``native_cell_center``, ``native_cell_area``, ``native_compact`` …). Capabilities
a backend cannot support raise ``NotImplementedError``.

Coordinate convention: like h3-py, all lat/lng arguments and returns are
``(lat, lng)`` in degrees — distinct from the GIS-native ``(lon, lat)`` order of
``from_point`` / ``GridCell.bounds``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Tuple, Type, Union

from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from ..base import BaseGrid, GridCell
from .grid_collection import GridCellCollection

# Mean Earth radius (km), matching h3's WGS84 authalic sphere.
_EARTH_RADIUS_KM = 6371.0088

CellArg = Union[GridCell, str]


class H3VerbsMixin:
    """
    h3-py verb vocabulary for a :class:`GridWrapper` backend.

    Expects the host to provide ``_get_grid(precision)``,
    ``_get_precision_range()``, ``_default_precision``, ``_grid_class`` and
    ``from_polygon`` (all supplied by :class:`GridWrapper`).
    """

    if TYPE_CHECKING:
        # Host (GridWrapper) interface — declared for type-checking only.
        _default_precision: int
        _grid_class: Type[BaseGrid]

        def _get_grid(self, precision: int) -> BaseGrid: ...

        def _get_precision_range(self) -> Tuple[int, int]: ...

        def from_polygon(
            self, geometry: Any, precision: Optional[int] = None
        ) -> GridCellCollection:
            """Host hook: see :meth:`GridWrapper.from_polygon`."""

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def _resolve(self, cell: CellArg) -> Tuple[BaseGrid, GridCell]:
        """
        Resolve a cell argument to its (grid, GridCell).

        A ``GridCell`` carries its precision, so no search is needed. A bare id
        string is resolved via the backend's ``identifier_to_precision`` hook,
        falling back to a validated precision sweep (the id must be the
        canonical cell for its own centre at the candidate precision).
        """
        if isinstance(cell, GridCell):
            return self._get_grid(cell.precision), cell

        identifier = cell
        lo, hi = self._get_precision_range()

        # Fast path: backend decodes precision straight from the id.
        probe = self._get_grid(self._default_precision)
        native_precision = probe.identifier_to_precision(identifier)
        if native_precision is not None and lo <= native_precision <= hi:
            grid = self._get_grid(native_precision)
            return grid, grid.get_cell_from_identifier(identifier)

        # Validated sweep across the backend's precision range.
        first_parse: Tuple[BaseGrid, GridCell] | None = None
        for candidate in range(lo, hi + 1):
            grid = self._get_grid(candidate)
            try:
                resolved = grid.get_cell_from_identifier(identifier)
            except Exception:
                continue
            if first_parse is None:
                first_parse = (grid, resolved)
            try:
                lon, lat = resolved.centroid
                if grid.get_cell_from_point(lat, lon).identifier == identifier:
                    return grid, resolved
            except Exception:
                continue

        if first_parse is not None:
            return first_parse
        raise ValueError(
            f"Cannot parse identifier {identifier!r} as a "
            f"{self._grid_class.__name__} cell"
        )

    @staticmethod
    def _id(cell: CellArg) -> str:
        """Extract the id string from a GridCell or pass a str through."""
        return cell.identifier if isinstance(cell, GridCell) else cell

    def _collection(self, cells: List[GridCell]) -> GridCellCollection:
        """Wrap cells in a GridCellCollection bound to this wrapper."""
        return GridCellCollection(cells, self)

    def _require_h3(self, verb: str) -> None:
        """Guard for verbs only the H3 backend can serve."""
        if self._grid_class.__name__ != "H3Grid":
            raise NotImplementedError(
                f"{verb!r} is only available on the H3 backend "
                f"(not {self._grid_class.__name__})"
            )

    # ==================================================================
    # Tier 1 — indexing, inspection, measurement
    # ==================================================================

    def latlng_to_cell(self, lat: float, lng: float, res: int) -> GridCell:
        """
        Cell containing a point at a given resolution (h3 ``latlng_to_cell``).

        Parameters
        ----------
        lat, lng : float
            Latitude and longitude in degrees, h3-native ``(lat, lng)`` order.
        res : int
            Target precision/resolution.

        Returns
        -------
        GridCell
            The cell containing the point.
        """
        grid = self._get_grid(res)
        return grid.get_cell_from_point(lat, lng)

    def cell_to_latlng(self, cell: CellArg) -> Tuple[float, float]:
        """
        Cell centre as ``(lat, lng)`` (h3 ``cell_to_latlng``).

        Uses the backend's exact centre when available
        (``native_cell_center``), else the polygon centroid.
        """
        grid, resolved = self._resolve(cell)
        native = grid.native_cell_center(resolved.identifier)
        if native is not None:
            return native
        lon, lat = resolved.centroid
        return (lat, lon)

    def cell_to_boundary(self, cell: CellArg) -> Tuple[Tuple[float, float], ...]:
        """
        Cell boundary as ordered ``(lat, lng)`` pairs (h3 ``cell_to_boundary``).

        Returns an open ring (no repeated closing vertex), matching h3.
        """
        _, resolved = self._resolve(cell)
        coords = list(resolved.polygon.exterior.coords)
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        return tuple((lat, lon) for lon, lat in coords)

    def get_resolution(self, cell: CellArg) -> int:
        """Resolution/precision of a cell (h3 ``get_resolution``)."""
        if isinstance(cell, GridCell):
            return cell.precision
        return self._resolve(cell)[1].precision

    def is_valid_cell(self, cell: CellArg) -> bool:
        """Whether ``cell`` is a valid cell of this backend (h3 ``is_valid_cell``)."""
        identifier = self._id(cell)
        lo, hi = self._get_precision_range()
        probe = self._get_grid(self._default_precision)
        native_precision = probe.identifier_to_precision(identifier)
        if native_precision is not None:
            if not (lo <= native_precision <= hi):
                return False
            return self._get_grid(native_precision).is_valid_identifier(identifier)
        try:
            self._resolve(identifier)
            return True
        except ValueError:
            return False

    def cell_area(self, cell: CellArg, unit: str = "km^2") -> float:
        """
        Area of a cell in ``unit`` (h3 ``cell_area``).

        ``unit`` is one of ``'km^2'``, ``'m^2'``, ``'rads^2'``. Uses the
        backend's exact area when available, else the projected polygon area.
        """
        grid, resolved = self._resolve(cell)
        native = grid.native_cell_area(resolved.identifier, unit)
        if native is not None:
            return native
        return self._convert_area(resolved.area_km2, unit)

    @staticmethod
    def _convert_area(area_km2: float, unit: str) -> float:
        if unit == "km^2":
            return area_km2
        if unit == "m^2":
            return area_km2 * 1_000_000.0
        if unit == "rads^2":
            return area_km2 / (_EARTH_RADIUS_KM**2)
        raise ValueError(f"Unknown area unit {unit!r}; use km^2, m^2 or rads^2")

    # ==================================================================
    # Tier 2 — hierarchy & (un)compaction
    # ==================================================================

    def cell_to_parent(self, cell: CellArg, res: int | None = None) -> GridCell:
        """
        Parent cell at coarser ``res`` (h3 ``cell_to_parent``).

        ``res`` defaults to one level coarser. Raises ``NotImplementedError``
        on non-hierarchical backends.
        """
        _, resolved = self._resolve(cell)
        current = resolved.precision
        if res is None:
            res = current - 1
        if res > current:
            raise ValueError(f"parent res ({res}) must be <= cell res ({current})")
        node = resolved
        precision = current
        while precision > res:
            g = self._get_grid(precision)
            if not hasattr(g, "get_parent"):
                raise NotImplementedError(
                    f"{self._grid_class.__name__} is not hierarchical; "
                    "cell_to_parent is unavailable"
                )
            parent = g.get_parent(node)
            if parent is None:
                raise ValueError(f"no parent below resolution {precision}")
            node = parent
            precision -= 1
        return node

    def cell_to_children(
        self, cell: CellArg, res: int | None = None
    ) -> GridCellCollection:
        """
        Children at finer ``res`` (h3 ``cell_to_children``).

        ``res`` defaults to one level finer. Raises ``NotImplementedError`` on
        non-hierarchical backends.
        """
        _, resolved = self._resolve(cell)
        current = resolved.precision
        if res is None:
            res = current + 1
        if res < current:
            raise ValueError(f"children res ({res}) must be >= cell res ({current})")
        nodes = [resolved]
        precision = current
        while precision < res:
            g = self._get_grid(precision)
            if not hasattr(g, "get_children"):
                raise NotImplementedError(
                    f"{self._grid_class.__name__} is not hierarchical; "
                    "cell_to_children is unavailable"
                )
            nxt: List[GridCell] = []
            for node in nodes:
                nxt.extend(g.get_children(node))
            nodes = nxt
            precision += 1
        return self._collection(nodes)

    def cell_to_children_size(self, cell: CellArg, res: int | None = None) -> int:
        """Return the number of children at ``res`` (h3 ``cell_to_children_size``)."""
        return len(self.cell_to_children(cell, res))

    def compact_cells(self, cells: Iterable[CellArg]) -> GridCellCollection:
        """
        Merge a same-resolution set into a minimal mixed-resolution set.

        Matches h3 ``compact_cells``. Uses the backend's native compaction when
        available, else a generic hierarchical roll-up.
        """
        ids = [self._id(c) for c in cells]
        if not ids:
            return self._collection([])
        grid = self._get_grid(self._default_precision)
        native = grid.native_compact(ids)
        if native is not None:
            return self._collection([self._resolve(i)[1] for i in native])
        return self._collection(self._generic_compact(ids))

    def uncompact_cells(self, cells: Iterable[CellArg], res: int) -> GridCellCollection:
        """Expand a compacted set to all cells at ``res`` (h3 ``uncompact_cells``)."""
        ids = [self._id(c) for c in cells]
        if not ids:
            return self._collection([])
        grid = self._get_grid(self._default_precision)
        native = grid.native_uncompact(ids, res)
        if native is not None:
            return self._collection([self._resolve(i)[1] for i in native])
        out: List[GridCell] = []
        for identifier in ids:
            _, resolved = self._resolve(identifier)
            if resolved.precision >= res:
                out.append(resolved)
            else:
                out.extend(self.cell_to_children(resolved, res))
        return self._collection(out)

    def _generic_compact(self, ids: List[str]) -> List[GridCell]:
        """Hierarchical roll-up: replace complete sibling sets with their parent."""
        lo, _ = self._get_precision_range()
        remaining = set(ids)
        cells = {i: self._resolve(i)[1] for i in ids}
        changed = True
        while changed:
            changed = False
            by_parent: dict[str, Tuple[GridCell, GridCell]] = {}
            for identifier in list(remaining):
                cell = cells[identifier]
                if cell.precision <= lo:
                    continue
                g = self._get_grid(cell.precision)
                if not hasattr(g, "get_parent") or not hasattr(g, "get_children"):
                    raise NotImplementedError(
                        f"{self._grid_class.__name__} is not hierarchical; "
                        "compact_cells is unavailable"
                    )
                parent = g.get_parent(cell)
                if parent is None:
                    continue
                by_parent[parent.identifier] = (parent, cell)
            for parent_id, (parent, _child) in by_parent.items():
                pg = self._get_grid(parent.precision)
                siblings = {
                    c.identifier
                    for c in pg.get_children(parent)  # type: ignore[attr-defined]
                }
                if siblings and siblings.issubset(remaining):
                    remaining -= siblings
                    remaining.add(parent_id)
                    cells[parent_id] = parent
                    changed = True
        return [cells[i] for i in remaining]

    # ==================================================================
    # Tier 3 — traversal (generic BFS over get_neighbors)
    # ==================================================================

    def grid_disk(self, cell: CellArg, k: int = 1) -> GridCellCollection:
        """All cells within grid distance ``<= k`` (filled disk, h3 ``grid_disk``)."""
        grid, resolved = self._resolve(cell)
        rings = self._bfs_rings(grid, resolved, k)
        out: List[GridCell] = []
        for ring in rings:
            out.extend(ring.values())
        return self._collection(out)

    def grid_ring(self, cell: CellArg, k: int = 1) -> GridCellCollection:
        """Cells at exact grid distance ``== k`` (hollow ring, h3 ``grid_ring``)."""
        grid, resolved = self._resolve(cell)
        rings = self._bfs_rings(grid, resolved, k)
        if k < len(rings):
            return self._collection(list(rings[k].values()))
        return self._collection([])

    def grid_distance(self, cell1: CellArg, cell2: CellArg) -> int:
        """
        Grid steps between two cells (h3 ``grid_distance``).

        Raises ``ValueError`` if no path is found within a bounded search.
        """
        grid, start = self._resolve(cell1)
        target = self._id(cell2)
        if start.identifier == target:
            return 0
        visited = {start.identifier}
        frontier = [start]
        max_steps = 256
        for distance in range(1, max_steps + 1):
            nxt: List[GridCell] = []
            for node in frontier:
                for neighbor in grid.get_neighbors(node):
                    if neighbor.identifier == target:
                        return distance
                    if neighbor.identifier not in visited:
                        visited.add(neighbor.identifier)
                        nxt.append(neighbor)
            if not nxt:
                break
            frontier = nxt
        raise ValueError("cells are not connected within the search bound")

    def grid_path_cells(self, start: CellArg, end: CellArg) -> GridCellCollection:
        """
        Return a shortest path of cells from ``start`` to ``end``.

        Matches h3 ``grid_path_cells`` (membership; ordering is start→end).
        """
        grid, origin = self._resolve(start)
        target = self._id(end)
        if origin.identifier == target:
            return self._collection([origin])
        previous: dict[str, GridCell | None] = {origin.identifier: None}
        cell_by_id = {origin.identifier: origin}
        frontier = [origin]
        max_steps = 256
        found = False
        for _ in range(max_steps):
            nxt: List[GridCell] = []
            for node in frontier:
                for neighbor in grid.get_neighbors(node):
                    if neighbor.identifier not in previous:
                        previous[neighbor.identifier] = node
                        cell_by_id[neighbor.identifier] = neighbor
                        if neighbor.identifier == target:
                            found = True
                            break
                        nxt.append(neighbor)
                if found:
                    break
            if found or not nxt:
                break
            frontier = nxt
        if target not in previous:
            raise ValueError("cells are not connected within the search bound")
        # Reconstruct path end -> start, then reverse.
        path: List[GridCell] = []
        cursor: GridCell | None = cell_by_id[target]
        while cursor is not None:
            path.append(cursor)
            cursor = previous[cursor.identifier]
        path.reverse()
        return self._collection(path)

    def are_neighbor_cells(self, cell1: CellArg, cell2: CellArg) -> bool:
        """Whether two cells are adjacent (h3 ``are_neighbor_cells``)."""
        grid, resolved = self._resolve(cell1)
        target = self._id(cell2)
        return any(n.identifier == target for n in grid.get_neighbors(resolved))

    @staticmethod
    def _bfs_rings(
        grid: BaseGrid, start: GridCell, k: int
    ) -> List[dict[str, GridCell]]:
        """BFS layers 0..k keyed by id; ring[d] holds cells at exact distance d."""
        rings: List[dict[str, GridCell]] = [{start.identifier: start}]
        seen = {start.identifier}
        for _ in range(max(k, 0)):
            current = rings[-1]
            nxt: dict[str, GridCell] = {}
            for node in current.values():
                for neighbor in grid.get_neighbors(node):
                    if neighbor.identifier not in seen:
                        seen.add(neighbor.identifier)
                        nxt[neighbor.identifier] = neighbor
            rings.append(nxt)
            if not nxt:
                break
        return rings

    def great_circle_distance(
        self,
        latlng1: Tuple[float, float],
        latlng2: Tuple[float, float],
        unit: str = "km",
    ) -> float:
        """
        Return the haversine distance between two ``(lat, lng)`` points.

        Matches h3 ``great_circle_distance``. ``unit`` is ``'km'``, ``'m'`` or
        ``'rads'``.
        """
        lat1, lng1 = latlng1
        lat2, lng2 = latlng2
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lng2 - lng1)
        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        )
        rads = 2 * math.asin(min(1.0, math.sqrt(a)))
        if unit == "rads":
            return rads
        km = _EARTH_RADIUS_KM * rads
        if unit == "km":
            return km
        if unit == "m":
            return km * 1000.0
        raise ValueError(f"Unknown distance unit {unit!r}; use km, m or rads")

    # ==================================================================
    # Region fill / GeoJSON (generic, returns objects)
    # ==================================================================

    def polygon_to_cells(self, shape_like: Any, res: int) -> GridCellCollection:
        """
        Return cells covering a shape at ``res``.

        Equivalent to h3 ``polygon_to_cells`` / ``h3shape_to_cells``. Accepts a
        shapely geometry, an object exposing ``__geo_interface__`` (e.g.
        ``h3.LatLngPoly``), or a GeoJSON-like mapping. Uses intersection
        (overlap) containment via the existing ``from_polygon`` machinery.
        """
        geometry = self._to_shapely(shape_like)
        return self.from_polygon(geometry, precision=res)

    # h3 alias
    geo_to_cells = polygon_to_cells

    def cells_to_geo(self, cells: Iterable[CellArg]) -> dict[str, Any]:
        """
        Return the outline of a set of cells as a GeoJSON-like mapping.

        Matches h3 ``cells_to_geo``.
        """
        polygons = [self._resolve(c)[1].polygon for c in cells]
        if not polygons:
            return {"type": "GeometryCollection", "geometries": []}
        return dict(mapping(unary_union(polygons)))

    @staticmethod
    def _to_shapely(shape_like: Any) -> BaseGeometry:
        if hasattr(shape_like, "exterior") or hasattr(shape_like, "geoms"):
            return shape_like  # already a shapely geometry
        if hasattr(shape_like, "__geo_interface__"):
            return shape(shape_like.__geo_interface__)
        if isinstance(shape_like, dict):
            return shape(shape_like)
        raise TypeError(f"Unsupported shape type: {type(shape_like)}")

    # ==================================================================
    # Tier 4 — H3-only verbs (delegate to the h3 library)
    # ==================================================================

    def is_pentagon(self, cell: CellArg) -> bool:
        """Whether the cell is a pentagon (H3 only)."""
        self._require_h3("is_pentagon")
        import h3

        return bool(h3.is_pentagon(self._id(cell)))

    def is_res_class_III(self, cell: CellArg) -> bool:
        """Whether the cell has Class III orientation (H3 only)."""
        self._require_h3("is_res_class_III")
        import h3

        return bool(h3.is_res_class_III(self._id(cell)))

    def get_base_cell_number(self, cell: CellArg) -> int:
        """Return the base (res-0) cell number (H3 only)."""
        self._require_h3("get_base_cell_number")
        import h3

        return int(h3.get_base_cell_number(self._id(cell)))

    def get_icosahedron_faces(self, cell: CellArg) -> List[int]:
        """Icosahedron face indices the cell intersects (H3 only)."""
        self._require_h3("get_icosahedron_faces")
        import h3

        return list(h3.get_icosahedron_faces(self._id(cell)))

    def get_num_cells(self, res: int) -> int:
        """Total number of cells at a resolution (H3 only)."""
        self._require_h3("get_num_cells")
        import h3

        return int(h3.get_num_cells(res))

    def get_res0_cells(self) -> GridCellCollection:
        """All base (resolution-0) cells (H3 only)."""
        self._require_h3("get_res0_cells")
        import h3

        grid = self._get_grid(0)
        return self._collection(
            [grid.get_cell_from_identifier(i) for i in h3.get_res0_cells()]
        )

    def get_pentagons(self, res: int) -> GridCellCollection:
        """Return the 12 pentagon cells at a resolution (H3 only)."""
        self._require_h3("get_pentagons")
        import h3

        grid = self._get_grid(res)
        return self._collection(
            [grid.get_cell_from_identifier(i) for i in h3.get_pentagons(res)]
        )

    def str_to_int(self, cell: CellArg) -> int:
        """Hex-string id -> 64-bit integer (H3 only)."""
        self._require_h3("str_to_int")
        import h3

        return int(h3.str_to_int(self._id(cell)))

    def int_to_str(self, value: int) -> str:
        """64-bit integer -> hex-string id (H3 only)."""
        self._require_h3("int_to_str")
        import h3

        return str(h3.int_to_str(value))

    # Directed edges (H3 only)

    def cells_to_directed_edge(self, origin: CellArg, destination: CellArg) -> str:
        """Directed edge id from two neighboring cells (H3 only)."""
        self._require_h3("cells_to_directed_edge")
        import h3

        return str(h3.cells_to_directed_edge(self._id(origin), self._id(destination)))

    def origin_to_directed_edges(self, cell: CellArg) -> List[str]:
        """All directed edges leaving a cell (H3 only)."""
        self._require_h3("origin_to_directed_edges")
        import h3

        return list(h3.origin_to_directed_edges(self._id(cell)))

    def directed_edge_to_cells(self, edge: str) -> Tuple[str, str]:
        """Both endpoint cell ids of an edge (H3 only)."""
        self._require_h3("directed_edge_to_cells")
        import h3

        origin, destination = h3.directed_edge_to_cells(edge)
        return (str(origin), str(destination))

    def edge_length(self, edge: str, unit: str = "km") -> float:
        """Length of a directed edge in ``unit`` (H3 only)."""
        self._require_h3("edge_length")
        import h3

        return float(h3.edge_length(edge, unit=unit))

    # Vertexes (H3 only)

    def cell_to_vertexes(self, cell: CellArg) -> List[str]:
        """All vertex ids of a cell (H3 only)."""
        self._require_h3("cell_to_vertexes")
        import h3

        return list(h3.cell_to_vertexes(self._id(cell)))

    def vertex_to_latlng(self, vertex: str) -> Tuple[float, float]:
        """Coordinates ``(lat, lng)`` of a vertex (H3 only)."""
        self._require_h3("vertex_to_latlng")
        import h3

        lat, lng = h3.vertex_to_latlng(vertex)
        return (float(lat), float(lng))

    # Measurements at resolution (H3 only)

    def average_hexagon_area(self, res: int, unit: str = "km^2") -> float:
        """Mean hexagon area at a resolution (H3 only)."""
        self._require_h3("average_hexagon_area")
        import h3

        return float(h3.average_hexagon_area(res, unit=unit))

    def average_hexagon_edge_length(self, res: int, unit: str = "km") -> float:
        """Mean hexagon edge length at a resolution (H3 only)."""
        self._require_h3("average_hexagon_edge_length")
        import h3

        return float(h3.average_hexagon_edge_length(res, unit=unit))
