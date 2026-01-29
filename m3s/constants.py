"""
Constants used throughout the M3S library.

Centralizes all magic numbers and configuration values to ensure consistency
and maintainability across the codebase.
"""

import math

# Earth model constants
EARTH_RADIUS_KM = 6371.0088  # Mean Earth radius in kilometers
EARTH_RADIUS_M = EARTH_RADIUS_KM * 1000  # Mean Earth radius in meters

# Mathematical constants
PI = math.pi
DEG_TO_RAD = PI / 180.0
RAD_TO_DEG = 180.0 / PI

# Web Mercator projection limits
WEB_MERCATOR_MAX_LAT = 85.051129  # Maximum latitude for Web Mercator projection
WEB_MERCATOR_MIN_LAT = -85.051129

# UTM projection constants
UTM_ZONE_WIDTH_DEGREES = 6  # Width of a UTM zone in degrees
UTM_FALSE_EASTING = 500000  # False easting in meters
UTM_NORTH_HEMISPHERE_BASE_EPSG = 32600  # EPSG code base for northern hemisphere
UTM_SOUTH_HEMISPHERE_BASE_EPSG = 32700  # EPSG code base for southern hemisphere

# Default precision levels for different grid systems
DEFAULT_PRECISIONS = {
    "geohash": 5,  # ~5km resolution
    "h3": 7,  # ~5km resolution
    "quadkey": 12,  # ~5km resolution
    "s2": 13,  # ~5km resolution
    "slippy": 12,  # ~5km resolution
    "mgrs": 5,  # 1km resolution
    "csquares": 2,  # 10° resolution
    "gars": 2,  # 5' resolution
    "maidenhead": 3,  # ~12km resolution (fields/squares)
    "pluscode": 4,  # ~12.5m resolution in this implementation
    "what3words": 3,  # 3m resolution
    "a5": 5,  # Varies by resolution
}

# Precision/resolution limits for grid systems
PRECISION_LIMITS = {
    "geohash": {"min": 1, "max": 12},
    "h3": {"min": 0, "max": 15},
    "quadkey": {"min": 1, "max": 23},
    "s2": {"min": 0, "max": 30},
    "slippy": {"min": 0, "max": 20},
    "mgrs": {"min": 1, "max": 5},
    "csquares": {"min": 1, "max": 5},
    "gars": {"min": 1, "max": 3},
    "maidenhead": {"min": 1, "max": 4},
    "pluscode": {"min": 1, "max": 7},
    "what3words": {"min": 3, "max": 3},
    "a5": {"min": 0, "max": 30},
}

# Cache configuration
DEFAULT_CACHE_SIZE = 512  # Default number of items in cache
SPATIAL_CACHE_SIZE = 1024  # Larger cache for spatial operations
UTM_CACHE_PRECISION_DECIMALS = 1  # Precision for UTM zone caching (degrees)
GEO_CACHE_PRECISION_DECIMALS = 6  # Precision for geographic coordinate caching (~1m)

# Parallel processing defaults
DEFAULT_CHUNK_SIZE = 10000  # Default chunk size for parallel processing
DEFAULT_MEMORY_LIMIT = "2GB"  # Default memory limit per worker
DEFAULT_THREADS_PER_WORKER = 2  # Default threads per worker

# Coordinate validation bounds
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0

# Spatial tolerance values
GEOMETRY_SIMPLIFY_TOLERANCE = 1e-6  # Tolerance for geometry simplification
COORDINATE_EPSILON = 1e-10  # Small epsilon for coordinate comparisons

# Grid system names (for validation and conversion)
GRID_SYSTEMS = [
    "geohash",
    "h3",
    "quadkey",
    "s2",
    "slippy",
    "mgrs",
    "csquares",
    "gars",
    "maidenhead",
    "pluscode",
    "what3words",
    "a5",
]

# CRS/EPSG codes
WGS84_EPSG = "EPSG:4326"  # WGS84 geographic coordinate system
WEB_MERCATOR_EPSG = "EPSG:3857"  # Web Mercator projection
