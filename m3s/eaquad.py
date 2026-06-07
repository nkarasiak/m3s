"""
EA-Quad (Equal-Area Quadtree) grid implementation for M3S.

A global, square, quadtree (aperture-4) grid with exact hierarchical
containment and kilometre-sized cells, built on a single global equal-area
cylindrical projection (EPSG:6933, EASE-Grid 2.0 Global / Lambert cylindrical
equal-area). Unlike Geohash it uses true squares; unlike H3 every cell nests
exactly into its parent; unlike MGRS it is seamless worldwide; unlike
Quadkey/Slippy its cells are equal-area and labelled in kilometres.

Cell sizes are powers of two kilometres (1, 2, 4, ... 1024 km). Each cell
subdivides into 2x2 = 4 children that perfectly tile it. Because the
projection is equal-area, a cell of a given size has the same ground area
everywhere on Earth.

Coverage is global to latitude +/-90. The equal-area cylindrical projection
(EPSG:6933) maps each pole to a finite line, so the top and bottom rows reach
the poles (very thin in latitude, full in area) -- there are no excluded polar
caps and the grid spans the entire Earth's surface area. For neighbour queries
longitude wraps at the antimeridian (column 0 is adjacent to the last column at
lon +/-180) while latitude does not wrap (the poles are real edges).

.. note::
    EA-Quad uses the EASE-Grid 2.0 *projection* (EPSG:6933) only; it is **not**
    the NSIDC EASE-Grid product. Its power-of-two kilometre cells do **not**
    align with NSIDC EASE-Grid pixel definitions (e.g. the SMAP/SMOS/AMSR
    25/12.5/9/3 km grids). Treat it as a general-purpose equal-area quadtree,
    not as a drop-in for EASE-Grid datasets.

.. note::
    Cell identifiers are Geohash-style base-4 quadtree paths: a single string of
    digits ``0-3`` over a square super-root that bounds the projection domain
    (see :data:`SUPER_ROOT_KM`). Each digit selects a quadrant
    (``0=SW, 1=SE, 2=NW, 3=NE``); appending a digit descends one level, so any
    prefix is an ancestor cell and a cell's parent is its identifier with the
    last character removed. Every cell at a given precision has the same
    identifier length (``6 + precision`` characters). The format is isolated in
    :func:`_format_id` / :func:`_parse_id`.
"""

import math
import re
from functools import lru_cache
from typing import override

import m3s_core
import pyproj
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell, cell_from_core

# EPSG:6933 (EASE-Grid 2.0 Global) valid projected domain, in metres.
# Full mathematical domain: lon +/-180 -> x +/-X_MAX, lat +/-90 -> y +/-Y_MAX.
X_MAX = 17367530.445161372
Y_MAX = 7342230.13649868
X_MIN = -X_MAX
Y_MIN = -Y_MAX
WIDTH = X_MAX - X_MIN
HEIGHT = Y_MAX - Y_MIN

# Precision range: precision p -> cell edge = 2 ** (10 - p) km.
# p=0 -> 1024 km (coarsest), p=10 -> 1 km (finest).
MIN_PRECISION = 0
MAX_PRECISION = 10

# Guard against accidental memory blow-up in get_cells_in_bbox.
MAX_BBOX_CELLS = 1_000_000

# Geohash-style base-4 identifiers: a quadtree path over a square super-root that
# bounds the projection domain. The super-root edge is the smallest power-of-two
# km >= the domain's larger dimension (~34735 km wide), SW-aligned at
# (X_MIN, Y_MIN). An identifier's length equals its super-root level == 6 +
# precision, so size_km == SUPER_ROOT_KM >> level.
SUPER_ROOT_KM = 65536  # 2 ** 16 km; >= domain width (~34735 km)
_SUPER_ROOT_LEVEL = SUPER_ROOT_KM.bit_length() - 1  # 16
_MIN_LEVEL = _SUPER_ROOT_LEVEL - MAX_PRECISION  # 6  (precision 0, 1024 km)
_MAX_LEVEL = _SUPER_ROOT_LEVEL - MIN_PRECISION  # 16 (precision 10, 1 km)
_ID_RE = re.compile(r"^[0-3]+$")


@lru_cache(maxsize=1)
def _get_transformers() -> tuple[pyproj.Transformer, pyproj.Transformer]:
    """Return cached (forward, inverse) transformers for WGS84 <-> EPSG:6933."""
    fwd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
    inv = pyproj.Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)
    return fwd, inv


def _precision_to_size_km(precision: int) -> int:
    """Cell edge length in km for a precision level (2 ** (10 - precision))."""
    return int(2 ** (MAX_PRECISION - precision))


