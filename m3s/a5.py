"""
A5 pentagonal grid implementation for M3S.

A5 is a global Discrete Global Grid System (DGGS) that tiles the Earth with
equilateral pentagons arranged on a dodecahedron. Unlike H3 (hexagons), S2
(squares) or HTM (triangles), A5 uses pentagons, which let every cell nest
exactly into its parent (aperture-4 above resolution 1) on a true equal-area
projection that accounts for the ellipsoidal shape of the Earth. See
https://a5geo.org/.

This module is a thin adapter over the shared ``m3s_core`` A5 grid (the Rust
``a5`` crate, ``felixpalmer/a5-rs`` — the same source ``pya5`` binds); all of the
dodecahedral geometry, Hilbert-curve indexing and equal-area projection live
there. M3S only maps it onto the :class:`~m3s.base.BaseGrid` interface.

.. note::
    Cell identifiers are the A5 64-bit cell id rendered as a 16-character
    hexadecimal string (e.g. ``"63c20e0000000000"``). The resolution is encoded
    in the id itself, so identifiers round-trip without any extra state and a
    cell's :attr:`~m3s.base.GridCell.precision` is read straight from the id.

.. note::
    Coverage is global. The core uses GIS-native ``(lon, lat)`` order; this
    wrapper exposes the M3S ``(lat, lon)`` order on
    :meth:`A5Grid.get_cell_from_point` and swaps at the boundary. Pentagons that
    cross the antimeridian yield a raw lon/lat polygon spanning >180 deg (the
    same caveat the other global M3S grids carry).
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

# Resolution range exposed by M3S. A5 supports 0..30 (the spec's MAX_RESOLUTION);
# its special WORLD_CELL (resolution -1) is not exposed.
MIN_PRECISION = 0
MAX_PRECISION = 30


class A5Grid(CoreBackedGrid):
    """
    A5 pentagonal grid system.

    Global, equal-area pentagonal DGGS backed by the ``pya5`` library, with
    exact hierarchical containment (aperture-4 above resolution 1).

    Attributes
    ----------
    precision : int
        Resolution level (0-30). Higher precision means smaller cells:
        resolution 0 has 12 cells (one per dodecahedron face), resolution 30
        cells are smaller than 30 mm^2.
    """

    KEY = "a5"
    GRID_NAME = "A5"
    MIN_PRECISION = MIN_PRECISION
    MAX_PRECISION = MAX_PRECISION
    DEFAULT_PRECISION = 8

    def __init__(self, precision: int = 8):
        """
        Initialize A5Grid.

        Parameters
        ----------
        precision : int, optional
            Resolution level (0-30), by default 8 (~520 km^2 cells).

        Raises
        ------
        ValueError
            If precision is not between 0 and 30.
        """
        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Theoretical area of a cell at this precision in km^2.

        A5 is equal-area, so every cell at a given resolution has the same
        ground area. The value comes straight from the shared core's authalic,
        ellipsoid-aware ``a5_cell_area_m2`` (the same a5 crate ``pya5`` wraps),
        in m^2, converted to km^2.

        Returns
        -------
        float
            Cell area in square kilometres.
        """
        return float(m3s_core.a5_cell_area_m2(self.precision)) / 1e6

    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the A5 cell containing the given point.

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
        return cell_from_core(m3s_core.a5_cell_from_point(lat, lon, self.precision))

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get an A5 cell from its identifier.

        Parameters
        ----------
        identifier : str
            Hexadecimal cell id (e.g. ``"63c20e0000000000"``).

        Returns
        -------
        GridCell
            The corresponding grid cell.

        Raises
        ------
        ValueError
            If the identifier is not a valid A5 hexadecimal cell id.
        """
        try:
            return cell_from_core(m3s_core.a5_cell_from_id(identifier))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid A5 identifier: {identifier}") from exc

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get the parent cell (one resolution coarser).

        Parameters
        ----------
        cell : GridCell
            Child cell.

        Returns
        -------
        GridCell
            The parent cell that contains ``cell``.

        Raises
        ------
        ValueError
            If the cell is already at resolution 0 (no parent).
        """
        if cell.precision <= 0:
            raise ValueError("Cell has no parent (already at resolution 0)")
        return cell_from_core(m3s_core.a5_parent(cell.identifier))

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get the child cells (one resolution finer) that tile this cell.

        Parameters
        ----------
        cell : GridCell
            Parent cell.

        Returns
        -------
        list[GridCell]
            The children (5 below resolution 1, 4 above), or an empty list if
            already at the finest resolution (30).
        """
        if cell.precision >= self.MAX_PRECISION:
            return []
        return cells_from_core_packed(m3s_core.a5_children(cell.identifier))

    @override
    def identifier_to_precision(self, identifier: str) -> int | None:
        """Native precision encoded in the identifier, or None if invalid."""
        try:
            return int(m3s_core.a5_cell_from_id(identifier)[2])
        except (ValueError, TypeError):
            return None
