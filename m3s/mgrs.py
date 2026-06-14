"""
MGRS (Military Grid Reference System) grid implementation.
"""

import re
from typing import Any, override

import m3s_core

from .base import CoreBackedGrid, GridCell, cell_from_core


class MGRSGrid(CoreBackedGrid):
    """
    MGRS-based spatial grid system.

    Implements the Military Grid Reference System (MGRS) for creating
    uniform square grid cells based on UTM projections.
    """

    KEY = "mgrs"
    GRID_NAME = "MGRS"
    MIN_PRECISION = 0
    MAX_PRECISION = 5
    DEFAULT_PRECISION = 3

    def __init__(self, precision: int = 3):
        """
        Initialize MGRSGrid.

        Parameters
        ----------
        precision : int, optional
            MGRS precision level (0-5), by default 3.

            Precision levels:
                0 = 100km grid
                1 = 10km grid
                2 = 1km grid
                3 = 100m grid
                4 = 10m grid
                5 = 1m grid

        Raises
        ------
        ValueError
            If precision is not between 0 and 5
        """
        super().__init__(precision)

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """Get an MGRS cell from its identifier."""
        try:
            return cell_from_core(m3s_core.mgrs_cell_from_id(identifier))
        except Exception as e:
            raise ValueError(f"Invalid MGRS identifier: {identifier}") from e

    @override
    def identifier_to_precision(self, identifier: str) -> int | None:
        """
        Decode MGRS precision from the digit count in the identifier.

        MGRS precision is the number of digits per easting/northing component:
        ``31UDQ524117`` has six numeric digits (three each) → precision 3.
        Returns None if the identifier is not a recognisable MGRS reference.
        """
        match = re.fullmatch(r"\s*\d{1,2}[C-X][A-Z]{2}(\d*)\s*", identifier.upper())
        if match is None:
            return None
        digits = len(match.group(1))
        if digits % 2 != 0:
            return None
        return digits // 2

    def _get_utm_zone_from_mgrs(self, mgrs_id: str) -> int:
        """Get UTM zone EPSG code from MGRS identifier."""
        zone_letter = mgrs_id[:3]
        zone_number = int(zone_letter[:2])
        hemisphere_letter = zone_letter[2]

        if hemisphere_letter in "CDEFGHJKLM":
            return 32700 + zone_number
        else:
            return 32600 + zone_number

    @override
    def _get_additional_columns(self, cell: GridCell) -> dict[str, Any]:
        """
        Add UTM zone column for MGRS cells.

        Parameters
        ----------
        cell : GridCell
            The grid cell to extract UTM data from

        Returns
        -------
        dict
            Dictionary with 'utm' column
        """
        if not cell.identifier:
            return {}

        utm_epsg = self._get_utm_zone_from_mgrs(cell.identifier)
        return {"utm": utm_epsg}