def _size_km_to_precision(size_km: int) -> int:
    """Inverse of :func:`_precision_to_size_km` for power-of-two km sizes."""
    return MAX_PRECISION - (size_km.bit_length() - 1)


def _ncols(size_km: int) -> int:
    """Return the column count spanning the projected width at this cell size."""
    return math.ceil(WIDTH / (size_km * 1000))


def _nrows(size_km: int) -> int:
    """Return the row count spanning the projected height at this cell size."""
    return math.ceil(HEIGHT / (size_km * 1000))


def _format_id(size_km: int, col: int, row: int) -> str:
    """
    Encode a cell as a Geohash-style base-4 quadtree path.

    The string has one digit per level from the super-root down to the cell;
    each digit ``0-3`` selects a quadrant (``0=SW, 1=SE, 2=NW, 3=NE``). ``col``
    and ``row`` are the cell's indices (in units of its own size) from the SW
    origin: their high bits give the coarse digits, so any prefix of the string
    is an ancestor cell.
    """
    level = _SUPER_ROOT_LEVEL - (size_km.bit_length() - 1)
    return "".join(
        str(2 * ((row >> i) & 1) + ((col >> i) & 1)) for i in range(level - 1, -1, -1)
    )


def _parse_id(identifier: str) -> tuple[int, int, int]:
    """
    Decode a base-4 quadtree path into ``(size_km, col, row)``.

    Raises
    ------
    ValueError
        If the identifier is not a base-4 string, or its length does not
        correspond to a valid precision level (6 to 16 characters inclusive).
    """
    if _ID_RE.match(identifier) is None:
        raise ValueError(f"Invalid EA-Quad identifier: {identifier}")
    level = len(identifier)
    if not _MIN_LEVEL <= level <= _MAX_LEVEL:
        raise ValueError(f"Invalid EA-Quad identifier length: {identifier}")
    size_km = SUPER_ROOT_KM >> level
    col = row = 0
    for ch in identifier:
        digit = int(ch)
        col = (col << 1) | (digit & 1)
        row = (row << 1) | ((digit >> 1) & 1)
    return size_km, col, row


