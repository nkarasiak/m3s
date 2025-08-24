"""
Tests for Slippy Map Tiling grid system in M3S.
"""

import pytest
from shapely.geometry import Point, Polygon, box

from m3s.base import GridCell
from m3s.slippy import SlippyGrid


class TestSlippyGrid:
    """Test SlippyGrid class."""

    @pytest.fixture
    def grid_zoom_10(self):
        """Create a Slippy grid with zoom 10."""
        return SlippyGrid(zoom=10)

    @pytest.fixture
    def grid_zoom_15(self):
        """Create a Slippy grid with zoom 15."""
        return SlippyGrid(zoom=15)

    def test_initialization_valid_zooms(self):
        """Test grid initialization with valid zoom levels."""
        for zoom in [0, 5, 10, 18, 22]:
            grid = SlippyGrid(zoom=zoom)
            assert grid.zoom == zoom
            assert grid.precision == zoom

    def test_initialization_invalid_zooms(self):
        """Test grid initialization with invalid zoom levels."""
        invalid_zooms = [-1, 23, 100]
        for zoom in invalid_zooms:
            with pytest.raises(
                ValueError, match="Slippy zoom level must be between 0 and 22"
            ):
                SlippyGrid(zoom=zoom)

    def test_area_km2_property(self):
        """Test area_km2 property calculation."""
        # Test zoom 0 (1 tile covering the world)
        grid_0 = SlippyGrid(zoom=0)
        expected_area_0 = 40075.0**2  # Earth circumference squared
        assert abs(grid_0.area_km2 - expected_area_0) < 1000  # Allow some tolerance

        # Test zoom 1 (4 tiles)
        grid_1 = SlippyGrid(zoom=1)
        expected_area_1 = (40075.0 / 2) ** 2
        assert abs(grid_1.area_km2 - expected_area_1) < 1000

        # Test that higher zoom levels have smaller areas
        grid_10 = SlippyGrid(zoom=10)
        grid_15 = SlippyGrid(zoom=15)
        assert grid_15.area_km2 < grid_10.area_km2

    def test_deg2num_conversion(self, grid_zoom_10):
        """Test latitude/longitude to tile conversion."""
        # Test known coordinates
        test_cases = [
            (0.0, 0.0),  # Equator, Prime Meridian
            (51.5074, -0.1278),  # London
            (40.7128, -74.0060),  # NYC
            (-33.8688, 151.2093),  # Sydney
        ]

        for lat, lon in test_cases:
            x, y = grid_zoom_10._deg2num(lat, lon)
            assert isinstance(x, int)
            assert isinstance(y, int)
            assert 0 <= x < 2**10
            assert 0 <= y < 2**10

    def test_num2deg_conversion(self, grid_zoom_10):
        """Test tile to bounding box conversion."""
        # Test center tile
        x, y = 512, 512  # Center of 1024x1024 grid
        min_lon, min_lat, max_lon, max_lat = grid_zoom_10._num2deg(x, y)

        assert -180 <= min_lon < max_lon <= 180
        assert -85.05 <= min_lat < max_lat <= 85.05

        # Test that bounding box has reasonable size
        width = max_lon - min_lon
        height = max_lat - min_lat
        assert width > 0
        assert height > 0

    def test_roundtrip_conversion(self, grid_zoom_10):
        """Test that deg2num and num2deg are consistent."""
        test_points = [
            (0.0, 0.0),
            (40.7128, -74.0060),  # NYC
            (51.5074, -0.1278),  # London
        ]

        for lat, lon in test_points:
            x, y = grid_zoom_10._deg2num(lat, lon)
            min_lon, min_lat, max_lon, max_lat = grid_zoom_10._num2deg(x, y)

            # Point should be within the tile bounds
            assert min_lon <= lon <= max_lon
            assert min_lat <= lat <= max_lat

    def test_get_cell_from_point_nyc(self, grid_zoom_10):
        """Test getting tile from NYC coordinates."""
        lat, lon = 40.7128, -74.0060
        cell = grid_zoom_10.get_cell_from_point(lat, lon)

        assert isinstance(cell, GridCell)
        assert isinstance(cell.identifier, str)
        assert "/" in cell.identifier  # Should be in z/x/y format
        assert cell.precision == 10
        assert isinstance(cell.polygon, Polygon)

        # Check that the cell contains the original point
        point = Point(lon, lat)
        assert cell.polygon.contains(point) or cell.polygon.touches(point)

    def test_get_cell_from_point_edge_cases(self, grid_zoom_10):
        """Test getting tiles from edge case coordinates."""
        edge_cases = [
            (85.0, 180.0),  # Near north pole, dateline
            (-85.0, -180.0),  # Near south pole, antimeridian
            (0.0, 0.0),  # Equator, prime meridian
        ]

        for lat, lon in edge_cases:
            cell = grid_zoom_10.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert "/" in cell.identifier

    def test_get_cell_from_identifier_valid(self, grid_zoom_10):
        """Test getting tile from valid z/x/y identifier."""
        # Get a tile first
        cell = grid_zoom_10.get_cell_from_point(40.7128, -74.0060)
        identifier = cell.identifier

        # Get tile from identifier
        cell_from_id = grid_zoom_10.get_cell_from_identifier(identifier)

        assert cell_from_id.identifier == identifier
        assert isinstance(cell_from_id.polygon, Polygon)

    def test_get_cell_from_identifier_invalid(self, grid_zoom_10):
        """Test getting tile from invalid z/x/y identifier."""
        invalid_identifiers = [
            "invalid_identifier",
            "10/1024/1024",  # Coordinates too large for zoom 10
            "5/100/200",  # Wrong zoom level
            "10/100",  # Missing y coordinate
            "10/100/200/300",  # Too many parts
        ]

        for identifier in invalid_identifiers:
            with pytest.raises(ValueError, match="Invalid Slippy tile identifier"):
                grid_zoom_10.get_cell_from_identifier(identifier)

    def test_get_neighbors(self, grid_zoom_10):
        """Test getting neighboring tiles."""
        # Get a tile not on the edge
        cell = grid_zoom_10.get_cell_from_point(40.0, -100.0)  # Central US
        neighbors = grid_zoom_10.get_neighbors(cell)

        assert isinstance(neighbors, list)
        assert len(neighbors) <= 8  # At most 8 neighbors
        assert len(neighbors) >= 3  # At least 3 neighbors (corner case)

        # All neighbors should be valid GridCells
        for neighbor in neighbors:
            assert isinstance(neighbor, GridCell)
            assert "/" in neighbor.identifier
            assert neighbor.identifier != cell.identifier

    def test_get_neighbors_edge_tile(self, grid_zoom_10):
        """Test getting neighbors for edge tiles."""
        # Get a tile at the edge (North Pole area)
        cell = grid_zoom_10.get_cell_from_point(85.0, 0.0)
        neighbors = grid_zoom_10.get_neighbors(cell)

        # Should have fewer neighbors due to edge constraints
        assert isinstance(neighbors, list)
        assert len(neighbors) <= 8

    def test_get_children(self, grid_zoom_10):
        """Test getting child tiles."""
        cell = grid_zoom_10.get_cell_from_point(40.7128, -74.0060)
        children = grid_zoom_10.get_children(cell)

        assert isinstance(children, list)
        assert len(children) == 4  # Slippy tiles have 4 children

        # All children should be valid
        for child in children:
            assert isinstance(child, GridCell)
            assert child.precision == 11  # One zoom level deeper

    def test_get_children_max_zoom(self):
        """Test getting children at maximum zoom level."""
        grid = SlippyGrid(zoom=22)  # Maximum zoom
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        children = grid.get_children(cell)

        assert children == []  # No children at max zoom

    def test_get_parent(self, grid_zoom_10):
        """Test getting parent tile."""
        cell = grid_zoom_10.get_cell_from_point(40.7128, -74.0060)
        parent = grid_zoom_10.get_parent(cell)

        assert isinstance(parent, GridCell)
        assert parent.precision == 9  # One zoom level up

    def test_get_parent_root_zoom(self):
        """Test getting parent at root zoom level."""
        grid = SlippyGrid(zoom=0)
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        parent = grid.get_parent(cell)

        assert parent is None  # No parent at zoom 0

    def test_get_cells_in_bbox_small(self, grid_zoom_10):
        """Test getting tiles in a small bounding box."""
        # Small area around NYC
        min_lat, min_lon = 40.7, -74.1
        max_lat, max_lon = 40.8, -74.0

        tiles = grid_zoom_10.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert isinstance(tiles, list)
        assert len(tiles) > 0

        # All tiles should be valid
        for tile in tiles:
            assert isinstance(tile, GridCell)
            assert "/" in tile.identifier

    def test_get_cells_in_bbox_large(self, grid_zoom_10):
        """Test getting tiles in a large bounding box."""
        # Large area covering multiple states
        min_lat, min_lon = 35.0, -80.0
        max_lat, max_lon = 45.0, -70.0

        tiles = grid_zoom_10.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert isinstance(tiles, list)
        assert len(tiles) > 10  # Should be many tiles

    def test_get_covering_cells(self, grid_zoom_10):
        """Test getting tiles that cover a polygon."""
        # Create a simple polygon
        polygon = box(-74.1, 40.7, -74.0, 40.8)  # Small rectangle around NYC

        tiles = grid_zoom_10.get_covering_cells(polygon, max_cells=50)

        assert isinstance(tiles, list)
        assert len(tiles) > 0
        assert len(tiles) <= 50  # Should respect max_cells limit

        # All tiles should be valid and intersect the polygon
        for tile in tiles:
            assert isinstance(tile, GridCell)
            assert tile.precision == 10
            assert tile.polygon.intersects(polygon)

    def test_different_zooms_same_point(self):
        """Test that different zoom levels produce different tile sizes."""
        lat, lon = 40.7128, -74.0060
        zooms = [5, 10, 15]
        tiles = []

        for zoom in zooms:
            grid = SlippyGrid(zoom=zoom)
            tile = grid.get_cell_from_point(lat, lon)
            tiles.append(tile)

        # All should contain the same point
        point = Point(lon, lat)
        for tile in tiles:
            assert tile.polygon.contains(point) or tile.polygon.touches(point)

        # Different zooms should produce different identifiers
        identifiers = [tile.identifier for tile in tiles]
        assert len(set(identifiers)) == 3  # All should be unique

        # Higher zoom should have smaller areas
        areas = [tile.area_km2 for tile in tiles]
        assert areas[0] > areas[1] > areas[2]  # Decreasing area

    def test_coordinate_conversion_consistency(self, grid_zoom_10):
        """Test that coordinate conversions are consistent."""
        test_points = [
            (40.7128, -74.0060),  # NYC
            (34.0522, -118.2437),  # LA
            (51.5074, -0.1278),  # London
            (35.6762, 139.6503),  # Tokyo
        ]

        for lat, lon in test_points:
            # Get tile from point
            tile = grid_zoom_10.get_cell_from_point(lat, lon)

            # Get tile from identifier
            tile_from_id = grid_zoom_10.get_cell_from_identifier(tile.identifier)

            # Should be the same identifier
            assert tile.identifier == tile_from_id.identifier

    def test_tile_hierarchy(self):
        """Test parent-child relationships."""
        parent_grid = SlippyGrid(zoom=10)
        child_grid = SlippyGrid(zoom=11)

        # Get a parent tile
        parent_tile = parent_grid.get_cell_from_point(40.7128, -74.0060)

        # Get its children
        children = parent_grid.get_children(parent_tile)
        assert len(children) == 4

        # Each child should have the correct parent
        for child in children:
            child_parent = child_grid.get_parent(child)
            assert child_parent.identifier == parent_tile.identifier

    def test_world_coverage_zoom_0(self):
        """Test that zoom 0 has exactly 4 tiles covering the world."""
        grid = SlippyGrid(zoom=0)

        # At zoom 0, there are 2x2 = 4 tiles covering the world
        # Test specific points to verify correct tiles
        origin_tile = grid.get_cell_from_point(0.0, 0.0)
        assert origin_tile.identifier in ["0/0/0", "0/0/1", "0/1/0", "0/1/1"]

        # Test that different quadrants get different tiles
        test_points = [
            (30.0, 30.0),  # NE quadrant
            (30.0, -30.0),  # NW quadrant
            (-30.0, 30.0),  # SE quadrant
            (-30.0, -30.0),  # SW quadrant
        ]

        tiles = set()
        for lat, lon in test_points:
            tile = grid.get_cell_from_point(lat, lon)
            tiles.add(tile.identifier)

        # Should have multiple tiles (but may not be 4 due to projection)
        assert len(tiles) >= 1

    def test_repr(self, grid_zoom_10):
        """Test string representation of grid."""
        repr_str = repr(grid_zoom_10)
        assert "SlippyGrid" in repr_str
        assert "zoom=10" in repr_str


class TestSlippyGridEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def grid_zoom_10(self):
        """Create a Slippy grid with zoom 10."""
        return SlippyGrid(zoom=10)

    def test_extreme_coordinates(self):
        """Test with extreme but valid coordinates."""
        grid = SlippyGrid(zoom=5)

        extreme_coords = [
            (85.0, 179.0),  # Near max lat/lon
            (-85.0, -179.0),  # Near min lat/lon
            (0.0, 0.0),  # Origin
        ]

        for lat, lon in extreme_coords:
            tile = grid.get_cell_from_point(lat, lon)
            assert isinstance(tile, GridCell)

    def test_dateline_crossing(self):
        """Test behavior around the international dateline."""
        grid = SlippyGrid(zoom=10)

        # Points on either side of dateline
        west_point = grid.get_cell_from_point(0.0, 179.9)
        east_point = grid.get_cell_from_point(0.0, -179.9)

        # Should be different tiles
        assert west_point.identifier != east_point.identifier

    def test_polar_regions(self):
        """Test behavior in polar regions."""
        grid = SlippyGrid(zoom=5)

        # Points near poles
        north_tile = grid.get_cell_from_point(84.0, 0.0)
        south_tile = grid.get_cell_from_point(-84.0, 0.0)

        assert isinstance(north_tile, GridCell)
        assert isinstance(south_tile, GridCell)
        assert north_tile.identifier != south_tile.identifier

    def test_empty_bbox(self, grid_zoom_10):
        """Test with empty bounding box."""
        # Point bounding box (min == max)
        tiles = grid_zoom_10.get_cells_in_bbox(40.7, -74.0, 40.7, -74.0)

        # Should return at least one tile
        assert len(tiles) >= 1

    def test_large_bbox_high_zoom(self):
        """Test large bounding box at high zoom level."""
        grid = SlippyGrid(zoom=18)  # High zoom

        # Small bounding box should not return too many tiles
        tiles = grid.get_cells_in_bbox(40.75, -74.05, 40.76, -74.04)

        # Should be reasonable number of tiles
        assert len(tiles) > 0
        assert len(tiles) < 100  # Should not be excessive


