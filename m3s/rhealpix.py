"""
rHEALPix DGGS grid implementation for M3S.

rHEALPix is an equal-area Discrete Global Grid System built on the rHEALPix
map projection: the HEALPix equal-area projection of the WGS84 authalic
sphere with the two polar caps rearranged into squares. The planar layout is
six squares -- one north polar (``N``), four equatorial (``O P Q R``), one
south polar (``S``) -- each of which subdivides into 3x3 = 9 children that
exactly tile it (aperture 9). Every cell at a given resolution has the same
ground area, and unlike a cylindrical equal-area grid (EA-Quad) the cell
*shape* distortion stays bounded all the way to the poles.

This module is a thin adapter over the shared ``m3s_core`` rHEALPix grid,
which reproduces the ``(0, 0)``-configuration (north and south squares at
position 0, ``N_side = 3``) of the `rhealpixdggs
<https://github.com/manaakiwhenua/rhealpixdggs-py>`_ reference implementation;
cell identifiers are interchangeable with it.

.. note::
    Cell identifiers are rhealpixdggs SUIDs: a face letter ``N/O/P/Q/R/S``
    followed by one digit ``0-8`` per resolution, numbered row-major from the
    upper-left child (e.g. ``"Q3"``, ``"N44"``). The resolution is the number
    of digits, so identifiers round-trip without extra state and any prefix is
    an ancestor cell.

.. note::
    Cells containing a pole or crossing the antimeridian yield raw lon/lat
    polygons spanning a wide longitude range -- the same caveat the other
    global M3S grids (S2, A5) carry. Polar-cell edges are curved in lon/lat
    and returned densified (4 segments per edge).
"""

from typing import override

import m3s_core

from .base import (
    CoreBackedGrid,
    GridCell,
    cell_from_core,
    cells_from_core_packed,
    validate_lat_lon,
)

# Resolution range. Resolution 0 is the six faces (~85 M km^2 each); each
# resolution divides the area by 9, so resolution 15 cells are ~6 m^2.
MIN_PRECISION = 0
MAX_PRECISION = 15

# Mean Earth radius (km) used for the 'rads^2' area unit, matching the core's
# geodesic area constant.
_EARTH_RADIUS_KM = 6371.0088

_FACES = set("NOPQRS")
_DIGITS = set("012345678")


def _validate_id(identifier: str) -> None:
    """Raise ValueError unless ``identifier`` is a well-formed SUID."""
    if (
        not 1 <= len(identifier) <= MAX_PRECISION + 1
        or identifier[0] not in _FACES
        or not set(identifier[1:]) <= _DIGITS
    ):
        raise ValueError(f"Invalid rHEALPix identifier: {identifier}")


class RHEALPixGrid(CoreBackedGrid):
    """
    rHEALPix equal-area DGGS grid system.

    Global aperture-9 quadtree on the rHEALPix projection (WGS84 ellipsoid,
    ``N_side = 3``, polar squares at position 0) with exact hierarchical
    containment, equal-area cells and bounded shape distortion.

    Attributes
    ----------
    precision : int
        Resolution level (0-15). Higher precision means smaller cells:
        resolution 0 has 6 cells (one per face), and each resolution divides
        the cell area by 9.
    """

    KEY = "rhp"
    GRID_NAME = "rHEALPix"
    MIN_PRECISION = MIN_PRECISION
    MAX_PRECISION = MAX_PRECISION
    DEFAULT_PRECISION = 5

    def __init__(self, precision: int = 5):
        """
        Initialize RHEALPixGrid.

        Parameters
        ----------
        precision : int, optional
            Resolution level (0-15), by default 5 (~1440 km^2, ~38 km cells).

            ===========  ==============
            precision    cell area
            ===========  ==============
            0            ~85 M km^2
            3            ~116,600 km^2
            5            ~1,440 km^2
            10           ~0.024 km^2
            15           ~6.2 m^2
            ===========  ==============

        Raises
        ------
        ValueError
            If precision is not between 0 and 15.
        """
        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Exact area of a cell at this resolution in km^2.

        rHEALPix is equal-area, so every cell at a given resolution has the
        same ground area: ``(2*pi/3) * R_A^2 / 9 ** resolution`` with ``R_A``
        the WGS84 authalic radius (one sixth of the Earth's surface at
        resolution 0). Analytic; no polygon involved.

        Returns
        -------
        float
            Cell area in square kilometres.
        """
        return float(m3s_core.rhp_cell_area_km2(self.precision))

    @override
    def native_cell_area(self, identifier: str, unit: str) -> float | None:
        """
        Exact cell area in ``unit`` (equal-area: identical for every cell).

        Parameters
        ----------
        identifier : str
            Cell identifier (SUID).
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
        _validate_id(identifier)
        area_km2 = float(m3s_core.rhp_cell_area_km2(len(identifier) - 1))
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
        Get the rHEALPix cell containing the given point.

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
        return cell_from_core(m3s_core.rhp_cell_from_point(lat, lon, self.precision))

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get the parent cell (one resolution coarser; drop the last digit).

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
            If the cell is already a resolution 0 face.
        """
        _validate_id(cell.identifier)
        if len(cell.identifier) == 1:
            raise ValueError("Cell has no parent (already a resolution 0 face)")
        return cell_from_core(m3s_core.rhp_parent(cell.identifier))

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get the 9 child cells (one resolution finer) that exactly tile this cell.

        Parameters
        ----------
        cell : GridCell
            Parent cell.

        Returns
        -------
        list[GridCell]
            The 9 children, or an empty list if already at the finest
            resolution (15).
        """
        _validate_id(cell.identifier)
        if len(cell.identifier) - 1 >= MAX_PRECISION:
            return []
        return cells_from_core_packed(m3s_core.rhp_children(cell.identifier))

    @override
    def identifier_to_precision(self, identifier: str) -> int | None:
        """Native resolution encoded in the identifier, or None if invalid."""
        try:
            _validate_id(identifier)
        except ValueError:
            return None
        return len(identifier) - 1
