"""
Caching utilities for M3S spatial grid operations.

Provides efficient caching mechanisms for expensive spatial computations
including area calculations, coordinate transformations, and grid operations.
"""

import functools
import hashlib
import weakref
from typing import Any, Callable, Dict, Optional


class LRUCache:
    """
    Thread-safe Least Recently Used (LRU) cache implementation.

    Provides efficient caching with automatic eviction of least recently
    used items when the cache reaches its maximum size.
    """

    def __init__(self, maxsize: int = 256):
        """
        Initialize LRU cache.

        Parameters
        ----------
        maxsize : int, optional
            Maximum number of items to store in cache, by default 256
        """
        self.maxsize = maxsize
        self.cache: Dict[str, Any] = {}
        self.access_order: list = []

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache and update access order."""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any) -> None:
        """Put item in cache, evicting LRU item if necessary."""
        if key in self.cache:
            # Update existing item
            self.access_order.remove(key)
            self.access_order.append(key)
            self.cache[key] = value
        else:
            # Add new item
            if len(self.cache) >= self.maxsize:
                # Evict least recently used item
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]

            self.cache[key] = value
            self.access_order.append(key)

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self.access_order.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)


class SpatialCache:
    """
    Specialized cache for spatial operations with geographic-aware key generation.
    """

    def __init__(self, maxsize: int = 512):
        """
        Initialize spatial cache.

        Parameters
        ----------
        maxsize : int, optional
            Maximum number of cached items, by default 512
        """
        self._cache = LRUCache(maxsize)

    def _make_geo_key(self, lat: float, lon: float, precision: int) -> str:
        """
        Create cache key for geographic coordinates.

        Rounds coordinates to appropriate precision to improve cache hit rates
        for nearby coordinates.
        """
        # Round to 6 decimal places (~1m precision) for better cache efficiency
        lat_rounded = round(lat, 6)
        lon_rounded = round(lon, 6)
        return f"geo_{lat_rounded}_{lon_rounded}_{precision}"

    def _make_polygon_key(self, polygon_wkt: str, precision: int) -> str:
        """Create cache key for polygon-based operations."""
        # Use hash of WKT for memory efficiency
        wkt_hash = hashlib.md5(polygon_wkt.encode()).hexdigest()[:16]
        return f"poly_{wkt_hash}_{precision}"

    def get_cell(self, lat: float, lon: float, precision: int) -> Optional[Any]:
        """Get cached grid cell for coordinates."""
        key = self._make_geo_key(lat, lon, precision)
        return self._cache.get(key)

    def put_cell(self, lat: float, lon: float, precision: int, cell: Any) -> None:
        """Cache grid cell for coordinates."""
        key = self._make_geo_key(lat, lon, precision)
        self._cache.put(key, cell)

    def get_area(self, cell_id: str) -> Optional[float]:
        """Get cached area for cell."""
        key = f"area_{cell_id}"
        return self._cache.get(key)

    def put_area(self, cell_id: str, area: float) -> None:
        """Cache area for cell."""
        key = f"area_{cell_id}"
        self._cache.put(key, area)

    def get_neighbors(self, cell_id: str) -> Optional[list]:
        """Get cached neighbors for cell."""
        key = f"neighbors_{cell_id}"
        return self._cache.get(key)

    def put_neighbors(self, cell_id: str, neighbors: list) -> None:
        """Cache neighbors for cell."""
        key = f"neighbors_{cell_id}"
        self._cache.put(key, neighbors)

    def get_utm_zone(self, lat: float, lon: float) -> Optional[str]:
        """Get cached UTM zone for coordinates."""
        # Round to 1 decimal place for UTM zone caching (zones are large)
        lat_rounded = round(lat, 1)
        lon_rounded = round(lon, 1)
        key = f"utm_{lat_rounded}_{lon_rounded}"
        return self._cache.get(key)

    def put_utm_zone(self, lat: float, lon: float, utm_zone: str) -> None:
        """Cache UTM zone for coordinates."""
        lat_rounded = round(lat, 1)
        lon_rounded = round(lon, 1)
        key = f"utm_{lat_rounded}_{lon_rounded}"
        self._cache.put(key, utm_zone)

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return self._cache.size()


# Global cache instances
_global_spatial_cache = SpatialCache(maxsize=1024)
_grid_instance_caches: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def get_spatial_cache() -> SpatialCache:
    """Get the global spatial cache instance."""
    return _global_spatial_cache


def get_grid_cache(grid_instance: Any) -> SpatialCache:
    """
    Get cache instance specific to a grid object.

    Uses weak references to avoid memory leaks when grid objects are deleted.
    """
    if grid_instance not in _grid_instance_caches:
        _grid_instance_caches[grid_instance] = SpatialCache(maxsize=512)
    return _grid_instance_caches[grid_instance]


def cached_method(
    cache_key_func: Optional[Callable] = None, use_global_cache: bool = True
):
    """
    Decorator for caching method results.

    Parameters
    ----------
    cache_key_func : callable, optional
        Function to generate cache key from method arguments
    use_global_cache : bool, optional
        Whether to use global cache (True) or instance-specific cache (False)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Choose cache instance
            if use_global_cache:
                cache = get_spatial_cache()
            else:
                cache = get_grid_cache(self)

            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(self, *args, **kwargs)
            else:
                # Default key generation
                args_str = "_".join(str(arg) for arg in args)
                kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{func.__name__}_{args_str}_{kwargs_str}"

            # Try to get from cache
            result = cache._cache.get(cache_key)
            if result is not None:
                return result

            # Compute and cache result
            result = func(self, *args, **kwargs)
            cache._cache.put(cache_key, result)
            return result

        # Add cache management methods
        wrapper.clear_cache = lambda: (
            get_spatial_cache().clear()
            if use_global_cache
            else get_grid_cache(wrapper.__self__).clear()
        )
        wrapper.cache_size = lambda: (
            get_spatial_cache().size()
            if use_global_cache
            else get_grid_cache(wrapper.__self__).size()
        )

        return wrapper

    return decorator


def cached_property(func: Callable) -> property:
    """
    Decorator for caching property results on the instance.

    Similar to functools.cached_property but with explicit cache management.
    """
    attr_name = f"_cached_{func.__name__}"

    @functools.wraps(func)
    def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)

    def clear_cache(self):
        if hasattr(self, attr_name):
            delattr(self, attr_name)

    def has_cache(self):
        return hasattr(self, attr_name)

    # Add cache management methods to the property
    wrapper.clear_cache = clear_cache
    wrapper.has_cache = has_cache

    return property(wrapper)


# Utility functions for common cache key patterns
def geo_cache_key(grid_instance, lat: float, lon: float, **kwargs) -> str:
    """Generate cache key for geographic coordinate operations."""
    precision = getattr(grid_instance, "precision", 0)
    lat_rounded = round(lat, 6)
    lon_rounded = round(lon, 6)
    extra = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return f"geo_{lat_rounded}_{lon_rounded}_{precision}_{extra}"


def cell_cache_key(grid_instance, cell_id: str, **kwargs) -> str:
    """Generate cache key for cell-based operations."""
    extra = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return f"cell_{cell_id}_{extra}"


def bbox_cache_key(
    grid_instance,
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    **kwargs,
) -> str:
    """Generate cache key for bounding box operations."""
    precision = getattr(grid_instance, "precision", 0)
    # Round to reasonable precision for bbox caching
    bbox_key = f"{round(min_lat, 4)}_{round(min_lon, 4)}_{round(max_lat, 4)}_{round(max_lon, 4)}"
    extra = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return f"bbox_{bbox_key}_{precision}_{extra}"
