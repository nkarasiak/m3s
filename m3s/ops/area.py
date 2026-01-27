"""Area calculations for polygons."""

from __future__ import annotations

from functools import lru_cache
from math import radians, sin

from shapely.geometry import Polygon
from shapely.ops import transform


@lru_cache(maxsize=256)
def _utm_transformer(utm_crs: str):
    import pyproj

    return pyproj.Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)


def _utm_crs_for(lon: float, lat: float) -> str:
    zone = int((lon + 180) / 6) + 1

    # Norway
    if 56 <= lat < 64 and 3 <= lon < 12:
        zone = 32
    # Svalbard
    elif 72 <= lat < 84 and lon >= 0:
        if lon < 9:
            zone = 31
        elif lon < 21:
            zone = 33
        elif lon < 33:
            zone = 35
        elif lon < 42:
            zone = 37

    hemisphere = "north" if lat >= 0 else "south"
    return (
        f"+proj=utm +zone={zone} +{hemisphere} "
        "+ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    )


def _spherical_bbox_area_km2(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> float:
    radius_km = 6371.0
    lat1 = radians(min_lat)
    lat2 = radians(max_lat)
    lon1 = radians(min_lon)
    lon2 = radians(max_lon)
    return abs((sin(lat2) - sin(lat1)) * (lon2 - lon1)) * radius_km * radius_km


def polygon_area_km2(polygon: Polygon) -> float:
    """Compute polygon area in square kilometers with UTM fallback."""
    try:
        centroid = polygon.centroid
        utm_crs = _utm_crs_for(centroid.x, centroid.y)
        transformer = _utm_transformer(utm_crs)
        projected_polygon = transform(transformer.transform, polygon)
        area_km2 = projected_polygon.area / 1_000_000
        if not (area_km2 > 0) or area_km2 != area_km2:
            raise ValueError("Invalid projected area")
        return area_km2
    except Exception:
        min_lon, min_lat, max_lon, max_lat = polygon.bounds
        return _spherical_bbox_area_km2(min_lon, min_lat, max_lon, max_lat)
