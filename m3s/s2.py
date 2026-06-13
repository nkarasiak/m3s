"""
S2 spatial grid implementation for M3S.

S2 is Google's spherical geometry library that provides hierarchical
decomposition of the sphere into cells. Each cell is uniquely identified
by a 64-bit S2CellId, with cells organized using the Hilbert curve for
optimal spatial locality.
"""

from typing import override

import m3s_core
from shapely.geometry import Polygon

from .base import (
    CoreBackedGrid,
    GridCell,
    cell_from_core,
    cells_from_core_packed,
)


class S2Grid(CoreBackedGrid):
    """
    S2 spatial grid implementation.

    Based on Google's S2 geometry library, this grid provides hierarchical
    decomposition of the sphere into cells. S2 uses a cube-to-sphere projection
    and the Hilbert curve to create a spatial index with excellent locality
    properties.

    Attributes
    ----------
    precision : int
        S2 cell precision (0-30), where higher values provide smaller cells
    """

    KEY = "s2"
    GRID_NAME = "S2"
    MIN_PRECISION = 0
    MAX_PRECISION = 30
    DEFAULT_PRECISION = 10

    def __init__(self, precision: int = 10):
        """
        Initialize S2 grid.

        Parameters
        ----------
        precision : int, optional
            S2 cell precision level (0-30), by default 10.
            Precision 0: ~85,000 km edge length
            Precision 10: ~1,300 km edge length
            Precision 20: ~20 m edge length
            Precision 30: ~1 cm edge length
        """
        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of S2 cells at this level in square kilometers.

        Returns
        -------
        float
            Theoretical area in square kilometers for cells at this level
        """
        # S2 cells are roughly equal area due to spherical geometry
        # Earth's surface area: ~510 million km²
        earth_surface_km2 = 510_072_000.0

        # S2 has 6 root cells (one per cube face)
        # At each level, cells are divided into 4 children
        # Total cells at level L = 6 × 4^L
        total_cells = 6 * (4**self.precision)

        # Average area per cell
        return float(earth_surface_km2 / total_cells)

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its S2 cell token.

        Parameters
        ----------
        identifier : str
            The S2 cell token (hexadecimal string)

        Returns
        -------
        GridCell
            The grid cell corresponding to the identifier
        """
        try:
            return cell_from_core(m3s_core.s2_cell_from_id(identifier))
        except Exception as e:
            raise ValueError(f"Invalid S2 cell token: {identifier}") from e

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get child cells at the next level.

        Parameters
        ----------
        cell : GridCell
            Parent cell

        Returns
        -------
        list[GridCell]
            List of 4 child cells
        """
        if self.precision >= self.MAX_PRECISION:
            return []  # No children at maximum level

        return cells_from_core_packed(m3s_core.s2_children(cell.identifier))

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get parent cell at the previous level.

        Parameters
        ----------
        cell : GridCell
            Child cell

        Returns
        -------
        GridCell
            Parent cell

        Raises
        ------
        ValueError
            If the cell is already at the coarsest level (0).
        """
        if self.precision <= self.MIN_PRECISION:
            raise ValueError("Cell has no parent (already at S2 level 0)")

        return cell_from_core(m3s_core.s2_parent(cell.identifier))

    def get_covering_cells(
        self, polygon: Polygon, max_cells: int = 100
    ) -> list[GridCell]:
        """
        Get S2 cells that cover the given polygon.

        Parameters
        ----------
        polygon : Polygon
            Shapely polygon to cover
        max_cells : int
            Maximum number of cells to return

        Returns
        -------
        list[GridCell]
            List of cells covering the polygon

        Notes
        -----
        Takes the level-``precision`` cells of the polygon's bounding box (from
        the shared core's ``s2_cells_in_bbox``) and keeps those that actually
        intersect the polygon, capped at ``max_cells``. This replaces the former
        ``s2sphere.RegionCoverer`` path; the result is the set of cells covering
        the polygon at this precision.
        """
        min_lon, min_lat, max_lon, max_lat = polygon.bounds
        cells = [
            cell
            for cell in self.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
            if cell.polygon.intersects(polygon)
        ]
        if max_cells > 0 and len(cells) > max_cells:
            return cells[:max_cells]
        return cells

    def __repr__(self) -> str:
        return f"S2Grid(precision={self.precision})"
