"""
Type definitions for M3S library.

Provides type-safe enums, dataclasses, and type aliases to ensure
consistency and type checking throughout the codebase.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class ConversionMethod(Enum):
    """
    Methods for converting between grid systems.

    Attributes
    ----------
    CENTROID : str
        Use centroid of source cell to determine target cell
    OVERLAP : str
        Find all target cells that overlap with source cell
    CONTAINMENT : str
        Find all target cells fully contained within source cell
    """

    CENTROID = "centroid"
    OVERLAP = "overlap"
    CONTAINMENT = "containment"


class GridSystemType(Enum):
    """
    Supported grid system types.

    Attributes
    ----------
    GEOHASH : str
        Geohash grid system (base-32 encoded)
    H3 : str
        Uber H3 hexagonal grid
    QUADKEY : str
        Microsoft Bing Maps quadtree tiles
    S2 : str
        Google S2 spherical geometry cells
    SLIPPY : str
        OpenStreetMap slippy map tiles
    MGRS : str
        Military Grid Reference System (UTM-based)
    CSQUARES : str
        C-squares marine data indexing
    GARS : str
        Global Area Reference System
    MAIDENHEAD : str
        Amateur radio grid locator system
    PLUSCODE : str
        Open Location Codes (Plus Codes)
    WHAT3WORDS : str
        What3Words-style 3-meter precision squares
    A5 : str
        A5 pentagonal DGGS (dodecahedral projection)
    """

    GEOHASH = "geohash"
    H3 = "h3"
    QUADKEY = "quadkey"
    S2 = "s2"
    SLIPPY = "slippy"
    MGRS = "mgrs"
    CSQUARES = "csquares"
    GARS = "gars"
    MAIDENHEAD = "maidenhead"
    PLUSCODE = "pluscode"
    WHAT3WORDS = "what3words"
    A5 = "a5"

    @classmethod
    def from_string(cls, value: str) -> "GridSystemType":
        """
        Convert string to GridSystemType enum.

        Parameters
        ----------
        value : str
            Grid system name (case-insensitive)

        Returns
        -------
        GridSystemType
            The corresponding enum value

        Raises
        ------
        ValueError
            If the grid system name is not recognized
        """
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
        raise ValueError(
            f"Unknown grid system: {value}. " f"Valid options: {[m.value for m in cls]}"
        )


class RelationshipType(Enum):
    """
    Spatial relationships between grid cells.

    Attributes
    ----------
    ADJACENT : str
        Cells share a border
    CONTAINS : str
        First cell contains second cell
    CONTAINED_BY : str
        First cell is contained by second cell
    OVERLAPS : str
        Cells overlap but neither contains the other
    DISJOINT : str
        Cells do not touch or overlap
    """

    ADJACENT = "adjacent"
    CONTAINS = "contains"
    CONTAINED_BY = "contained_by"
    OVERLAPS = "overlaps"
    DISJOINT = "disjoint"


@dataclass(frozen=True)
class PrecisionSpec:
    """
    Specification for grid precision/resolution.

    Attributes
    ----------
    system : GridSystemType
        The grid system type
    precision : int
        Precision/resolution level
    area_km2 : Optional[float]
        Approximate cell area in square kilometers
    edge_length_km : Optional[float]
        Approximate edge length in kilometers
    """

    system: GridSystemType
    precision: int
    area_km2: Optional[float] = None
    edge_length_km: Optional[float] = None

    def __post_init__(self):
        """Validate precision after initialization."""
        from .constants import PRECISION_LIMITS

        # Get limits for this system
        limits = PRECISION_LIMITS.get(self.system.value)
        if limits:
            min_val = limits["min"]
            max_val = limits["max"]
            if not (min_val <= self.precision <= max_val):
                raise ValueError(
                    f"{self.system.value} precision must be between "
                    f"{min_val} and {max_val}, got {self.precision}"
                )


@dataclass
class BoundingBox:
    """
    Geographic bounding box.

    Attributes
    ----------
    min_lat : float
        Minimum latitude (south)
    min_lon : float
        Minimum longitude (west)
    max_lat : float
        Maximum latitude (north)
    max_lon : float
        Maximum longitude (east)
    """

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def __post_init__(self):
        """Validate bounds after initialization."""
        from .constants import (
            MAX_LATITUDE,
            MAX_LONGITUDE,
            MIN_LATITUDE,
            MIN_LONGITUDE,
        )

        if not (MIN_LATITUDE <= self.min_lat <= MAX_LATITUDE):
            raise ValueError(
                f"min_lat must be between {MIN_LATITUDE} and {MAX_LATITUDE}"
            )

        if not (MIN_LATITUDE <= self.max_lat <= MAX_LATITUDE):
            raise ValueError(
                f"max_lat must be between {MIN_LATITUDE} and {MAX_LATITUDE}"
            )

        if not (MIN_LONGITUDE <= self.min_lon <= MAX_LONGITUDE):
            raise ValueError(
                f"min_lon must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}"
            )

        if not (MIN_LONGITUDE <= self.max_lon <= MAX_LONGITUDE):
            raise ValueError(
                f"max_lon must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}"
            )

        if self.min_lat >= self.max_lat:
            raise ValueError(
                f"min_lat ({self.min_lat}) must be less than max_lat ({self.max_lat})"
            )

        if self.min_lon >= self.max_lon:
            raise ValueError(
                f"min_lon ({self.min_lon}) must be less than max_lon ({self.max_lon})"
            )

    @property
    def center(self) -> Tuple[float, float]:
        """
        Calculate the center point of the bounding box.

        Returns
        -------
        Tuple[float, float]
            (latitude, longitude) of center point
        """
        center_lat = (self.min_lat + self.max_lat) / 2
        center_lon = (self.min_lon + self.max_lon) / 2
        return (center_lat, center_lon)

    @property
    def width_degrees(self) -> float:
        """
        Get width of bounding box in degrees.

        Returns
        -------
        float
            Width in longitude degrees
        """
        return self.max_lon - self.min_lon

    @property
    def height_degrees(self) -> float:
        """
        Get height of bounding box in degrees.

        Returns
        -------
        float
            Height in latitude degrees
        """
        return self.max_lat - self.min_lat

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """
        Convert to tuple format.

        Returns
        -------
        Tuple[float, float, float, float]
            (min_lat, min_lon, max_lat, max_lon)
        """
        return (self.min_lat, self.min_lon, self.max_lat, self.max_lon)


# Type aliases for common patterns
Coordinate = Tuple[float, float]  # (latitude, longitude)
CellIdentifier = str  # Grid cell identifier string
Bounds = Tuple[float, float, float, float]  # (min_lat, min_lon, max_lat, max_lon)
