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

.. note::
    The identifier format (``"<size>kmE<easting>N<northing>"``) is provisional
    and isolated in :func:`_format_id` / :func:`_parse_id`; it can be changed
    later without touching the rest of the API.
"""

import math
import re
from functools import lru_cache
from typing import override

import pyproj
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell

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
_VALID_SIZES_KM = {2**k for k in range(MAX_PRECISION + 1)}  # {1, 2, ..., 1024}

# Guard against accidental memory blow-up in get_cells_in_bbox.
MAX_BBOX_CELLS = 1_000_000

_ID_RE = re.compile(r"^(\d+)kmE(\d+)N(\d+)$")


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
    Encode a cell as an identifier (PROVISIONAL format, easy to change later).

    The easting/northing are the kilometres of the cell's south-west corner
    measured from the projection's south-west origin, INSPIRE-style.
    """
    return f"{size_km}kmE{col * size_km}N{row * size_km}"


def _parse_id(identifier: str) -> tuple[int, int, int]:
    """
    Decode an identifier into ``(size_km, col, row)``.

    Raises
    ------
    ValueError
        If the identifier is malformed, the size is not a valid power-of-two
        km level, or the easting/northing are not aligned to the cell size.
    """
    match = _ID_RE.match(identifier)
    if match is None:
        raise ValueError(f"Invalid EA-Quad identifier: {identifier}")
    size_km = int(match.group(1))
    easting = int(match.group(2))
    northing = int(match.group(3))
    if size_km not in _VALID_SIZES_KM:
        raise ValueError(f"Invalid EA-Quad cell size: {size_km} km")
    if easting % size_km != 0 or northing % size_km != 0:
        raise ValueError(f"EA-Quad identifier not aligned to cell size: {identifier}")
    return size_km, easting // size_km, northing // size_km


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
        if not MIN_PRECISION <= precision <= MAX_PRECISION:
            raise ValueError(
                f"EA-Quad precision must be between {MIN_PRECISION} and "
                f"{MAX_PRECISION}"
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

        Returns
        -------
        float
            Theoretical area in square kilometres.
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

        size_km = self.size_km
        size_m = size_km * 1000
        fwd, _ = _get_transformers()
        x, y = fwd.transform(lon, lat)
        col = int(math.floor((x - X_MIN) / size_m))
        row = int(math.floor((y - Y_MIN) / size_m))
        # Clamp points on the eastern/northern domain edge into the last cell.
        col = min(max(col, 0), _ncols(size_km) - 1)
        row = min(max(row, 0), _nrows(size_km) - 1)
        return self._make_cell(size_km, col, row)

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get an EA-Quad cell from its identifier.

        Parameters
        ----------
        identifier : str
            Identifier of the form ``"<size>kmE<easting>N<northing>"``.

        Returns
        -------
        GridCell
            The corresponding grid cell.

        Raises
        ------
        ValueError
            If the identifier is invalid.
        """
        size_km, col, row = _parse_id(identifier)
        return self._make_cell(size_km, col, row)

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get up to 8 neighbouring cells (no wraparound at the domain edges).

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbours.

        Returns
        -------
        list[GridCell]
            Neighbouring cells of the same size that lie within the grid.
        """
        size_km, col, row = _parse_id(cell.identifier)
        ncols = _ncols(size_km)
        nrows = _nrows(size_km)
        neighbors = []
        for dcol in (-1, 0, 1):
            for drow in (-1, 0, 1):
                if dcol == 0 and drow == 0:
                    continue
                ncol = col + dcol
                nrow = row + drow
                if 0 <= ncol < ncols and 0 <= nrow < nrows:
                    neighbors.append(self._make_cell(size_km, ncol, nrow))
        return neighbors

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
        size_km = self.size_km
        size_m = size_km * 1000
        fwd, _ = _get_transformers()

        # Monotonic mapping: project the box edges to get the col/row span.
        x_lo, _ = fwd.transform(min_lon, 0.0)
        x_hi, _ = fwd.transform(max_lon, 0.0)
        _, y_lo = fwd.transform(0.0, min_lat)
        _, y_hi = fwd.transform(0.0, max_lat)

        col_lo = max(0, int(math.floor((min(x_lo, x_hi) - X_MIN) / size_m)))
        col_hi = min(
            _ncols(size_km) - 1, int(math.floor((max(x_lo, x_hi) - X_MIN) / size_m))
        )
        row_lo = max(0, int(math.floor((min(y_lo, y_hi) - Y_MIN) / size_m)))
        row_hi = min(
            _nrows(size_km) - 1, int(math.floor((max(y_lo, y_hi) - Y_MIN) / size_m))
        )

        if col_hi < col_lo or row_hi < row_lo:
            return []

        n_cells = (col_hi - col_lo + 1) * (row_hi - row_lo + 1)
        if n_cells > MAX_BBOX_CELLS:
            raise ValueError(
                f"Bounding box would yield {n_cells} cells (> {MAX_BBOX_CELLS}); "
                f"use a coarser precision"
            )

        bbox_polygon = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )

        cells = []
        for col in range(col_lo, col_hi + 1):
            for row in range(row_lo, row_hi + 1):
                try:
                    cell = self._make_cell(size_km, col, row)
                except ValueError:
                    continue
                if cell.polygon.intersects(bbox_polygon):
                    cells.append(cell)
        return cells

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
        size_km, col, row = _parse_id(cell.identifier)
        if size_km >= _precision_to_size_km(MIN_PRECISION):
            raise ValueError("Cell has no parent (already at coarsest 1024 km level)")
        return self._make_cell(size_km * 2, col // 2, row // 2)

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
        size_km, col, row = _parse_id(cell.identifier)
        if size_km <= _precision_to_size_km(MAX_PRECISION):
            return []
        child_size = size_km // 2
        return [
            self._make_cell(child_size, 2 * col + dcol, 2 * row + drow)
            for dcol in (0, 1)
            for drow in (0, 1)
        ]

    @override
    def identifier_to_precision(self, identifier: str) -> int | None:
        """Native precision encoded in the identifier, or None if invalid."""
        try:
            size_km, _, _ = _parse_id(identifier)
        except ValueError:
            return None
        return _size_km_to_precision(size_km)
