"""
A5 pentagonal grid implementation for M3S.

A5 is a global Discrete Global Grid System (DGGS) that tiles the Earth with
equilateral pentagons arranged on a dodecahedron. Unlike H3 (hexagons), S2
(squares) or HTM (triangles), A5 uses pentagons, which let every cell nest
exactly into its parent (aperture-4 above resolution 1) on a true equal-area
projection that accounts for the ellipsoidal shape of the Earth. See
https://a5geo.org/.

This module is a thin adapter over the official ``pya5`` library
(``felixpalmer/a5-py``, imported as :mod:`a5`); all of the dodecahedral
geometry, Hilbert-curve indexing and equal-area projection live there. M3S only
maps ``pya5`` onto the :class:`~m3s.base.BaseGrid` interface.

.. note::
    Cell identifiers are the ``pya5`` 64-bit cell id rendered as a 16-character
    hexadecimal string (e.g. ``"63c20e0000000000"``). The resolution is encoded
    in the id itself, so identifiers round-trip without any extra state and a
    cell's :attr:`~m3s.base.GridCell.precision` is read straight from the id.

.. note::
    Coverage is global. ``pya5`` uses GIS-native ``(lon, lat)`` order; this
    wrapper exposes the M3S ``(lat, lon)`` order on
    :meth:`A5Grid.get_cell_from_point` and swaps at the boundary. Pentagons that
    cross the antimeridian yield a raw lon/lat polygon spanning >180 deg (the
    same caveat the other global M3S grids carry).
"""

from typing import override

import a5
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell

# Resolution range exposed by M3S. pya5 supports 0..MAX_RESOLUTION (30); its
# special WORLD_CELL (resolution -1) is not exposed.
MIN_PRECISION = 0
MAX_PRECISION = a5.MAX_RESOLUTION


class A5Grid(BaseGrid):
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
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"A5 precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )
        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Theoretical area of a cell at this precision in km^2.

        A5 is equal-area, so every cell at a given resolution has the same
        ground area. The value comes straight from ``pya5`` (authalic,
        ellipsoid-aware) in m^2 and is converted to km^2.

        Returns
        -------
        float
            Cell area in square kilometres.
        """
        return float(a5.cell_area(self.precision)) / 1e6

    def _make_cell(self, cell_id: int) -> GridCell:
        """Build a :class:`GridCell` from a ``pya5`` integer cell id."""
        boundary = a5.cell_to_boundary(cell_id)  # closed (lon, lat) ring
        polygon = Polygon(boundary)
        identifier = a5.u64_to_hex(cell_id)
        precision = a5.get_resolution(cell_id)
        return GridCell(identifier, polygon, precision)

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
        if not -90 <= lat <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= lon <= 180:
            raise ValueError("Longitude must be between -180 and 180")

        cell_id = a5.lonlat_to_cell((lon, lat), self.precision)
        return self._make_cell(cell_id)

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
            cell_id = a5.hex_to_u64(identifier)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid A5 identifier: {identifier}") from exc
        return self._make_cell(cell_id)

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get the edge-sharing neighbours of a cell.

        Uses ``pya5``'s ``grid_disk`` (k=1), which returns the centre cell plus
        its edge neighbours; the centre is removed. Pentagons have 5 edge
        neighbours away from face boundaries.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbours.

        Returns
        -------
        list[GridCell]
            Neighbouring cells of the same precision, excluding ``cell`` itself.
        """
        cell_id = a5.hex_to_u64(cell.identifier)
        return [
            self._make_cell(neighbor_id)
            for neighbor_id in a5.grid_disk(cell_id, 1)
            if neighbor_id != cell_id
        ]

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Get the A5 cells covering the given bounding box.

        Parameters
        ----------
        min_lat, min_lon, max_lat, max_lon : float
            Bounding box in WGS84 degrees.

        Returns
        -------
        list[GridCell]
            Cells at this grid's precision covering the box.

        Notes
        -----
        Built on ``pya5``'s ``polygon_to_cells`` (centre-in-polygon
        containment), expanded to this precision with ``uncompact``. The cells
        covering the four corners and the centre of the box are always included,
        so a box smaller than a single cell still returns its covering cell(s).
        """
        ring = [
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
        ]
        compacted = a5.polygon_to_cells(ring, self.precision)
        ids = set(a5.uncompact(compacted, self.precision))

        # polygon_to_cells uses centre containment, so it can miss a cell that
        # covers a box smaller than itself; sample the corners + centre too.
        mid_lon = (min_lon + max_lon) / 2
        mid_lat = (min_lat + max_lat) / 2
        for lon, lat in (*((x, y) for x, y in ring), (mid_lon, mid_lat)):
            ids.add(a5.lonlat_to_cell((lon, lat), self.precision))

        return [self._make_cell(cell_id) for cell_id in ids]

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
        cell_id = a5.hex_to_u64(cell.identifier)
        if a5.get_resolution(cell_id) <= 0:
            raise ValueError("Cell has no parent (already at resolution 0)")
        return self._make_cell(a5.cell_to_parent(cell_id))

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
        cell_id = a5.hex_to_u64(cell.identifier)
        if a5.get_resolution(cell_id) >= self.MAX_PRECISION:
            return []
        return [self._make_cell(child_id) for child_id in a5.cell_to_children(cell_id)]

    @override
    def identifier_to_precision(self, identifier: str) -> int | None:
        """Native precision encoded in the identifier, or None if invalid."""
        try:
            return int(a5.get_resolution(a5.hex_to_u64(identifier)))
        except (ValueError, TypeError):
            return None
