"""
Common projection utilities for M3S spatial operations.

Provides shared projection functions to avoid code duplication across
grid system implementations.
"""

import functools
import logging
from typing import Optional

import pyproj
from shapely.geometry import Polygon
from shapely.ops import transform

from .cache import get_spatial_cache
from .constants import (
    EARTH_RADIUS_KM,
    UTM_NORTH_HEMISPHERE_BASE_EPSG,
    UTM_SOUTH_HEMISPHERE_BASE_EPSG,
    UTM_ZONE_WIDTH_DEGREES,
)

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=256)
def get_utm_epsg_code(lat: float, lon: float) -> int:
    """
    Get the EPSG code for the optimal UTM zone at a given location.

    Uses PyProj 3.5+ auto-detection when available, with fallback to
    manual calculation. Results are cached for performance.

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
    try:
        from pyproj.aoi import AreaOfInterest
        from pyproj.database import query_utm_crs_info

        # Use PyProj 3.5+ auto-detection
        aoi = AreaOfInterest(
            west_lon_degree=lon,
            south_lat_degree=lat,
            east_lon_degree=lon,
            north_lat_degree=lat,
        )

        utm_crs_list = query_utm_crs_info(
            datum_name="WGS 84",
            area_of_interest=aoi,
        )

        if utm_crs_list:
            # Extract EPSG code as integer
            code = int(utm_crs_list[0].code)
            return code

    except (ImportError, AttributeError) as e:
        logger.debug(f"PyProj 3.5+ not available: {e}. Using manual calculation.")

    # Fallback: manual UTM calculation
    utm_zone = int((lon + 180) / UTM_ZONE_WIDTH_DEGREES) + 1
    base_code = (
        UTM_NORTH_HEMISPHERE_BASE_EPSG if lat >= 0 else UTM_SOUTH_HEMISPHERE_BASE_EPSG
    )
    return base_code + utm_zone


@functools.lru_cache(maxsize=128)
def get_utm_transformer(lat: float, lon: float) -> pyproj.Transformer:
    """
    Get a cached Transformer for WGS84 to optimal UTM projection.

    Parameters
    ----------
    lat : float
        Latitude in degrees
    lon : float
        Longitude in degrees

    Returns
    -------
    pyproj.Transformer
        Transformer from WGS84 (EPSG:4326) to UTM

    Examples
    --------
    >>> transformer = get_utm_transformer(40.7, -74.0)
    >>> x, y = transformer.transform(-74.0, 40.7)
    """
    epsg_code = get_utm_epsg_code(lat, lon)
    return pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_code}", always_xy=True)


def calculate_polygon_area_km2(
    polygon: Polygon, cache_key: Optional[str] = None, use_cache: bool = True
) -> float:
    """
    Calculate polygon area in square kilometers using equal-area projection.

    Automatically selects the optimal UTM zone based on polygon centroid
    and uses equal-area projection for accurate area calculation.

    Parameters
    ----------
    polygon : Polygon
        Shapely polygon to measure
    cache_key : str, optional
        Key for caching the result
    use_cache : bool, optional
        Whether to use caching, by default True

    Returns
    -------
    float
        Area in square kilometers

    Examples
    --------
    >>> from shapely.geometry import box
    >>> polygon = box(-74.01, 40.70, -74.00, 40.71)
    >>> area = calculate_polygon_area_km2(polygon)
    >>> 0.9 < area < 1.0  # Approximately 0.94 km²
    True
    """
    # Check cache first
    if use_cache and cache_key:
        cache = get_spatial_cache()
        cached_area = cache.get_area(cache_key)
        if cached_area is not None:
            return cached_area

    try:
        # Get centroid for UTM zone determination
        centroid = polygon.centroid
        lon, lat = centroid.x, centroid.y

        # Get transformer for optimal UTM projection
        transformer = get_utm_transformer(lat, lon)

        # Transform polygon to UTM
        projected_polygon = transform(transformer.transform, polygon)

        # Calculate area in square meters, convert to km²
        area_m2 = projected_polygon.area
        area_km2 = area_m2 / 1_000_000

        # Cache if requested
        if use_cache and cache_key:
            cache = get_spatial_cache()
            cache.put_area(cache_key, area_km2)

        return area_km2

    except Exception as e:
        # Fallback: spherical approximation
        logger.warning(f"UTM projection failed: {e}. Using spherical approximation.")
        return calculate_polygon_area_spherical(polygon)


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
    return f"+proj=utm +zone={zone} +{hemisphere} +ellps=WGS84 +datum=WGS84 +units=m +no_defs"


# Export commonly used functions
__all__ = [
    "get_utm_epsg_code",
    "get_utm_transformer",
    "calculate_polygon_area_km2",
    "calculate_polygon_area_spherical",
    "get_utm_zone_number",
    "get_utm_hemisphere",
    "format_utm_crs_string",
]