class EAQuadGrid(BaseGrid):
    """
    EA-Quad (Equal-Area Quadtree) grid system.

    Global square quadtree grid on an equal-area projection (EPSG:6933) with
    power-of-two kilometre cells and exact hierarchical containment.

    Attributes
    ----------
    precision : int
        Precision level (0-10). Higher precision means smaller cells.
        ``size_km == 2 ** (10 - precision)`` so precision 0 = 1024 km and
        precision 10 = 1 km.
    """

    # Mirror the module-level bounds as the BaseGrid metadata attributes so
    # consumers (GridWrapper, AreaCalculator, ...) see EA-Quad's true 0-10 range.
    MIN_PRECISION = MIN_PRECISION
    MAX_PRECISION = MAX_PRECISION
    DEFAULT_PRECISION = 4

    def __init__(self, precision: int = 4):
        """
        Initialize EAQuadGrid.

        Parameters
        ----------
        precision : int, optional
            Precision level (0-10), by default 4 (64 km cells).

            ===========  =========
            precision    cell edge
            ===========  =========
            0            1024 km
            4            64 km
            10           1 km
            ===========  =========

        Raises
        ------
        ValueError
            If precision is not between 0 and 10.
        """
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"EA-Quad precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )
        super().__init__(precision)

    @property
    def size_km(self) -> int:
        """Cell edge length in kilometres at this grid's precision."""
        return _precision_to_size_km(self.precision)

    @property
    def area_km2(self) -> float:
        """
        Theoretical area of a cell at this precision in km^2.

        Equal-area projection: the area is analytic and constant worldwide,
        ``size_km ** 2``. No projection of the polygon is needed.

        This is the *nominal* cell area. The projection domain is not an integer
        multiple of every cell size, so the easternmost/northernmost (and polar)
        cells are clipped to the domain and are physically smaller than nominal.
        Like the other M3S grids, ``area_km2`` still reports the nominal
        ``size_km ** 2`` for those boundary cells.

        Returns
        -------
        float
            Theoretical (nominal) area in square kilometres.
        """
        return float(self.size_km**2)

    def _make_polygon(self, size_km: int, col: int, row: int) -> Polygon:
        """
        Build the WGS84 polygon for a cell, clamped to the projection domain.

        In a cylindrical equal-area projection constant-x lines are meridians
        and constant-y lines are parallels, so the projected square maps to an
        axis-aligned lon/lat rectangle: the four inverse-projected corners are
        exact (no edge densification needed).
        """
        size_m = size_km * 1000
        x0 = max(X_MIN + col * size_m, X_MIN)
        x1 = min(X_MIN + (col + 1) * size_m, X_MAX)
        y0 = max(Y_MIN + row * size_m, Y_MIN)
        y1 = min(Y_MIN + (row + 1) * size_m, Y_MAX)
        if x1 <= x0 or y1 <= y0:
            raise ValueError(
                f"EA-Quad cell outside projection domain: "
                f"{_format_id(size_km, col, row)}"
            )

        _, inv = _get_transformers()
        lon_w, lat_s = inv.transform(x0, y0)
        lon_e, lat_n = inv.transform(x1, y1)
        return Polygon(
            [
                (lon_w, lat_s),
                (lon_e, lat_s),
                (lon_e, lat_n),
                (lon_w, lat_n),
                (lon_w, lat_s),
            ]
        )

    def _make_cell(self, size_km: int, col: int, row: int) -> GridCell:
        """Construct a :class:`GridCell` from grid coordinates."""
        identifier = _format_id(size_km, col, row)
        polygon = self._make_polygon(size_km, col, row)
        precision = _size_km_to_precision(size_km)
        return GridCell(identifier, polygon, precision)

    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the EA-Quad cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate (-90 to 90).
        lon : float
            Longitude coordinate (-180 to 180).

        Returns
        -------
        GridCell
            The cell containing the point at this grid's precision.

        Raises
        ------
        ValueError
            If coordinates are out of valid range.
        """
        if not -90 <= lat <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= lon <= 180:
            raise ValueError("Longitude must be between -180 and 180")

        return cell_from_core(m3s_core.eaq_cell_from_point(lat, lon, self.precision))

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get an EA-Quad cell from its identifier.

        Parameters
        ----------
        identifier : str
            Base-4 quadtree path identifier (digits ``0-3``), e.g. ``"0122012"``.

        Returns
        -------
        GridCell
            The corresponding grid cell.

        Raises
        ------
        ValueError
            If the identifier is invalid.
        """
        return cell_from_core(m3s_core.eaq_cell_from_id(identifier))

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get up to 8 neighbouring cells.

        Longitude wraps at the antimeridian: the single seamless cylindrical
        projection makes column 0 and the last column physically adjacent at
        lon +/-180, so the east neighbour of an easternmost-column cell is the
        column-0 cell at the same row. Latitude does **not** wrap -- the poles
        are real edges, so cells in the top/bottom rows have fewer than 8
        neighbours.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbours.

        Returns
        -------
        list[GridCell]
            Up to 8 neighbouring cells of the same size; unique and excluding
            ``cell`` itself.
        """
        return [cell_from_core(n) for n in m3s_core.eaq_neighbors(cell.identifier)]

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Get all EA-Quad cells intersecting the given bounding box.

        Parameters
        ----------
        min_lat, min_lon, max_lat, max_lon : float
            Bounding box in WGS84 degrees.

        Returns
        -------
        list[GridCell]
            Cells at this grid's precision that intersect the bounding box.

        Raises
        ------
        ValueError
            If the requested box would yield more than ``MAX_BBOX_CELLS`` cells
            (use a coarser precision).
        """
        return [
            cell_from_core(c)
            for c in m3s_core.eaq_cells_in_bbox(
                min_lat, min_lon, max_lat, max_lon, self.precision
            )
        ]

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get the parent cell (one level coarser, double the edge length).

        Parameters
        ----------
        cell : GridCell
            Child cell.

        Returns
        -------
        GridCell
            The parent cell that exactly contains ``cell``.

        Raises
        ------
        ValueError
            If the cell is already at the coarsest level (1024 km).
        """
        size_km, _, _ = _parse_id(cell.identifier)
        if size_km >= _precision_to_size_km(MIN_PRECISION):
            raise ValueError("Cell has no parent (already at coarsest 1024 km level)")
        return cell_from_core(m3s_core.eaq_parent(cell.identifier))

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get the 4 child cells (one level finer) that exactly tile this cell.

        Parameters
        ----------
        cell : GridCell
            Parent cell.

        Returns
        -------
        list[GridCell]
            The 4 children, or an empty list if already at the finest level
            (1 km).
        """
        size_km, _, _ = _parse_id(cell.identifier)
        if size_km <= _precision_to_size_km(MAX_PRECISION):
            return []
        return [cell_from_core(c) for c in m3s_core.eaq_children(cell.identifier)]

    @override
    def identifier_to_precision(self, identifier: str) -> int | None:
        """Native precision encoded in the identifier, or None if invalid."""
        try:
            size_km, _, _ = _parse_id(identifier)
        except ValueError:
            return None
        return _size_km_to_precision(size_km)
