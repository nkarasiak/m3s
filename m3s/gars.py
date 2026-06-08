"""
GARS (Global Area Reference System) grid implementation.
"""

from functools import cached_property

from .base import CoreBackedGrid


class GARSGrid(CoreBackedGrid):
    """
    GARS (Global Area Reference System) spatial grid.

    Implements the military/aviation grid system using a hierarchical
    coordinate system with longitude bands and latitude zones.
    """

    KEY = "gars"
    MIN_PRECISION = 1
    MAX_PRECISION = 3
    DEFAULT_PRECISION = 2

    def __init__(self, precision: int = 1):
        """
        Initialize GARSGrid.

        Parameters
        ----------
        precision : int, optional
            GARS precision level (1-3), by default 1.

            Precision levels:
                1 = 30' × 30' (0.5° × 0.5°) - e.g., "001AA"
                2 = 15' × 15' (0.25° × 0.25°) - e.g., "001AA1"
                3 = 5' × 5' (~0.083° × 0.083°) - e.g., "001AA19"

        Raises
        ------
        ValueError
            If precision is not between 1 and 3
        """
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"GARS precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )
        super().__init__(precision)

    @cached_property
    def area_km2(self) -> float:
        """
        Approximate area of a GARS cell at this precision in square kilometers.

        Returns
        -------
        float
            Approximate area in square kilometers
        """
        size_degrees = {1: 0.5, 2: 0.25, 3: 0.25 / 3}[self.precision]
        size_km = size_degrees * 111.32
        return size_km * size_km

    def encode(self, lat: float, lon: float) -> str:
        """
        Encode a latitude/longitude into a GARS identifier.

        Parameters
        ----------
        lat : float
            Latitude coordinate (-90 to 90)
        lon : float
            Longitude coordinate (-180 to 180)

        Returns
        -------
        str
            GARS identifier string
        """
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")

        return self.get_cell_from_point(lat, lon).identifier

    def decode(self, gars_id: str) -> tuple:
        """
        Decode a GARS identifier into latitude/longitude bounds.

        Parameters
        ----------
        gars_id : str
            GARS identifier string

        Returns
        -------
        tuple
            (south, west, north, east) bounds
        """
        min_lon, min_lat, max_lon, max_lat = self.get_cell_from_identifier(
            gars_id
        ).polygon.bounds
        return (min_lat, min_lon, max_lat, max_lon)
