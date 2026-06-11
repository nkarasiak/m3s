"""
Plus codes (Open Location Code) grid implementation.
"""

from functools import cached_property

import m3s_core

from .base import (
    CoreBackedGrid,
    GridCell,
    cell_from_core,
    cells_from_core_packed,
)


class PlusCodeGrid(CoreBackedGrid):
    """
    Plus codes (Open Location Code) spatial grid system.

    Implements Google's open-source alternative to addresses using
    a base-20 encoding system to create hierarchical grid cells.
    """

    KEY = "pc"
    GRID_NAME = "Plus code"
    MIN_PRECISION = 1
    MAX_PRECISION = 7
    DEFAULT_PRECISION = 5

    # Base-20 alphabet excluding vowels and some confusing characters
    ALPHABET = "23456789CFGHJMPQRVWX"
    BASE = len(ALPHABET)

    # Grid sizes for different precision levels
    GRID_SIZES = [
        20.0,  # 0: ~2000km
        1.0,  # 1: ~100km
        0.05,  # 2: ~5km
        0.0025,  # 3: ~250m
        0.000125,  # 4: ~12.5m
        0.00000625,  # 5: ~62cm
        0.0000003125,  # 6: ~3cm
        0.000000015625,  # 7: ~1.5mm
    ]

    def __init__(self, precision: int = 4):
        """
        Initialize PlusCodeGrid.

        Parameters
        ----------
        precision : int, optional
            Plus code precision level (1-7), by default 4.
            Higher values mean smaller cells.

        Raises
        ------
        ValueError
            If precision is not between 1 and 7
        """
        super().__init__(precision)

    @cached_property
    def area_km2(self) -> float:
        """
        Approximate area of a Plus Code cell at this precision in square kilometers.

        Returns
        -------
        float
            Approximate area in square kilometers
        """
        size_degrees = self.GRID_SIZES[self.precision - 1]
        size_km = size_degrees * 111.32
        return size_km * size_km

    def encode(self, lat: float, lon: float) -> str:
        """
        Encode a latitude/longitude into a plus code.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        str
            Plus code identifier
        """
        return self.get_cell_from_point(lat, lon).identifier

    def decode(self, code: str) -> tuple:
        """
        Decode a plus code into latitude/longitude bounds.

        Parameters
        ----------
        code : str
            Plus code identifier

        Returns
        -------
        tuple
            (south, west, north, east) bounds
        """
        min_lon, min_lat, max_lon, max_lat = self.get_cell_from_identifier(
            code
        ).polygon.bounds
        return (min_lat, min_lon, max_lat, max_lon)

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get the child cells one precision level finer.

        Plus Codes nest exactly: each level subdivides a cell into
        ``BASE x BASE`` (20 x 20 = 400) children that tile it. Children are
        produced by re-encoding each sub-cell centre at the finer precision,
        so identifiers are always canonical.

        Parameters
        ----------
        cell : GridCell
            Parent cell.

        Returns
        -------
        list[GridCell]
            The child cells, or an empty list if already at the finest
            precision.
        """
        if self.precision >= self.MAX_PRECISION:
            return []
        return cells_from_core_packed(m3s_core.pc_children(cell.identifier))

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get the parent cell one precision level coarser.

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
            If the cell is already at the coarsest precision.
        """
        if self.precision <= self.MIN_PRECISION:
            raise ValueError(
                "Cell has no parent (already at the coarsest plus code precision)"
            )
        return cell_from_core(m3s_core.pc_parent(cell.identifier))
