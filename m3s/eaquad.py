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
from typing import override

import m3s_core

from .base import CoreBackedGrid, GridCell, cell_from_core, validate_lat_lon

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


class EAQuadGrid(CoreBackedGrid):
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

    KEY = "eaq"
    GRID_NAME = "EA-Quad"
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
        validate_lat_lon(lat, lon)
        return cell_from_core(m3s_core.eaq_cell_from_point(lat, lon, self.precision))

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
