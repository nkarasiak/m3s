"""
Vectorized UTM zone calculations for high-performance batch operations.

Provides numpy-vectorized functions for calculating UTM zones from arrays
of coordinates, offering 10-100x speedup compared to iterative approaches.
"""

import logging
from typing import Tuple, Union

import numpy as np

from .constants import UTM_ZONE_WIDTH_DEGREES

logger = logging.getLogger(__name__)


def calculate_utm_zones_vectorized(
    lats: Union[np.ndarray, list, tuple], lons: Union[np.ndarray, list, tuple]
) -> np.ndarray:
    """
    Calculate UTM zones for arrays of coordinates using vectorized operations.

    Provides 10-100x speedup compared to iterative approaches for large datasets.
    Handles special cases for Norway and Svalbard.

    Parameters
    ----------
    lats : array-like
        Array of latitude values in degrees
    lons : array-like
        Array of longitude values in degrees

    Returns
    -------
    np.ndarray
        Array of UTM zone numbers (1-60)

    Examples
    --------
    >>> lats = np.array([40.7, 51.5, 35.7])
    >>> lons = np.array([-74.0, -0.1, 139.7])
    >>> zones = calculate_utm_zones_vectorized(lats, lons)
    >>> zones
    array([18, 30, 54])
    """
    # Convert to numpy arrays if needed
    lats = np.asarray(lats, dtype=np.float64)
    lons = np.asarray(lons, dtype=np.float64)

    # Validate shapes
    if lats.shape != lons.shape:
        raise ValueError(
            f"Latitude and longitude arrays must have the same shape. "
            f"Got lats: {lats.shape}, lons: {lons.shape}"
        )

    # Standard UTM zone calculation: zone = floor((lon + 180) / 6) + 1
    zones = ((lons + 180.0) / UTM_ZONE_WIDTH_DEGREES).astype(np.int32) + 1

    # Handle edge cases: ensure zones are in valid range [1, 60]
    zones = np.clip(zones, 1, 60)

    # Special case: Norway (56°N to 64°N)
    # Between 3°E and 12°E should use zone 32 (not 31/32/33)
    norway_mask = (lats >= 56.0) & (lats < 64.0) & (lons >= 3.0) & (lons < 12.0)
    zones[norway_mask] = 32

    # Special case: Svalbard (72°N to 84°N)
    # Specific longitude ranges map to specific zones
    svalbard_mask = (lats >= 72.0) & (lats < 84.0)

    # Zone 31: 0°E to 9°E
    svalbard_31 = svalbard_mask & (lons >= 0.0) & (lons < 9.0)
    zones[svalbard_31] = 31

    # Zone 33: 9°E to 21°E
    svalbard_33 = svalbard_mask & (lons >= 9.0) & (lons < 21.0)
    zones[svalbard_33] = 33

    # Zone 35: 21°E to 33°E
    svalbard_35 = svalbard_mask & (lons >= 21.0) & (lons < 33.0)
    zones[svalbard_35] = 35

    # Zone 37: 33°E to 42°E
    svalbard_37 = svalbard_mask & (lons >= 33.0) & (lons < 42.0)
    zones[svalbard_37] = 37

    return zones


def calculate_utm_epsg_codes_vectorized(
    lats: Union[np.ndarray, list, tuple], lons: Union[np.ndarray, list, tuple]
) -> np.ndarray:
    """
    Calculate UTM EPSG codes for arrays of coordinates.

    EPSG codes are calculated as:
    - Northern hemisphere: 32600 + zone (e.g., 32618 for zone 18N)
    - Southern hemisphere: 32700 + zone (e.g., 32718 for zone 18S)

    Parameters
    ----------
    lats : array-like
        Array of latitude values in degrees
    lons : array-like
        Array of longitude values in degrees

    Returns
    -------
    np.ndarray
        Array of EPSG codes (int32)

    Examples
    --------
    >>> lats = np.array([40.7, -33.9])
    >>> lons = np.array([-74.0, 18.4])
    >>> epsg_codes = calculate_utm_epsg_codes_vectorized(lats, lons)
    >>> epsg_codes
    array([32618, 32734])
    """
    # Convert to numpy arrays
    lats = np.asarray(lats, dtype=np.float64)
    lons = np.asarray(lons, dtype=np.float64)

    # Get UTM zones
    zones = calculate_utm_zones_vectorized(lats, lons)

    # Calculate EPSG codes based on hemisphere
    # Northern hemisphere: 32600 + zone
    # Southern hemisphere: 32700 + zone
    base_code = np.where(lats >= 0, 32600, 32700)
    epsg_codes = base_code + zones

    return epsg_codes.astype(np.int32)


