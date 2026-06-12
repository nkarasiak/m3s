"""
EA-Quad (Equal-Area Quadtree) grid implementation for M3S.

A global, square, quadtree (aperture-4) grid with exact hierarchical
containment and metre- to kilometre-sized cells, built on a single global
equal-area cylindrical projection (EPSG:6933, EASE-Grid 2.0 Global / Lambert
cylindrical equal-area). Unlike Geohash it uses true squares; unlike H3 every
cell nests exactly into its parent; unlike MGRS it is seamless worldwide;
unlike Quadkey/Slippy its cells are equal-area and sized in round powers of
two of a kilometre.

Cell edges are powers of two kilometres: 1024 km down to 1 km at precision
0-10, and sub-kilometre below that (precision 20 is ~0.98 m). Each cell
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
    Cell identifiers are S2-style hex tokens (e.g. ``"47ef4"``) of a 64-bit
    cell id: the cell's Hilbert-curve index over a square super-root that
    bounds the projection domain (2 bits per level, most significant first),
    followed by a sentinel ``1`` bit, zero-padded to 64 bits, hex-encoded with
    trailing ``'0'`` characters stripped. The precision is recovered from the
    sentinel bit, so tokens round-trip without extra state; coarser cells get
    shorter tokens, and an ancestor's id is a bit-prefix of its descendants'.
    The Hilbert ordering means tokens that are numerically close are spatially
    close (good range-query locality). The format is isolated in
    :func:`_format_id` / :func:`_parse_id`.
"""

import math
from typing import override

import m3s_core

from .base import (
    CoreBackedGrid,
    GridCell,
    cell_from_core,
    cells_from_core_packed,
    validate_lat_lon,
)

# EPSG:6933 (EASE-Grid 2.0 Global) valid projected domain, in metres.
# Full mathematical domain: lon +/-180 -> x +/-X_MAX, lat +/-90 -> y +/-Y_MAX.
X_MAX = 17367530.445161372
Y_MAX = 7342230.13649868
X_MIN = -X_MAX
Y_MIN = -Y_MAX
WIDTH = X_MAX - X_MIN
HEIGHT = Y_MAX - Y_MIN

# Precision range: precision p -> cell edge = 2 ** (10 - p) km.
# p=0 -> 1024 km (coarsest), p=10 -> 1 km, p=20 -> ~0.98 m (finest).
MIN_PRECISION = 0
MAX_PRECISION = 20

# Quadtree super-root: 65536 km (2 ** 16), SW-aligned at (X_MIN, Y_MIN). A
# cell's level is its depth below the super-root; precision = level - 6.
SUPER_ROOT_KM = 65536
_SUPER_ROOT_M = float(SUPER_ROOT_KM * 1000)
_MIN_LEVEL = MIN_PRECISION + 6  # 6  (precision 0, 1024 km)
_MAX_LEVEL = MAX_PRECISION + 6  # 26 (precision 20, ~0.98 m)

# Mean Earth radius (km) used for the 'rads^2' area unit, matching the core's
# geodesic area constant.
_EARTH_RADIUS_KM = 6371.0088

_HEX_DIGITS = set("0123456789abcdef")


def _precision_to_size_km(precision: int) -> float:
    """Cell edge length in km for a precision level (2 ** (10 - precision))."""
    return 2.0 ** (10 - precision)


def _size_m(level: int) -> float:
    """Cell edge in metres at a level; exact in f64 (125 * 2^k every level)."""
    return _SUPER_ROOT_M / (1 << level)


def _ncols(level: int) -> int:
    """Return the column count spanning the projected width at this level."""
    return math.ceil(WIDTH / _size_m(level))


def _nrows(level: int) -> int:
    """Return the row count spanning the projected height at this level."""
    return math.ceil(HEIGHT / _size_m(level))


def _xy2d(level: int, x: int, y: int) -> int:
    """
    Hilbert index of ``(x, y)`` on the ``2**level x 2**level`` lattice.

    SW origin (x east, y north). The curve is hierarchical: a parent's index is
    its child's index shifted right by two bits, which makes a token's bit
    prefix its ancestor (the S2 property).
    """
    d = 0
    s = 1 << (level - 1)
    while s > 0:
        rx = 1 if x & s else 0
        ry = 1 if y & s else 0
        d += s * s * ((3 * rx) ^ ry)
        x &= s - 1
        y &= s - 1
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        s >>= 1
    return d


