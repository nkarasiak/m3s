"""
Tests for caching functionality.
"""

from shapely.geometry import Polygon

from m3s import GeohashGrid
from m3s.base import GridCell
from m3s.cache import LRUCache, SpatialCache, get_spatial_cache


class TestLRUCache:
    """Test LRU cache implementation."""

    def test_basic_operations(self):
        """Test basic cache operations."""
        cache = LRUCache(maxsize=3)

        # Test empty cache
        assert cache.get("key1") is None
        assert cache.size() == 0

        # Test put and get
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size() == 1

        # Test multiple items
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        assert cache.size() == 3

        # Test eviction (cache is at maxsize=3)
        cache.put("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key1") is None  # Should be evicted (LRU)
        assert cache.get("key4") == "value4"  # Should be present

    def test_lru_behavior(self):
        """Test that least recently used items are evicted."""
        cache = LRUCache(maxsize=2)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key3, which should evict key2 (LRU)
        cache.put("key3", "value3")

        assert cache.get("key1") == "value1"  # Should still be there
        assert cache.get("key2") is None  # Should be evicted
        assert cache.get("key3") == "value3"  # Should be there

    def test_update_existing(self):
        """Test updating existing cache entries."""
        cache = LRUCache(maxsize=2)

        cache.put("key1", "value1")
        cache.put("key1", "updated_value1")  # Update existing

        assert cache.get("key1") == "updated_value1"
        assert cache.size() == 1

    def test_clear(self):
        """Test cache clearing."""
        cache = LRUCache(maxsize=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None


class TestSpatialCache:
    """Test spatial cache functionality."""

    def test_geographic_operations(self):
        """Test caching of geographic operations."""
        cache = SpatialCache(maxsize=10)

        # Test cell caching
        lat, lon, precision = 40.7, -74.0, 5
        cell = GridCell(
            "dr5ru", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), precision
        )

        assert cache.get_cell(lat, lon, precision) is None
        cache.put_cell(lat, lon, precision, cell)
        cached_cell = cache.get_cell(lat, lon, precision)
        assert cached_cell == cell

        # Test area caching
        cell_id = "dr5ru"
        area = 25.5

        assert cache.get_area(cell_id) is None
        cache.put_area(cell_id, area)
        assert cache.get_area(cell_id) == area

    def test_utm_zone_caching(self):
        """Test UTM zone caching."""
        cache = SpatialCache(maxsize=10)

        lat, lon = 40.7, -74.0
        utm_zone = "18N"

        assert cache.get_utm_zone(lat, lon) is None
        cache.put_utm_zone(lat, lon, utm_zone)
        assert cache.get_utm_zone(lat, lon) == utm_zone

        # Test that nearby coordinates get same cached result
        # (due to rounding in cache key generation)
        nearby_lat, nearby_lon = 40.71, -74.01
        assert cache.get_utm_zone(nearby_lat, nearby_lon) == utm_zone

    def test_neighbors_caching(self):
        """Test neighbor caching."""
        cache = SpatialCache(maxsize=10)

        cell_id = "dr5ru"
        neighbors = [
            GridCell("dr5rv", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 5),
            GridCell("dr5rw", Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]), 5),
        ]

        assert cache.get_neighbors(cell_id) is None
        cache.put_neighbors(cell_id, neighbors)
        cached_neighbors = cache.get_neighbors(cell_id)
        assert cached_neighbors == neighbors


class TestCachedMethods:
    """Test cached method decorators."""

    def test_geohash_caching(self):
        """Test that GeohashGrid methods use caching."""
        grid = GeohashGrid(precision=5)

        # Test get_cell_from_point caching
        lat, lon = 40.7, -74.0

        # First call should compute
        cell1 = grid.get_cell_from_point(lat, lon)

        # Second call should use cache
        cell2 = grid.get_cell_from_point(lat, lon)

        assert cell1.identifier == cell2.identifier
        assert cell1.polygon.equals(cell2.polygon)

        # Test neighbors caching
        neighbors1 = grid.get_neighbors(cell1)
        neighbors2 = grid.get_neighbors(cell1)

        assert len(neighbors1) == len(neighbors2)
        for n1, n2 in zip(neighbors1, neighbors2):
            assert n1.identifier == n2.identifier

    def test_cache_with_different_precision(self):
        """Test that different precisions are cached separately."""
        grid1 = GeohashGrid(precision=5)
        grid2 = GeohashGrid(precision=6)

        lat, lon = 40.7, -74.0

        cell1 = grid1.get_cell_from_point(lat, lon)
        cell2 = grid2.get_cell_from_point(lat, lon)

        # Should be different due to different precision
        assert cell1.identifier != cell2.identifier
        assert cell1.precision != cell2.precision

    def test_area_caching(self):
        """Test that area calculations are cached."""
        grid = GeohashGrid(precision=5)
        cell = grid.get_cell_from_point(40.7, -74.0)

        # First access should compute
        area1 = cell.area_km2

        # Second access should use cached value
        area2 = cell.area_km2

        assert area1 == area2

        # Test that the property is working consistently
        area3 = cell.area_km2
        assert area3 == area1  # Should be same value

    def test_global_cache_instance(self):
        """Test global cache instance functionality."""
        cache = get_spatial_cache()

        assert isinstance(cache, SpatialCache)

        # Test that we get the same instance
        cache2 = get_spatial_cache()
        assert cache is cache2

        # Test cache operations
        initial_size = cache.size()
        cache.put_area("test_cell", 100.0)
        assert cache.size() == initial_size + 1

        assert cache.get_area("test_cell") == 100.0


class TestCachePerformance:
    """Test cache performance characteristics."""

    def test_cache_hit_rate(self):
        """Test that repeated operations benefit from caching."""
        grid = GeohashGrid(precision=5)

        # Test coordinates
        coords = [
            (40.7, -74.0),
            (40.8, -74.1),
            (40.7, -74.0),  # Repeat
            (40.9, -74.2),
            (40.8, -74.1),  # Repeat
        ]

        cells = []
        for lat, lon in coords:
            cell = grid.get_cell_from_point(lat, lon)
            cells.append(cell)

        # Verify that repeated coordinates return same cells
        assert cells[0].identifier == cells[2].identifier
        assert cells[1].identifier == cells[4].identifier

    def test_memory_efficiency(self):
        """Test that cache doesn't grow unbounded."""
        cache = SpatialCache(maxsize=5)

        # Add more items than cache size
        for i in range(10):
            cache.put_area(f"cell_{i}", float(i))

        # Cache should not exceed maxsize
        assert cache.size() <= 5

        # Most recent items should still be in cache
        assert cache.get_area("cell_9") is not None
        assert cache.get_area("cell_8") is not None