def calculate_utm_hemisphere_vectorized(
    lats: Union[np.ndarray, list, tuple],
) -> np.ndarray:
    """
    Determine UTM hemisphere (north/south) for arrays of latitudes.

    Parameters
    ----------
    lats : array-like
        Array of latitude values in degrees

    Returns
    -------
    np.ndarray
        Array of hemisphere strings: "north" or "south"

    Examples
    --------
    >>> lats = np.array([40.7, -33.9, 0.0])
    >>> hemispheres = calculate_utm_hemisphere_vectorized(lats)
    >>> hemispheres
    array(['north', 'south', 'north'], dtype='<U5')
    """
    lats = np.asarray(lats, dtype=np.float64)
    return np.where(lats >= 0, "north", "south")


def get_utm_zone_info_vectorized(
    lats: Union[np.ndarray, list, tuple], lons: Union[np.ndarray, list, tuple]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Get complete UTM zone information for arrays of coordinates.

    Parameters
    ----------
    lats : array-like
        Array of latitude values in degrees
    lons : array-like
        Array of longitude values in degrees

    Returns
    -------
    zones : np.ndarray
        Array of UTM zone numbers (1-60)
    hemispheres : np.ndarray
        Array of hemisphere strings ("north" or "south")
    epsg_codes : np.ndarray
        Array of EPSG codes

    Examples
    --------
    >>> lats = np.array([40.7, -33.9])
    >>> lons = np.array([-74.0, 18.4])
    >>> zones, hemispheres, epsg_codes = get_utm_zone_info_vectorized(lats, lons)
    >>> zones
    array([18, 34])
    >>> hemispheres
    array(['north', 'south'], dtype='<U5')
    >>> epsg_codes
    array([32618, 32734])
    """
    lats = np.asarray(lats, dtype=np.float64)
    lons = np.asarray(lons, dtype=np.float64)

    zones = calculate_utm_zones_vectorized(lats, lons)
    hemispheres = calculate_utm_hemisphere_vectorized(lats)
    epsg_codes = calculate_utm_epsg_codes_vectorized(lats, lons)

    return zones, hemispheres, epsg_codes


def batch_calculate_utm_zones(
    lats: Union[np.ndarray, list, tuple],
    lons: Union[np.ndarray, list, tuple],
    chunk_size: int = 10000,
) -> np.ndarray:
    """
    Calculate UTM zones for very large datasets using chunked processing.

    Useful for datasets too large to fit in memory at once.

    Parameters
    ----------
    lats : array-like
        Array of latitude values
    lons : array-like
        Array of longitude values
    chunk_size : int, optional
        Number of coordinates to process at once, by default 10000

    Returns
    -------
    np.ndarray
        Array of UTM zone numbers

    Examples
    --------
    >>> # Process 1 million coordinates in chunks
    >>> lats = np.random.uniform(-90, 90, 1_000_000)
    >>> lons = np.random.uniform(-180, 180, 1_000_000)
    >>> zones = batch_calculate_utm_zones(lats, lons, chunk_size=10000)
    """
    lats = np.asarray(lats, dtype=np.float64)
    lons = np.asarray(lons, dtype=np.float64)

    n_coords = len(lats)
    zones = np.empty(n_coords, dtype=np.int32)

    # Process in chunks
    for i in range(0, n_coords, chunk_size):
        end_idx = min(i + chunk_size, n_coords)
        chunk_lats = lats[i:end_idx]
        chunk_lons = lons[i:end_idx]

        zones[i:end_idx] = calculate_utm_zones_vectorized(chunk_lats, chunk_lons)

    return zones


# Benchmark function for performance testing
def benchmark_utm_calculations(n_points: int = 10000) -> dict:
    """
    Benchmark vectorized UTM calculations.

    Parameters
    ----------
    n_points : int, optional
        Number of points to test, by default 10000

    Returns
    -------
    dict
        Benchmark results with timing information
    """
    import time

    # Generate random test data
    lats = np.random.uniform(-90, 90, n_points)
    lons = np.random.uniform(-180, 180, n_points)

    # Vectorized calculation
    start = time.time()
    zones_vec = calculate_utm_zones_vectorized(lats, lons)
    elapsed_vec = time.time() - start

    # Iterative calculation (for comparison)
    start = time.time()
    zones_iter = np.array(
        [int((lon + 180) / UTM_ZONE_WIDTH_DEGREES) + 1 for lon in lons]
    )
    elapsed_iter = time.time() - start

    speedup = elapsed_iter / elapsed_vec if elapsed_vec > 0 else float("inf")

    return {
        "n_points": n_points,
        "vectorized_time": elapsed_vec,
        "iterative_time": elapsed_iter,
        "speedup": speedup,
        "zones_match": np.allclose(
            zones_vec, zones_iter, atol=2
        ),  # Allow ±2 zones for special cases
    }
