"""
C-squares (Concise Spatial Query and Representation System) grid implementation.
"""

from typing import override

import m3s_core

from .base import CoreBackedGrid, GridCell, cell_from_core


class CSquaresGrid(CoreBackedGrid):
    """
    C-squares-based spatial grid system.

    Implements the Concise Spatial Query and Representation System (C-squares)
    for marine and environmental data referencing using a hierarchical
    decimal grid system.
    """

    KEY = "cs"
    MIN_PRECISION = 1
    MAX_PRECISION = 5
    DEFAULT_PRECISION = 5

    def __init__(self, precision: int = 3):
        """
        Initialize CSquaresGrid.

        Parameters
        ----------
        precision : int, optional
            C-squares precision level (1-5), by default 3.

            Precision levels:
                1 = 10° x 10° cells (base level)
                2 = 5° x 5° cells
                3 = 1° x 1° cells
                4 = 0.5° x 0.5° cells (30' x 30')
                5 = 0.1° x 0.1° cells (6' x 6')

        Raises
        ------
        ValueError
            If precision is not between 1 and 5
        """
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"C-squares precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )
        super().__init__(precision)

    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the C-squares cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate (-90 to 90)
        lon : float
            Longitude coordinate (-180 to 180)

        Returns
        -------
        GridCell
            The C-squares grid cell containing the specified point

        Raises
        ------
        ValueError
            If coordinates are out of valid range
        """
        if not -90 <= lat <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= lon <= 180:
            raise ValueError("Longitude must be between -180 and 180")

        return cell_from_core(m3s_core.cs_cell_from_point(lat, lon, self.precision))

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a C-squares cell from its identifier.

        Parameters
        ----------
        identifier : str
            The C-squares identifier string

        Returns
        -------
        GridCell
            The C-squares grid cell with rectangular geometry

        Raises
        ------
        ValueError
            If the identifier is invalid
        """
        try:
            return cell_from_core(m3s_core.cs_cell_from_id(identifier))
        except Exception as e:
            raise ValueError(f"Invalid C-squares identifier: {identifier}") from e

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring C-squares cells.

        Parameters
        ----------
        cell : GridCell
            The C-squares cell for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring C-squares cells (up to 8 neighbors)
        """
        try:
            return [cell_from_core(n) for n in m3s_core.cs_neighbors(cell.identifier)]
        except Exception:
            # Return empty list if cell lookup fails
            return []

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get the child cells one precision level finer.

        C-squares nest exactly, but the aperture varies by level (10 deg -> 5
        deg is 2x2, 5 deg -> 1 deg is 5x5, etc.). Children are produced by
        re-encoding each finer-cell centre, so identifiers stay canonical and
        the per-level aperture is handled automatically.

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
        return [cell_from_core(c) for c in m3s_core.cs_children(cell.identifier)]

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
                "Cell has no parent (already at the coarsest C-squares precision)"
            )
        return cell_from_core(m3s_core.cs_parent(cell.identifier))

    def _encode_csquare(self, lat: float, lon: float, precision: int) -> str:
        """
        Encode latitude and longitude to C-squares identifier.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate
        precision : int
            Precision level

        Returns
        -------
        str
            C-squares identifier
        """
        return m3s_core.cs_cell_from_point(lat, lon, precision)[0]

    def _decode_csquare(self, identifier: str) -> tuple:
        """
        Decode C-squares identifier to bounding box coordinates.

        Parameters
        ----------
        identifier : str
            C-squares identifier

        Returns
        -------
        tuple
            (min_lat, min_lon, max_lat, max_lon)
        """
        min_lon, min_lat, max_lon, max_lat = self.get_cell_from_identifier(
            identifier
        ).polygon.bounds
        return min_lat, min_lon, max_lat, max_lon

    def _get_precision_from_identifier(self, identifier: str) -> int:
        """
        Determine precision level from identifier format.

        Parameters
        ----------
        identifier : str
            C-squares identifier

        Returns
        -------
        int
            Precision level
        """
        parts = identifier.split(":")
        return len(parts)

    def _get_cell_size(self, precision: int) -> float:
        """
        Get cell size in degrees for given precision.

        Parameters
        ----------
        precision : int
            Precision level

        Returns
        -------
        float
            Cell size in degrees
        """
        sizes = {1: 10.0, 2: 5.0, 3: 1.0, 4: 0.5, 5: 0.1}
        return sizes[precision]

    def get_precision_info(self) -> dict:
        """
        Get detailed information about the current precision level.

        Returns
        -------
        dict
            Dictionary containing precision metrics including cell size
            and coverage information
        """
        cell_size = self._get_cell_size(self.precision)
        return {
            "precision": self.precision,
            "cell_size_degrees": cell_size,
            "cell_size_km": cell_size * 111.32,  # Approximate conversion
            "total_global_cells": int(180 / cell_size) * int(360 / cell_size),
            "description": self._get_precision_description(self.precision),
        }

    def _get_precision_description(self, precision: int) -> str:
        """
        Get human-readable description of precision level.

        Parameters
        ----------
        precision : int
            Precision level

        Returns
        -------
        str
            Description of the precision level
        """
        descriptions = {
            1: "10° x 10° cells (global overview)",
            2: "5° x 5° cells (regional scale)",
            3: "1° x 1° cells (national scale)",
            4: "0.5° x 0.5° cells (30' x 30', sub-national)",
            5: "0.1° x 0.1° cells (6' x 6', local scale)",
        }
        return descriptions[precision]

    @property
    def area_km2(self) -> float:
        """
        Theoretical area of a C-squares cell at this precision in km².

        Returns
        -------
        float
            Theoretical area in square kilometers
        """
        cell_size_degrees = self._get_cell_size(self.precision)
        # Convert degrees to kilometers (approximate)
        # 1 degree ≈ 111.32 km at equator
        cell_size_km = cell_size_degrees * 111.32
        return cell_size_km * cell_size_km