def _d2xy(level: int, d: int) -> tuple[int, int]:
    """Inverse of :func:`_xy2d`: Hilbert index -> ``(x, y)``."""
    x = y = 0
    s = 1
    while s < (1 << level):
        rx = 1 & (d // 2)
        ry = 1 & (d ^ rx)
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        d //= 4
        s <<= 1
    return x, y


def _format_id(level: int, col: int, row: int) -> str:
    """Encode a cell as an S2-style hex token (trailing zeros stripped)."""
    d = _xy2d(level, col, row)
    cell_id = (d << (64 - 2 * level)) | (1 << (63 - 2 * level))
    return f"{cell_id:016x}".rstrip("0")


def _parse_id(identifier: str) -> tuple[int, int, int]:
    """
    Decode a hex token into ``(level, col, row)``.

    Raises
    ------
    ValueError
        If the token is not 1-16 lowercase hex characters, its sentinel bit
        does not encode a level between 6 and 26 inclusive, or the cell lies
        fully outside the projection domain.
    """
    if (
        not 1 <= len(identifier) <= 16
        or not set(identifier) <= _HEX_DIGITS
        or int(identifier, 16) == 0
    ):
        raise ValueError(f"Invalid EA-Quad identifier: {identifier}")
    cell_id = int(identifier, 16) << (4 * (16 - len(identifier)))
    trailing = (cell_id & -cell_id).bit_length() - 1
    if (63 - trailing) % 2 != 0:
        raise ValueError(f"Invalid EA-Quad identifier: {identifier}")
    level = (63 - trailing) // 2
    if not _MIN_LEVEL <= level <= _MAX_LEVEL:
        raise ValueError(f"Invalid EA-Quad identifier: {identifier}")
    col, row = _d2xy(level, cell_id >> (64 - 2 * level))
    if col >= _ncols(level) or row >= _nrows(level):
        raise ValueError(f"EA-Quad cell outside projection domain: {identifier}")
    return level, col, row


class EAQuadGrid(CoreBackedGrid):
    """
    EA-Quad (Equal-Area Quadtree) grid system.

    Global square quadtree grid on an equal-area projection (EPSG:6933) with
    power-of-two cell edges and exact hierarchical containment.

    Attributes
    ----------
    precision : int
        Precision level (0-20). Higher precision means smaller cells.
        ``size_km == 2 ** (10 - precision)`` so precision 0 = 1024 km,
        precision 10 = 1 km and precision 20 ~ 0.98 m.
    """

    KEY = "eaq"
    GRID_NAME = "EA-Quad"
    # Mirror the module-level bounds as the BaseGrid metadata attributes so
    # consumers (GridWrapper, AreaCalculator, ...) see EA-Quad's true 0-20 range.
    MIN_PRECISION = MIN_PRECISION
    MAX_PRECISION = MAX_PRECISION
    DEFAULT_PRECISION = 4

    def __init__(self, precision: int = 4):
        """
        Initialize EAQuadGrid.

        Parameters
        ----------
        precision : int, optional
            Precision level (0-20), by default 4 (64 km cells).

            ===========  =========
            precision    cell edge
            ===========  =========
            0            1024 km
            4            64 km
            10           1 km
            14           62.5 m
            20           ~0.98 m
            ===========  =========

        Raises
        ------
        ValueError
            If precision is not between 0 and 20.
        """
        super().__init__(precision)

    @property
    def size_km(self) -> float:
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
        ``size_km ** 2``; use :meth:`native_cell_area` for the exact (clipped)
        area of an individual cell.

        Returns
        -------
        float
            Theoretical (nominal) area in square kilometres.
        """
        return float(self.size_km**2)

    @override
    def native_cell_area(self, identifier: str, unit: str) -> float | None:
        """
        Exact ground area of a cell, accounting for domain clipping.

        The projection is equal-area, so a cell's true ground area equals its
        projected rectangle's area after clipping to the EPSG:6933 domain --
        analytic, with no polygon involved. Interior cells report the nominal
        ``size_km ** 2``; the easternmost/northernmost (and polar) cells report
        their physically smaller clipped area.

        Parameters
        ----------
        identifier : str
            Cell identifier (hex token).
        unit : str
            Area unit: ``'km^2'``, ``'m^2'`` or ``'rads^2'``.

        Returns
        -------
        float | None
            Exact area in ``unit``, or None for an unknown unit.

        Raises
        ------
        ValueError
            If the identifier is invalid.
        """
        level, col, row = _parse_id(identifier)
        size_m = _size_m(level)
        width_m = min(X_MAX, X_MIN + (col + 1) * size_m) - (X_MIN + col * size_m)
        height_m = min(Y_MAX, Y_MIN + (row + 1) * size_m) - (Y_MIN + row * size_m)
        area_km2 = width_m * height_m / 1e6
        if unit == "km^2":
            return area_km2
        if unit == "m^2":
            return area_km2 * 1e6
        if unit == "rads^2":
            return area_km2 / _EARTH_RADIUS_KM**2
        return None

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
        level, _, _ = _parse_id(cell.identifier)
        if level <= _MIN_LEVEL:
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
            (~0.98 m).
        """
        level, _, _ = _parse_id(cell.identifier)
        if level >= _MAX_LEVEL:
            return []
        return cells_from_core_packed(m3s_core.eaq_children(cell.identifier))

    @override
    def identifier_to_precision(self, identifier: str) -> int | None:
        """Native precision encoded in the identifier, or None if invalid."""
        try:
            level, _, _ = _parse_id(identifier)
        except ValueError:
            return None
        return level - 6
