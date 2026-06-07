"""
Common projection utilities for M3S spatial operations.

Provides shared projection functions to avoid code duplication across
grid system implementations.
"""

import functools

from shapely.geometry import Polygon

from .constants import (
    EARTH_RADIUS_KM,
    UTM_NORTH_HEMISPHERE_BASE_EPSG,
    UTM_SOUTH_HEMISPHERE_BASE_EPSG,
    UTM_ZONE_WIDTH_DEGREES,
)


@functools.lru_cache(maxsize=256)
def get_utm_epsg_code(lat: float, lon: float) -> int:
    """
    Get the EPSG code for the optimal UTM zone at a given location.

    Computed from the 6°-wide UTM zone of ``lon`` and the hemisphere of ``lat``
    (north base ``32600`` / south base ``32700`` + zone). Results are cached.

    Parameters
    ----------
    lat : float
        Latitude in degrees
    lon : float
        Longitude in degrees

    Returns
    -------
    int
        EPSG code (e.g., 32618 for UTM Zone 18N)

    Examples
    --------
    >>> get_utm_epsg_code(40.7, -74.0)  # New York
    32618
    >>> get_utm_epsg_code(-33.9, 18.4)  # Cape Town
    32734
    """
    utm_zone = int((lon + 180) / UTM_ZONE_WIDTH_DEGREES) + 1
    base_code = (
        UTM_NORTH_HEMISPHERE_BASE_EPSG if lat >= 0 else UTM_SOUTH_HEMISPHERE_BASE_EPSG
    )
    return base_code + utm_zone


def calculate_polygon_area_spherical(polygon: Polygon) -> float:
    """
    Calculate approximate polygon area using spherical geometry.

    Less accurate than UTM projection but always works. Used as fallback
    when projection fails.

    Parameters
    ----------
    polygon : Polygon
        Shapely polygon to measure

    Returns
    -------
    float
        Approximate area in square kilometers

    Notes
    -----
    This is a rough approximation that assumes:
    - Small areas where Earth's curvature is minimal
    - Mid-latitude correction using average latitude
    - Rectangular approximation of the polygon bounds
    """
    from .constants import DEG_TO_RAD

    bounds = polygon.bounds
    min_lon, min_lat, max_lon, max_lat = bounds

    # Calculate differences in degrees
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon

    # Convert to radians
    lat_rad = (min_lat + max_lat) / 2 * DEG_TO_RAD
    lat_diff_rad = lat_diff * DEG_TO_RAD
    lon_diff_rad = lon_diff * DEG_TO_RAD

    # Approximate area using Earth's radius
    area_km2 = (
        EARTH_RADIUS_KM
        * EARTH_RADIUS_KM
        * abs(lat_diff_rad * lon_diff_rad * abs(lat_rad))
    )

    return area_km2


def get_utm_zone_number(lon: float) -> int:
    """
    Calculate UTM zone number from longitude.

    Parameters
    ----------
    lon : float
        Longitude in degrees

    Returns
    -------
    int
        UTM zone number (1-60)

    Examples
    --------
    >>> get_utm_zone_number(-74.0)  # New York
    18
    >>> get_utm_zone_number(139.7)  # Tokyo
    54
    """
    zone = int((lon + 180) / UTM_ZONE_WIDTH_DEGREES) + 1
    # Ensure zone is in valid range
    return max(1, min(60, zone))


def get_utm_hemisphere(lat: float) -> str:
    """
    Determine UTM hemisphere from latitude.

    Parameters
    ----------
    lat : float
        Latitude in degrees

    Returns
    -------
    str
        "north" or "south"

    Examples
    --------
    >>> get_utm_hemisphere(40.7)
    'north'
    >>> get_utm_hemisphere(-33.9)
    'south'
    """
    return "north" if lat >= 0 else "south"


def format_utm_crs_string(lat: float, lon: float) -> str:
    """
    Format a PROJ.4 UTM CRS string for a location.

    Parameters
    ----------
    lat : float
        Latitude in degrees
    lon : float
        Longitude in degrees

    Returns
    -------
    str
        PROJ.4 CRS string

    Examples
    --------
    >>> format_utm_crs_string(40.7, -74.0)
    '+proj=utm +zone=18 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    """
    zone = get_utm_zone_number(lon)
    hemisphere = get_utm_hemisphere(lat)
    return (
        f"+proj=utm +zone={zone} +{hemisphere} +ellps=WGS84 +datum=WGS84 "
        "+units=m +no_defs"
    )


# Export commonly used functions
__all__ = [
    "get_utm_epsg_code",
    "calculate_polygon_area_spherical",
    "get_utm_zone_number",
    "get_utm_hemisphere",
    "format_utm_crs_string",
]
