"""
Maidenhead locator system grid implementation.
"""

from .base import CoreBackedGrid, validate_lat_lon


class MaidenheadGrid(CoreBackedGrid):
    """
    Maidenhead locator system spatial grid.

    Implements the ham radio grid system using a hierarchical
    coordinate system with alternating letter/number pairs.
    """

    KEY = "mh"
    GRID_NAME = "Maidenhead"
    MIN_PRECISION = 1
    MAX_PRECISION = 4
    DEFAULT_PRECISION = 4

    def __init__(self, precision: int = 4):
        """
        Initialize MaidenheadGrid.

        Parameters
        ----------
        precision : int, optional
            Maidenhead precision level (1-4), by default 4.

            Precision levels:
                1 = Field (20° × 10°) - e.g., "JO"
                2 = Square (2° × 1°) - e.g., "JO62"
                3 = Subsquare (5' × 2.5') - e.g., "JO62KO"
                4 = Extended square (12.5" × 6.25") - e.g., "JO62KO78"

        Raises
        ------
        ValueError
            If precision is not between 1 and 4
        """
        super().__init__(precision)

    def encode(self, lat: float, lon: float) -> str:
        """
        Encode a latitude/longitude into a Maidenhead locator.

        Parameters
        ----------
        lat : float
            Latitude coordinate (-90 to 90)
        lon : float
            Longitude coordinate (-180 to 180)

        Returns
        -------
        str
            Maidenhead locator string
        """
        validate_lat_lon(lat, lon)
        return self.get_cell_from_point(lat, lon).identifier

    def decode(self, locator: str) -> tuple[float, float, float, float]:
        """
        Decode a Maidenhead locator into latitude/longitude bounds.

        Parameters
        ----------
        locator : str
            Maidenhead locator string

        Returns
        -------
        tuple
            (south, west, north, east) bounds
        """
        min_lon, min_lat, max_lon, max_lat = self.get_cell_from_identifier(
            locator
        ).polygon.bounds
        return (min_lat, min_lon, max_lat, max_lon)