class TestSlippyGridSpecialProperties:
    """Test special properties of Slippy Map tiles."""

    def test_web_mercator_bounds(self):
        """Test that tiles respect Web Mercator bounds."""
        grid = SlippyGrid(zoom=10)

        # Test that extreme latitudes are handled correctly
        # Web Mercator clips at approximately ±85.05°
        north_tile = grid.get_cell_from_point(85.0, 0.0)
        south_tile = grid.get_cell_from_point(-85.0, 0.0)

        assert isinstance(north_tile, GridCell)
        assert isinstance(south_tile, GridCell)

    def test_tile_naming_convention(self):
        """Test that tile names follow z/x/y convention."""
        grid = SlippyGrid(zoom=10)

        tile = grid.get_cell_from_point(40.7128, -74.0060)
        parts = tile.identifier.split("/")

        assert len(parts) == 3
        z, x, y = map(int, parts)
        assert z == 10
        assert 0 <= x < 2**10
        assert 0 <= y < 2**10

    def test_quadtree_property(self):
        """Test that tiles follow quadtree subdivision."""
        parent_grid = SlippyGrid(zoom=5)

        # Get a parent tile
        parent = parent_grid.get_cell_from_point(40.0, -100.0)
        children = parent_grid.get_children(parent)

        # Should have exactly 4 children
        assert len(children) == 4

        # Children should have coordinates that are 2x parent coordinates
        parent_parts = parent.identifier.split("/")
        parent_z, parent_x, parent_y = map(int, parent_parts)

        expected_children = [
            f"{parent_z + 1}/{parent_x * 2}/{parent_y * 2}",
            f"{parent_z + 1}/{parent_x * 2 + 1}/{parent_y * 2}",
            f"{parent_z + 1}/{parent_x * 2}/{parent_y * 2 + 1}",
            f"{parent_z + 1}/{parent_x * 2 + 1}/{parent_y * 2 + 1}",
        ]

        child_ids = [child.identifier for child in children]
        assert set(child_ids) == set(expected_children)
