"""
Plus codes (Open Location Code) grid implementation.
"""

from functools import cached_property
from typing import override

import m3s_core

from .base import BaseGrid, GridCell, cell_from_core


class PlusCodeGrid(BaseGrid):
    """
    Plus codes (Open Location Code) spatial grid system.

    Implements Google's open-source alternative to addresses using
    a base-20 encoding system to create hierarchical grid cells.
    """

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
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"Plus code precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )
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
        # Normalize latitude and longitude
        lat = max(-90, min(90, lat))
        lon = ((lon + 180) % 360) - 180

        # Shift to positive range
        lat_range = lat + 90
        lon_range = lon + 180

        code = ""
        lat_precision = 20.0
        lon_precision = 20.0

        for i in range(self.precision):
            lat_digit = int(lat_range / lat_precision)
            lon_digit = int(lon_range / lon_precision)

            # Ensure digits are within bounds
            lat_digit = min(lat_digit, self.BASE - 1)
            lon_digit = min(lon_digit, self.BASE - 1)

            code += self.ALPHABET[lon_digit] + self.ALPHABET[lat_digit]

            # Remove the encoded portion
            lat_range -= lat_digit * lat_precision
            lon_range -= lon_digit * lon_precision

            # Increase precision for next iteration
            lat_precision /= self.BASE
            lon_precision /= self.BASE

            # Add separator after 4th character (standard plus code format)
            if i == 1:
                code += "+"

        return code

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
        # Remove separator and normalize
        code = code.replace("+", "").upper()

        lat_range = 0.0
        lon_range = 0.0
        lat_precision = 20.0
        lon_precision = 20.0

        pairs_decoded = 0

        # Decode pairs of characters
        for i in range(0, min(len(code), self.precision * 2), 2):
            if i + 1 >= len(code):
                break

            lon_char = code[i]
            lat_char = code[i + 1]

            if lat_char in self.ALPHABET and lon_char in self.ALPHABET:
                lat_digit = self.ALPHABET.index(lat_char)
                lon_digit = self.ALPHABET.index(lon_char)

                lat_range += lat_digit * lat_precision
                lon_range += lon_digit * lon_precision

                lat_precision /= self.BASE
                lon_precision /= self.BASE
                pairs_decoded += 1

        # Determine cell size based on actual precision used
        if pairs_decoded > 0:
            # Cell size is the precision at the last level
            final_lat_precision = lat_precision * self.BASE
            final_lon_precision = lon_precision * self.BASE
        else:
            final_lat_precision = 20.0
            final_lon_precision = 20.0

        # Convert back to lat/lon coordinates
        south = lat_range - 90
        west = lon_range - 180
        north = south + final_lat_precision
        east = west + final_lon_precision

        return (south, west, north, east)

    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the grid cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        GridCell
            The grid cell containing the specified point
        """
        return cell_from_core(m3s_core.pc_cell_from_point(lat, lon, self.precision))

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its identifier.

        Parameters
        ----------
        identifier : str
            The plus code identifier

        Returns
        -------
        GridCell
            The grid cell corresponding to the identifier

        Raises
        ------
        ValueError
            If the identifier contains characters outside the Plus Code
            alphabet or is too short to encode a cell.
        """
        return cell_from_core(m3s_core.pc_cell_from_id(identifier))

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring cells of the given cell.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring grid cells
        """
        return [cell_from_core(n) for n in m3s_core.pc_neighbors(cell.identifier)]

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
        return [cell_from_core(c) for c in m3s_core.pc_children(cell.identifier)]

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

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Get all grid cells within the given bounding box.

        Parameters
        ----------
        min_lat : float
            Minimum latitude of bounding box
        min_lon : float
            Minimum longitude of bounding box
        max_lat : float
            Maximum latitude of bounding box
        max_lon : float
            Maximum longitude of bounding box

        Returns
        -------
        list[GridCell]
            List of grid cells that intersect the bounding box

        Notes
        -----
        Plus-code cells form a regular square lon/lat lattice, so this returns
        the exact, complete set of intersecting cells from the shared core
        (``m3s_core.pc_cells_in_bbox``). It replaces the former dense
        point-sampling, whose 5%-cell margin and epsilon-expanded boundaries
        could include a few cells just outside the box.
        """
        return [
            cell_from_core(c)
            for c in m3s_core.pc_cells_in_bbox(
                min_lat, min_lon, max_lat, max_lon, self.precision
            )
        ]
